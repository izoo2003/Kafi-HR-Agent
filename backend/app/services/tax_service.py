"""Tax year / slab CRUD and annual tax calculation."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, EntityNotFound, ValidationFailed
from app.models.payroll import TaxSlab, TaxYear
from app.schemas.common import AuthContext
from app.schemas.payroll import (
    TaxSlabCreate,
    TaxSlabRead,
    TaxSlabsReplace,
    TaxYearCreate,
    TaxYearRead,
    TaxYearUpdate,
)
from app.services import audit_service

# Pakistan salary tax slabs FY 2026-27 (annual taxable income, PKR)
FY_2026_27_SLABS: list[dict] = [
    {
        "sort_order": 1,
        "min_amount": Decimal("0"),
        "max_amount": Decimal("600000"),
        "fixed_amount": Decimal("0"),
        "rate_percent": Decimal("0"),
        "excess_over": Decimal("0"),
    },
    {
        "sort_order": 2,
        "min_amount": Decimal("600001"),
        "max_amount": Decimal("1200000"),
        "fixed_amount": Decimal("0"),
        "rate_percent": Decimal("1"),
        "excess_over": Decimal("600000"),
    },
    {
        "sort_order": 3,
        "min_amount": Decimal("1200001"),
        "max_amount": Decimal("2200000"),
        "fixed_amount": Decimal("6000"),
        "rate_percent": Decimal("11"),
        "excess_over": Decimal("1200000"),
    },
    {
        "sort_order": 4,
        "min_amount": Decimal("2200001"),
        "max_amount": Decimal("3200000"),
        "fixed_amount": Decimal("116000"),
        "rate_percent": Decimal("20"),
        "excess_over": Decimal("2200000"),
    },
    {
        "sort_order": 5,
        "min_amount": Decimal("3200001"),
        "max_amount": Decimal("4100000"),
        "fixed_amount": Decimal("316000"),
        "rate_percent": Decimal("25"),
        "excess_over": Decimal("3200000"),
    },
    {
        "sort_order": 6,
        "min_amount": Decimal("4100001"),
        "max_amount": Decimal("5600000"),
        "fixed_amount": Decimal("541000"),
        "rate_percent": Decimal("29"),
        "excess_over": Decimal("4100000"),
    },
    {
        "sort_order": 7,
        "min_amount": Decimal("5600001"),
        "max_amount": Decimal("7000000"),
        "fixed_amount": Decimal("976000"),
        "rate_percent": Decimal("32"),
        "excess_over": Decimal("5600000"),
    },
    {
        "sort_order": 8,
        "min_amount": Decimal("7000001"),
        "max_amount": None,
        "fixed_amount": Decimal("1424000"),
        "rate_percent": Decimal("35"),
        "excess_over": Decimal("7000000"),
    },
]


def list_tax_years(db: Session) -> list[TaxYearRead]:
    rows = db.query(TaxYear).order_by(TaxYear.start_date.desc()).all()
    out: list[TaxYearRead] = []
    for y in rows:
        slabs = (
            db.query(TaxSlab)
            .filter(TaxSlab.tax_year_id == y.id)
            .order_by(TaxSlab.sort_order, TaxSlab.id)
            .all()
        )
        out.append(
            TaxYearRead(
                id=y.id,
                label=y.label,
                start_date=y.start_date,
                end_date=y.end_date,
                is_active=y.is_active,
                notes=y.notes,
                slabs=[TaxSlabRead.model_validate(s) for s in slabs],
                created_at=y.created_at,
                updated_at=y.updated_at,
            )
        )
    return out


def get_tax_year(db: Session, tax_year_id: int) -> TaxYear:
    row = db.query(TaxYear).filter(TaxYear.id == tax_year_id).one_or_none()
    if row is None:
        raise EntityNotFound(f"Tax year {tax_year_id} not found")
    return row


def get_tax_year_read(db: Session, tax_year_id: int) -> TaxYearRead:
    y = get_tax_year(db, tax_year_id)
    slabs = (
        db.query(TaxSlab)
        .filter(TaxSlab.tax_year_id == y.id)
        .order_by(TaxSlab.sort_order, TaxSlab.id)
        .all()
    )
    return TaxYearRead(
        id=y.id,
        label=y.label,
        start_date=y.start_date,
        end_date=y.end_date,
        is_active=y.is_active,
        notes=y.notes,
        slabs=[TaxSlabRead.model_validate(s) for s in slabs],
        created_at=y.created_at,
        updated_at=y.updated_at,
    )


def create_tax_year(db: Session, auth: AuthContext, payload: TaxYearCreate) -> TaxYearRead:
    if payload.end_date < payload.start_date:
        raise ValidationFailed("end_date must be on or after start_date")
    if db.query(TaxYear).filter(TaxYear.label == payload.label.strip()).one_or_none():
        raise ConflictError(f"Tax year '{payload.label}' already exists")
    year = TaxYear(
        label=payload.label.strip(),
        start_date=payload.start_date,
        end_date=payload.end_date,
        is_active=payload.is_active,
        notes=payload.notes,
    )
    db.add(year)
    db.flush()
    for s in payload.slabs:
        db.add(
            TaxSlab(
                tax_year_id=year.id,
                sort_order=s.sort_order,
                min_amount=s.min_amount,
                max_amount=s.max_amount,
                fixed_amount=s.fixed_amount,
                rate_percent=s.rate_percent,
                excess_over=s.excess_over,
            )
        )
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="tax_year.created",
        entity_type="tax_year",
        entity_id=year.id,
        after_state={"label": year.label, "slabs": len(payload.slabs)},
    )
    return get_tax_year_read(db, year.id)


def update_tax_year(
    db: Session, auth: AuthContext, tax_year_id: int, payload: TaxYearUpdate
) -> TaxYearRead:
    year = get_tax_year(db, tax_year_id)
    before = {"label": year.label, "is_active": year.is_active}
    data = payload.model_dump(exclude_unset=True)
    if "label" in data and data["label"]:
        data["label"] = data["label"].strip()
        clash = (
            db.query(TaxYear)
            .filter(TaxYear.label == data["label"], TaxYear.id != tax_year_id)
            .one_or_none()
        )
        if clash:
            raise ConflictError(f"Tax year '{data['label']}' already exists")
    for k, v in data.items():
        setattr(year, k, v)
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="tax_year.updated",
        entity_type="tax_year",
        entity_id=year.id,
        before_state=before,
        after_state=data,
    )
    return get_tax_year_read(db, year.id)


def replace_slabs(
    db: Session, auth: AuthContext, tax_year_id: int, payload: TaxSlabsReplace
) -> TaxYearRead:
    year = get_tax_year(db, tax_year_id)
    if not payload.slabs:
        raise ValidationFailed("At least one tax slab is required")
    existing = db.query(TaxSlab).filter(TaxSlab.tax_year_id == tax_year_id).all()
    for row in existing:
        db.delete(row)
    db.flush()
    for s in payload.slabs:
        db.add(
            TaxSlab(
                tax_year_id=year.id,
                sort_order=s.sort_order,
                min_amount=s.min_amount,
                max_amount=s.max_amount,
                fixed_amount=s.fixed_amount,
                rate_percent=s.rate_percent,
                excess_over=s.excess_over,
            )
        )
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="tax_slabs.replaced",
        entity_type="tax_year",
        entity_id=year.id,
        after_state={"count": len(payload.slabs)},
    )
    return get_tax_year_read(db, year.id)


def calculate_annual_tax(annual_income: Decimal, slabs: list[TaxSlab]) -> Decimal:
    """Progressive annual tax from ordered slabs."""
    income = Decimal(annual_income or 0)
    if income <= 0:
        return Decimal("0")
    ordered = sorted(slabs, key=lambda s: (s.sort_order, s.min_amount))
    for slab in ordered:
        upper = slab.max_amount
        if upper is None or income <= upper:
            excess = income - Decimal(slab.excess_over)
            if excess < 0:
                excess = Decimal("0")
            tax = Decimal(slab.fixed_amount) + (
                excess * Decimal(slab.rate_percent) / Decimal("100")
            )
            return tax.quantize(Decimal("0.01"))
    # Fallback: last slab
    if ordered:
        slab = ordered[-1]
        excess = max(Decimal("0"), income - Decimal(slab.excess_over))
        tax = Decimal(slab.fixed_amount) + (
            excess * Decimal(slab.rate_percent) / Decimal("100")
        )
        return tax.quantize(Decimal("0.01"))
    return Decimal("0")


def ensure_default_tax_year(db: Session) -> None:
    """Seed FY 2026-27 slabs if missing."""
    from datetime import date

    label = "2026-27"
    if db.query(TaxYear).filter(TaxYear.label == label).one_or_none():
        return
    year = TaxYear(
        label=label,
        start_date=date(2026, 7, 1),
        end_date=date(2027, 6, 30),
        is_active=True,
        notes="Pakistan salary tax slabs FY 2026-27 (seeded; editable in Payroll → Tax slabs)",
    )
    db.add(year)
    db.flush()
    for s in FY_2026_27_SLABS:
        db.add(TaxSlab(tax_year_id=year.id, **s))
    db.flush()
