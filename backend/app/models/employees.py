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
    # Department-level role duties and standard operating procedures
    job_description_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    sops_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    employees: Mapped[list[Employee]] = relationship(
        "Employee",
        back_populates="department",
        foreign_keys="Employee.department_id",
        lazy="selectin",
    )
    documents: Mapped[list[DepartmentDocument]] = relationship(
        "DepartmentDocument",
        back_populates="department",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="DepartmentDocument.id",
    )


class DepartmentDocument(Base, TimestampMixin):
    """Image or PDF attached to a department JD or SOP."""

    __tablename__ = "department_documents"

    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # job_description | sop
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)

    department: Mapped[Department] = relationship("Department", back_populates="documents")


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

    # Personal details
    cnic: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    personal_mobile: Mapped[str | None] = mapped_column(String(32), nullable=True)
    alternate_mobile: Mapped[str | None] = mapped_column(String(32), nullable=True)
    father_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(32), nullable=True)
    marital_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    current_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    permanent_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Workplace site: Mill | Clifton Office | KMP House
    location: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Bank details
    bank_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    account_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    account_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    iban: Mapped[str | None] = mapped_column(String(64), nullable=True)
    branch_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    branch_code: Mapped[str | None] = mapped_column(String(64), nullable=True)

    department: Mapped[Department] = relationship(
        "Department",
        back_populates="employees",
        foreign_keys=[department_id],
    )
    documents: Mapped[list[EmployeeDocument]] = relationship(
        "EmployeeDocument",
        back_populates="employee",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    references: Mapped[list[EmployeeReference]] = relationship(
        "EmployeeReference",
        back_populates="employee",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="EmployeeReference.id",
    )


class EmployeeDocument(Base, TimestampMixin):
    """Employee file attachments (CNIC, education, other)."""

    __tablename__ = "employee_documents"

    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)  # cnic | education | other | photo
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)

    employee: Mapped[Employee] = relationship("Employee", back_populates="documents")


class EmployeeReference(Base, TimestampMixin):
    __tablename__ = "employee_references"

    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    relation: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cnic: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    employee: Mapped[Employee] = relationship("Employee", back_populates="references")
    documents: Mapped[list[EmployeeReferenceDocument]] = relationship(
        "EmployeeReferenceDocument",
        back_populates="reference",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class EmployeeReferenceDocument(Base, TimestampMixin):
    __tablename__ = "employee_reference_documents"

    reference_id: Mapped[int] = mapped_column(
        ForeignKey("employee_references.id"), nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)

    reference: Mapped[EmployeeReference] = relationship(
        "EmployeeReference", back_populates="documents"
    )
