"""Compute monthly net salary from attendance + tax slabs."""
from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.exceptions import EntityNotFound, ValidationFailed
from app.models.attendance import AttendanceRecord
from app.models.employees import Department, Employee
from app.models.payroll import PayrollSheetAdjustment, TaxSlab
from app.models.system import SystemConfig
from app.schemas.payroll import PayrollComputeResult, PayrollComputeRow, PayrollTaxSlabLite
from app.services.attendance_service import _company_tz, _holiday_dates
from app.services.payroll_ai_summary import load_saved_payroll_ai_summary
from app.services.payroll_service import _normalize_payment_mode
from app.services.tax_service import calculate_annual_tax, get_tax_year_read


def _office_policy(db: Session) -> dict:
    row = db.query(SystemConfig).filter(SystemConfig.key == "attendance.office_policy").one_or_none()
    defaults = {
        "late_after": "09:40",
        "half_day_after": "11:30",
        "majority_absent_threshold": 0.9,
        "lates_per_off": 3,
        "month_days": 30,
        "leave_after_months": 6,
        "monthly_leave_allowance": 1,
    }
    if row and isinstance(row.value, dict):
        return {**defaults, **row.value}
    return defaults


def _parse_hhmm(value: str, fallback: time) -> time:
    try:
        parts = str(value).split(":")
        return time(int(parts[0]), int(parts[1]))
    except Exception:
        return fallback


def _tenure_months(joined: date | None, as_of: date) -> int:
    if joined is None or joined > as_of:
        return 0
    months = (as_of.year - joined.year) * 12 + (as_of.month - joined.month)
    if as_of.day < joined.day:
        months -= 1
    return max(0, months)


def compute_payroll_for_month(
    db: Session,
    *,
    period_month: int,
    period_year: int,
    tax_year_id: int,
    ignore_attendance_overrides: bool = False,
) -> PayrollComputeResult:
    if period_month < 1 or period_month > 12:
        raise ValidationFailed("period_month must be 1–12")
    tax_year = get_tax_year_read(db, tax_year_id)
    slabs = (
        db.query(TaxSlab)
        .filter(TaxSlab.tax_year_id == tax_year_id)
        .order_by(TaxSlab.sort_order, TaxSlab.id)
        .all()
    )
    if not slabs:
        raise ValidationFailed(f"Tax year '{tax_year.label}' has no slabs configured")

    tax_slab_lites = [
        PayrollTaxSlabLite(
            sort_order=s.sort_order,
            min_amount=s.min_amount,
            max_amount=s.max_amount,
            fixed_amount=s.fixed_amount,
            rate_percent=s.rate_percent,
            excess_over=s.excess_over,
        )
        for s in slabs
    ]

    policy = _office_policy(db)
    late_after = _parse_hhmm(policy["late_after"], time(9, 40))
    half_after = _parse_hhmm(policy["half_day_after"], time(11, 30))
    majority = float(policy["majority_absent_threshold"])
    lates_per_off = int(policy["lates_per_off"])
    month_days = int(policy["month_days"])
    leave_after_months = int(policy["leave_after_months"])
    monthly_leave = int(policy["monthly_leave_allowance"])

    last_day = calendar.monthrange(period_year, period_month)[1]
    period_start = date(period_year, period_month, 1)
    period_end = date(period_year, period_month, last_day)
    tz = _company_tz(db)
    configured_holidays = _holiday_dates(db)

    employees = (
        db.query(Employee)
        .filter(Employee.status == "active")
        .order_by(Employee.full_name)
        .all()
    )
    if not employees:
        return PayrollComputeResult(
            period_month=period_month,
            period_year=period_year,
            period_start=period_start,
            period_end=period_end,
            tax_year_id=tax_year.id,
            tax_year_label=tax_year.label,
            month_days=month_days,
            lates_per_off=lates_per_off,
            tax_slabs=tax_slab_lites,
            employees=[],
        )

    dept_ids = {e.department_id for e in employees}
    dept_names = {
        d.id: d.name for d in db.query(Department).filter(Department.id.in_(dept_ids)).all()
    }
    emp_ids = [e.id for e in employees]
    emp_id_set = set(emp_ids)
    adj_rows = (
        db.query(PayrollSheetAdjustment)
        .filter(
            PayrollSheetAdjustment.period_month == period_month,
            PayrollSheetAdjustment.period_year == period_year,
        )
        .all()
    )
    adjustments: dict[int, PayrollSheetAdjustment] = {
        a.employee_id: a for a in adj_rows if a.employee_id in emp_id_set
    }

    records = (
        db.query(AttendanceRecord)
        .filter(
            AttendanceRecord.employee_id.in_(emp_ids),
            AttendanceRecord.date >= period_start,
            AttendanceRecord.date <= period_end,
        )
        .all()
    )
    punches: dict[int, dict[date, AttendanceRecord]] = defaultdict(dict)
    for r in records:
        punches[r.employee_id][r.date] = r

    stored_off_dates: set[date] = set()
    statuses_by_date: dict[date, list[str]] = defaultdict(list)
    for r in records:
        statuses_by_date[r.date].append(r.status)
    for day, statuses in statuses_by_date.items():
        holiday_n = sum(1 for s in statuses if s == "holiday")
        if statuses and holiday_n / len(statuses) >= 0.5:
            stored_off_dates.add(day)

    # Day classification (same office rules as attendance period report).
    # Imported holiday/Saturday-off rows are the source of truth for that month.
    day_types: dict[date, str] = {}
    d = period_start
    while d <= period_end:
        if d.weekday() == 6:
            day_types[d] = "sunday_off"
        elif d in configured_holidays:
            day_types[d] = "configured_holiday"
        elif d in stored_off_dates:
            day_types[d] = "saturday_off" if d.weekday() == 5 else "auto_holiday"
        else:
            present_n = sum(
                1
                for eid in emp_ids
                if punches.get(eid, {}).get(d) and punches[eid][d].check_in is not None
            )
            absent_rate = 1.0 - (present_n / max(len(emp_ids), 1))
            if d.weekday() == 5:
                day_types[d] = "saturday_off" if absent_rate >= majority else "working"
            else:
                day_types[d] = "auto_holiday" if absent_rate >= majority else "working"
        d += timedelta(days=1)

    rows: list[PayrollComputeRow] = []
    for emp in employees:
        adj = adjustments.get(emp.id)
        # Rows removed from the edit salary sheet stay out until re-imported / un-excluded.
        if (
            adj is not None
            and bool(getattr(adj, "excluded", False))
            and not ignore_attendance_overrides
        ):
            continue

        base = Decimal(str(emp.base_salary or 0))
        per_day = (base / Decimal(month_days)).quantize(Decimal("0.01")) if base else Decimal("0")
        emp_punches = punches.get(emp.id, {})

        days_late = days_half = days_absent = 0
        late_events: list[dict] = []
        ot_days = 0

        d = period_start
        while d <= period_end:
            dtype = day_types[d]
            rec = emp_punches.get(d)
            cin = rec.check_in if rec else None
            local_in = cin.astimezone(tz).time() if cin else None

            if dtype in ("sunday_off", "saturday_off", "configured_holiday", "auto_holiday"):
                if cin is not None:
                    ot_days += 1
            else:
                if cin is None:
                    days_absent += 1
                else:
                    is_half = bool(local_in and local_in > half_after)
                    is_late = bool(local_in and local_in > late_after)
                    # After 11:30 counts as late + half day
                    if is_half:
                        days_half += 1
                        days_late += 1
                        late_events.append(
                            {
                                "date": d.isoformat(),
                                "check_in_time": local_in.strftime("%H:%M") if local_in else "",
                                "note": "late + half day (after 11:30)",
                            }
                        )
                    elif is_late:
                        days_late += 1
                        late_events.append(
                            {
                                "date": d.isoformat(),
                                "check_in_time": local_in.strftime("%H:%M") if local_in else "",
                                "note": "late",
                            }
                        )
            d += timedelta(days=1)

        late_off_days = days_late // lates_per_off
        tenure_m = _tenure_months(emp.date_joined, period_end)
        leave_allowance = monthly_leave if tenure_m >= leave_after_months else 0
        leave_used = min(leave_allowance, days_absent)
        # Chargeable no-show absents after leave forgiveness (late offs are separate).
        raw_absents_after_leave = max(0, days_absent - leave_used)
        # Absent column = days the person did not come (never includes late-off days).
        days_absent_reported = days_absent
        absents_after_leave_reported = raw_absents_after_leave
        ot_days_final = ot_days

        if adj is not None:
            if not ignore_attendance_overrides:
                if adj.leave_used is not None:
                    leave_used = max(0, adj.leave_used)
                if adj.days_absent is not None:
                    # Sheet Absent is no-show days only.
                    days_absent_reported = max(0, adj.days_absent)
                if adj.days_late is not None:
                    days_late = max(0, adj.days_late)
                    late_off_days = days_late // lates_per_off
                if adj.days_half_day is not None:
                    days_half = max(0, adj.days_half_day)
                if adj.overtime_bonus_days is not None:
                    ot_days_final = max(0, adj.overtime_bonus_days)

                # Recompute forgiveness against recorded no-show Absents only.
                if adj.leave_used is not None or adj.days_absent is not None:
                    leave_used = min(leave_used, days_absent_reported)
                    raw_absents_after_leave = max(0, days_absent_reported - leave_used)
                    absents_after_leave_reported = raw_absents_after_leave

        days_present = (
            adj.days_present
            if (
                adj is not None
                and adj.days_present is not None
                and not ignore_attendance_overrides
            )
            else max(0, month_days - raw_absents_after_leave)
        )

        overtime_amount = (Decimal(ot_days_final) * per_day).quantize(Decimal("0.01"))
        allowance = Decimal(str(adj.allowance_amount)) if adj else Decimal("0")
        bonus = Decimal(str(getattr(adj, "bonus_amount", 0) or 0)) if adj else Decimal("0")
        loan = Decimal(str(adj.loan_deduction_amount)) if adj else Decimal("0")
        advance = Decimal(str(adj.advance_amount)) if adj else Decimal("0")
        late_deduction_amount = (Decimal(late_off_days) * per_day).quantize(Decimal("0.01"))
        half_day_deduction = (Decimal(days_half) * per_day * Decimal("0.5")).quantize(Decimal("0.01"))
        attendance_deduction = (
            Decimal(raw_absents_after_leave) * per_day + late_deduction_amount + half_day_deduction
        ).quantize(Decimal("0.01"))
        gross_salary = (
            per_day * Decimal(days_present) + allowance + bonus + overtime_amount
        ).quantize(Decimal("0.01"))
        annual_taxable = (gross_salary * Decimal("12")).quantize(Decimal("0.01"))
        annual_tax = calculate_annual_tax(annual_taxable, slabs)
        monthly_tax = (annual_tax / Decimal("12")).quantize(Decimal("0.01"))
        if adj is not None and adj.monthly_tax_override is not None:
            monthly_tax = Decimal(str(adj.monthly_tax_override)).quantize(Decimal("0.01"))
        net_payable = (
            gross_salary
            - late_deduction_amount
            - loan
            - half_day_deduction
            - advance
            - monthly_tax
        ).quantize(Decimal("0.01"))
        if net_payable < 0:
            net_payable = Decimal("0")
        gross = gross_salary

        note = adj.remarks if adj and adj.remarks else None
        if not any(punches.values()):
            note = note or (
                "No attendance imported for this month — gross ≈ base (upload Excel period report first)"
            )
        elif not emp_punches:
            note = note or "No attendance rows for this employee in the selected month"

        rows.append(
            PayrollComputeRow(
                employee_id=emp.id,
                employee_code=emp.employee_code,
                full_name=emp.full_name,
                department_name=dept_names.get(emp.department_id),
                role_title=emp.role_title or "",
                base_salary=base,
                per_day_rate=per_day,
                days_present=days_present,
                days_absent=days_absent_reported,
                days_late=days_late,
                days_half_day=days_half,
                late_off_days=late_off_days,
                leave_allowance=leave_allowance,
                leave_used=leave_used,
                absents_after_leave=absents_after_leave_reported,
                overtime_bonus_days=ot_days_final,
                attendance_deduction=attendance_deduction,
                overtime_amount=overtime_amount,
                late_deduction_amount=late_deduction_amount,
                half_day_deduction=half_day_deduction,
                allowance_amount=allowance,
                bonus_amount=bonus,
                loan_deduction_amount=loan,
                advance_amount=advance,
                payment_mode=_normalize_payment_mode(
                    adj.payment_mode if adj and adj.payment_mode else None
                ),
                remarks=adj.remarks if adj else None,
                gross_salary=gross_salary,
                gross_after_attendance=gross,
                annual_taxable_income=annual_taxable,
                annual_tax=annual_tax,
                monthly_tax=monthly_tax,
                net_salary=net_payable,
                net_payable=net_payable,
                tax_manual=bool(adj is not None and adj.monthly_tax_override is not None),
                late_events=late_events,
                notes=note,
            )
        )

    return PayrollComputeResult(
        period_month=period_month,
        period_year=period_year,
        period_start=period_start,
        period_end=period_end,
        tax_year_id=tax_year.id,
        tax_year_label=tax_year.label,
        month_days=month_days,
        lates_per_off=lates_per_off,
        tax_slabs=tax_slab_lites,
        employees=rows,
        ai_summary=load_saved_payroll_ai_summary(db, period_year, period_month),
    )
