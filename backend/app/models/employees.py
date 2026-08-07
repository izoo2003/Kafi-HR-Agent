"""Employee & org models — DATABASE_SCHEMA.md §2."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin


class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    head_employee_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("employees.id", use_alter=True, name="fk_departments_head_employee"),
        nullable=True,
    )

    employees: Mapped[list[Employee]] = relationship(
        "Employee",
        back_populates="department",
        foreign_keys="Employee.department_id",
        lazy="selectin",
    )


class Employee(Base, TimestampMixin):
    __tablename__ = "employees"

    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, unique=True)
    employee_code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), nullable=False)
    role_title: Mapped[str] = mapped_column(Text, nullable=False)
    # Duties / requirements for this employee (internal JD — not a hiring job posting).
    job_description_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String, nullable=True)
    date_joined: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_exited: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)
    base_salary: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    manager_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)

    department: Mapped[Department] = relationship(
        "Department",
        back_populates="employees",
        foreign_keys=[department_id],
    )
