"""Batched KPI rollups — one employee query + one work-log query per window, cached."""
from __future__ import annotations

import threading
import time as time_mod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import EntityNotFound
from app.models.employees import Department, Employee
from app.models.kpi import KpiDefinition, KpiEntry
from app.schemas.kpi import (
    DepartmentEmployeeKpiSummary,
    DepartmentKpiSummary,
    EmployeeKpiSummary,
    EmployeeWorkItem,
    GlobalDepartmentKpiSummary,
    GlobalKpiSummary,
    KpiDailyPoint,
    KpiDailySummary,
)


@dataclass(frozen=True)
class _EmpSnap:
    id: int
    full_name: str
    department_id: int
    date_joined: date | None
    date_exited: date | None


@dataclass(frozen=True)
class _DeptSnap:
    id: int
    name: str


@dataclass(frozen=True)
class _EntrySnap:
    employee_id: int
    period_start: date
    actual_value: float
    notes: str


@dataclass
class _WorkRollupIndex:
    departments: list[_DeptSnap]
    employees_by_id: dict[int, _EmpSnap]
    employees_by_dept: dict[int, list[_EmpSnap]]
    points_by_emp_day: dict[tuple[int, date], float]
    entries_by_emp: dict[int, list[_EntrySnap]] = field(default_factory=dict)


_INDEX_TTL_SECONDS = 20.0
_index_lock = threading.Lock()
_index_cache: dict[tuple[date, date, int | None], tuple[float, _WorkRollupIndex]] = {}
_index_inflight: dict[tuple[date, date, int | None], threading.Event] = {}


def invalidate_kpi_rollup_cache() -> None:
    with _index_lock:
        _index_cache.clear()


def _ks():
    from app.services import kpi_service as ks

    return ks


def load_work_rollup_index(
    db: Session,
    period_start: date,
    period_end: date,
    *,
    department_id: int | None = None,
) -> _WorkRollupIndex:
    ks = _ks()
    cache_key = (period_start, period_end, department_id)
    now = time_mod.monotonic()
    wait_for: threading.Event | None = None
    builder = False
    with _index_lock:
        hit = _index_cache.get(cache_key)
        if hit is not None and now - hit[0] < _INDEX_TTL_SECONDS:
            return hit[1]
        inflight = _index_inflight.get(cache_key)
        if inflight is not None:
            wait_for = inflight
        else:
            wait_for = threading.Event()
            _index_inflight[cache_key] = wait_for
            builder = True
    if not builder:
        wait_for.wait(timeout=30)
        with _index_lock:
            hit = _index_cache.get(cache_key)
        if hit is not None:
            return hit[1]

    try:
        # Column selects only — Employee/Department have lazy="selectin" relationships
        # (documents, references) that would otherwise fire extra remote round-trips.
        emp_stmt = select(
            Employee.id,
            Employee.full_name,
            Employee.department_id,
            Employee.date_joined,
            Employee.date_exited,
        ).where(Employee.status == "active")
        dept_stmt = select(Department.id, Department.name).order_by(
            Department.name.asc(), Department.id.asc()
        )
        entry_stmt = (
            select(
                KpiEntry.employee_id,
                KpiEntry.period_start,
                KpiEntry.actual_value,
                KpiEntry.notes,
            )
            .join(KpiDefinition, KpiDefinition.id == KpiEntry.kpi_definition_id)
            .where(
                KpiDefinition.name == ks.WORK_LOG_KPI_NAME,
                KpiEntry.period_start >= period_start,
                KpiEntry.period_start <= period_end,
            )
        )
        if department_id is not None:
            emp_stmt = emp_stmt.where(Employee.department_id == department_id)
            dept_stmt = dept_stmt.where(Department.id == department_id)
            entry_stmt = entry_stmt.where(KpiDefinition.department_id == department_id)

        employees = db.execute(emp_stmt).all()
        departments = db.execute(dept_stmt).all()
        entry_rows = db.execute(entry_stmt).all()

        points: dict[tuple[int, date], float] = {}
        entries_by_emp: dict[int, list[_EntrySnap]] = defaultdict(list)
        for entry in entry_rows:
            snap = _EntrySnap(
                employee_id=entry.employee_id,
                period_start=entry.period_start,
                actual_value=float(entry.actual_value or 0),
                notes=entry.notes or "",
            )
            key = (snap.employee_id, snap.period_start)
            points[key] = points.get(key, 0.0) + snap.actual_value
            entries_by_emp[snap.employee_id].append(snap)

        emp_snaps = [
            _EmpSnap(
                id=emp.id,
                full_name=emp.full_name,
                department_id=emp.department_id,
                date_joined=emp.date_joined,
                date_exited=emp.date_exited,
            )
            for emp in employees
        ]
        by_dept: dict[int, list[_EmpSnap]] = defaultdict(list)
        by_id: dict[int, _EmpSnap] = {}
        for emp in emp_snaps:
            by_id[emp.id] = emp
            by_dept[emp.department_id].append(emp)
        index = _WorkRollupIndex(
            departments=[_DeptSnap(id=d.id, name=d.name) for d in departments],
            employees_by_id=by_id,
            employees_by_dept=by_dept,
            points_by_emp_day=points,
            entries_by_emp=entries_by_emp,
        )
        with _index_lock:
            _index_cache[cache_key] = (time_mod.monotonic(), index)
            done = _index_inflight.pop(cache_key, None)
        if done is not None:
            done.set()
        return index
    except Exception:
        with _index_lock:
            done = _index_inflight.pop(cache_key, None)
        if done is not None:
            done.set()
        raise


def _contribution(
    emp: _EmpSnap,
    period_start: date,
    period_end: date,
    index: _WorkRollupIndex,
    *,
    include_work_items: bool,
) -> tuple[float, int, list[EmployeeWorkItem]]:
    ks = _ks()
    workdays = [
        day
        for day in ks._workdays_in_range(period_start, period_end)
        if ks._employee_on_date(emp, day)
    ]
    target = float(ks.WORK_LOG_TARGET)
    daily = [
        min(index.points_by_emp_day.get((emp.id, day), 0.0), target) for day in workdays
    ]
    contribution = round(sum(daily) / len(daily), 2) if daily else 0.0
    entries = index.entries_by_emp.get(emp.id, [])
    if include_work_items:
        items: list[EmployeeWorkItem] = []
        for entry in entries:
            items.extend(ks._split_work_items(entry))
        return contribution, len(items), items
    submission_count = 0
    for entry in entries:
        notes = entry.notes or ""
        submission_count += len(
            [chunk for chunk in notes.split(ks.WORK_ENTRY_SEPARATOR) if chunk.strip()]
        )
    return contribution, submission_count, []


def department_from_index(
    index: _WorkRollupIndex,
    department_id: int,
    period_start: date,
    period_end: date,
    *,
    include_work_items: bool,
) -> DepartmentKpiSummary:
    ks = _ks()
    eligible = [
        emp
        for emp in index.employees_by_dept.get(department_id, [])
        if ks._employee_in_period(emp, period_start, period_end)
    ]
    employee_summaries: list[DepartmentEmployeeKpiSummary] = []
    for emp in eligible:
        score, count, items = _contribution(
            emp, period_start, period_end, index, include_work_items=include_work_items
        )
        employee_summaries.append(
            DepartmentEmployeeKpiSummary(
                employee_id=emp.id,
                employee_name=emp.full_name,
                submission_count=count,
                contribution_score=score,
                band=ks.work_log_band(score),
                work_items=items,
            )
        )
    submitted = [s for s in employee_summaries if s.submission_count > 0]
    entries_expected = len(eligible)
    entries_recorded = len(submitted)
    overall = (
        round(sum(s.contribution_score for s in employee_summaries) / len(employee_summaries), 2)
        if employee_summaries
        else 0.0
    )
    completeness = (entries_recorded / entries_expected) if entries_expected else 1.0
    band = (
        "complete"
        if eligible and all(s.contribution_score >= 10.0 for s in employee_summaries)
        else ks.work_log_band(overall)
    )
    return DepartmentKpiSummary(
        department_id=department_id,
        period_start=period_start,
        period_end=period_end,
        overall_score=overall,
        band=band,
        entries_recorded=entries_recorded,
        entries_expected=entries_expected,
        completeness=round(completeness, 4),
        employees=employee_summaries,
    )


def global_from_index(
    index: _WorkRollupIndex, period_start: date, period_end: date
) -> GlobalKpiSummary:
    ks = _ks()
    departments: list[GlobalDepartmentKpiSummary] = []
    total_expected = 0
    total_recorded = 0
    scores: list[float] = []
    for dept in index.departments:
        summary = department_from_index(
            index, dept.id, period_start, period_end, include_work_items=False
        )
        departments.append(
            GlobalDepartmentKpiSummary(
                department_id=dept.id,
                department_name=dept.name,
                overall_score=summary.overall_score,
                band=summary.band,
                entries_recorded=summary.entries_recorded,
                entries_expected=summary.entries_expected,
                completeness=summary.completeness,
            )
        )
        total_expected += summary.entries_expected
        total_recorded += summary.entries_recorded
        if summary.entries_expected > 0:
            scores.append(summary.overall_score)
    departments.sort(key=lambda item: (-item.overall_score, item.department_name.lower()))
    overall = round(sum(scores) / len(scores), 2) if scores else 0.0
    completeness = (total_recorded / total_expected) if total_expected else 1.0
    return GlobalKpiSummary(
        period_start=period_start,
        period_end=period_end,
        overall_score=overall,
        band="complete"
        if departments and all(d.band == "complete" for d in departments)
        else ks.work_log_band(overall),
        departments_complete=sum(1 for d in departments if d.band == "complete"),
        departments_expected=len(departments),
        entries_recorded=total_recorded,
        entries_expected=total_expected,
        completeness=round(completeness, 4),
        departments=departments,
    )


def _score_for_day(index: _WorkRollupIndex, department_id: int, day: date) -> tuple[float, int]:
    ks = _ks()
    if ks.is_sunday(day) or day > ks.company_today():
        return 0.0, 0
    eligible = [
        emp
        for emp in index.employees_by_dept.get(department_id, [])
        if ks._employee_on_date(emp, day)
    ]
    if not eligible:
        return 0.0, 0
    target = float(ks.WORK_LOG_TARGET)
    scores = [
        min(index.points_by_emp_day.get((emp.id, day), 0.0), target) for emp in eligible
    ]
    recorded = sum(
        1 for emp in eligible if index.points_by_emp_day.get((emp.id, day), 0.0) > 0
    )
    return round(sum(scores) / len(scores), 2), recorded


def department_summary(
    db: Session, department_id: int, period_start: date, period_end: date
) -> DepartmentKpiSummary:
    index = load_work_rollup_index(
        db, period_start, period_end, department_id=department_id
    )
    if not index.departments:
        raise EntityNotFound(f"Department {department_id} not found")
    return department_from_index(
        index, department_id, period_start, period_end, include_work_items=False
    )


def global_summary(db: Session, period_start: date, period_end: date) -> GlobalKpiSummary:
    index = load_work_rollup_index(db, period_start, period_end)
    return global_from_index(index, period_start, period_end)


def daily_summary(
    db: Session,
    period_start: date,
    period_end: date,
    *,
    department_id: int | None = None,
    department_name: str | None = None,
) -> KpiDailySummary:
    ks = _ks()
    index = load_work_rollup_index(
        db, period_start, period_end, department_id=department_id
    )
    days: list[KpiDailyPoint] = []
    scored: list[float] = []
    for day in ks._workdays_in_range(period_start, period_end):
        if department_id is not None:
            score, recorded = _score_for_day(index, department_id, day)
        else:
            dept_scores: list[float] = []
            recorded = 0
            for dept in index.departments:
                d_score, d_recorded = _score_for_day(index, dept.id, day)
                recorded += d_recorded
                if any(
                    ks._employee_on_date(emp, day)
                    for emp in index.employees_by_dept.get(dept.id, [])
                ):
                    dept_scores.append(d_score)
            score = round(sum(dept_scores) / len(dept_scores), 2) if dept_scores else 0.0
        scored.append(score)
        days.append(
            KpiDailyPoint(
                date=day,
                score=score,
                band=ks.work_log_band(score),
                entries_recorded=recorded,
            )
        )
    overall = round(sum(scored) / len(scored), 2) if scored else 0.0
    return KpiDailySummary(
        scope="department" if department_id is not None else "global",
        department_id=department_id,
        department_name=department_name,
        period_start=period_start,
        period_end=period_end,
        overall_score=overall,
        band=ks.work_log_band(overall),
        days=days,
    )


def employee_summary(
    db: Session,
    emp: Employee | _EmpSnap,
    period_start: date,
    period_end: date,
) -> EmployeeKpiSummary:
    index = load_work_rollup_index(db, period_start, period_end)
    snap = _EmpSnap(
        id=emp.id,
        full_name=emp.full_name,
        department_id=emp.department_id,
        date_joined=emp.date_joined,
        date_exited=emp.date_exited,
    )
    score, count, items = _contribution(
        snap, period_start, period_end, index, include_work_items=True
    )
    department = department_from_index(
        index, emp.department_id, period_start, period_end, include_work_items=False
    )
    company = global_from_index(index, period_start, period_end)
    return EmployeeKpiSummary(
        employee_id=emp.id,
        department_id=emp.department_id,
        period_start=period_start,
        period_end=period_end,
        submission_count=count,
        contribution_score=score,
        department_score=department.overall_score,
        department_band=department.band,
        global_score=company.overall_score,
        global_band=company.band,
        work_items=items,
    )
