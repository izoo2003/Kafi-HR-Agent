"""HR policies document — stored in system_config key `hr.policies`."""
from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models.system import SystemConfig
from app.schemas.common import AuthContext
from app.schemas.hr_policies import HrPoliciesDocument
from app.services import audit_service

HR_POLICIES_KEY = "hr.policies"

DEFAULT_HR_POLICIES: dict = {
    "welcome_title": "Welcome to KAFI Team",
    "welcome_subtitle": "HR Major Highlight Points",
    "sections": [
        {
            "id": "documents",
            "title": "Required Documents",
            "icon": "documents",
            "status": "info",
            "list_style": "ol",
            "items": [
                {"text": "Updated CV with photo & CNIC/ID copy", "quoted": False, "children": []},
                {"text": "CNIC/ID copy of one first blood relative", "quoted": False, "children": []},
                {
                    "text": "Five references in total:",
                    "quoted": False,
                    "children": [
                        "One previous job reference (Director-level preferred)",
                        "One blood relative reference",
                        "Three professional references",
                    ],
                },
                {
                    "text": "Resignation letter from last job with official receiving",
                    "quoted": False,
                    "children": [],
                },
                {"text": "Last job salary slip (any one month)", "quoted": False, "children": []},
            ],
        },
        {
            "id": "timings",
            "title": "Office Timings & Attendance",
            "icon": "timings",
            "status": "warning",
            "list_style": "ul",
            "items": [
                {"text": "Office Timing: 9:30 AM to 6:30 PM", "quoted": False, "children": []},
                {"text": "3 late arrivals = 1 leave deduction", "quoted": False, "children": []},
                {
                    "text": "Second Saturday of every month is an official holiday",
                    "quoted": False,
                    "children": [],
                },
                {
                    "text": (
                        "Government-gazetted holidays (e.g., Eid, 14th August, 25th December) "
                        "will be observed"
                    ),
                    "quoted": False,
                    "children": [],
                },
                {
                    "text": (
                        "Non-regular or emergency government holidays will not be observed unless "
                        "officially approved and circulated by KAFI"
                    ),
                    "quoted": False,
                    "children": [],
                },
            ],
        },
        {
            "id": "sop",
            "title": "SOP",
            "icon": "sop",
            "status": "neutral",
            "list_style": "paragraphs",
            "items": [
                {
                    "text": "All KPI are daily sent by WhatsApp/ SMS / emails",
                    "quoted": False,
                    "children": [],
                },
                {
                    "text": "Daily tasks must be written on Computer Sticky notes",
                    "quoted": False,
                    "children": [],
                },
                {
                    "text": (
                        "All SOP as per JOB description, dress code, and ethical policy must be followed"
                    ),
                    "quoted": False,
                    "children": [],
                },
            ],
        },
        {
            "id": "leave",
            "title": "Leave Policy",
            "icon": "leave",
            "status": "on_leave",
            "list_style": "ul",
            "items": [
                {
                    "text": "No leaves allowed during the first 3-month probation period",
                    "quoted": False,
                    "children": [],
                },
                {
                    "text": (
                        "After completing 7 months, employees receive 12 annual leaves per year "
                        "(including sick leave)"
                    ),
                    "quoted": False,
                    "children": [],
                },
                {
                    "text": "1 Saturday off every month = 12 additional holidays per year",
                    "quoted": False,
                    "children": [],
                },
                {
                    "text": (
                        "Total: 24 company holidays annually + all official government-gazetted holidays"
                    ),
                    "quoted": False,
                    "children": [],
                },
                {
                    "text": (
                        "Non-regular or emergency Government-announced holidays will not be observed "
                        "unless officially approved and formally communicated by KAFI Management."
                    ),
                    "quoted": True,
                    "children": [],
                },
                {"text": "All leave requests must be made in advance", "quoted": False, "children": []},
                {
                    "text": "Unapproved absence will be counted as Leave Without Pay (LWP)",
                    "quoted": False,
                    "children": [],
                },
            ],
        },
        {
            "id": "confidentiality",
            "title": "Confidentiality Clause",
            "icon": "confidentiality",
            "status": "critical",
            "list_style": "paragraphs",
            "items": [
                {
                    "text": (
                        "All company data, documents, contacts, pricing, client details, and internal "
                        "information are strictly confidential. Any unauthorized sharing or misuse is a "
                        "serious violation and may result in immediate termination, financial penalties, "
                        "recovery of damages, and legal action under applicable laws"
                    ),
                    "quoted": False,
                    "children": [],
                },
            ],
        },
    ],
}


def get_hr_policies(db: Session) -> HrPoliciesDocument:
    row = db.query(SystemConfig).filter(SystemConfig.key == HR_POLICIES_KEY).one_or_none()
    if row and isinstance(row.value, dict):
        try:
            return HrPoliciesDocument.model_validate(row.value)
        except Exception:
            return HrPoliciesDocument.model_validate(DEFAULT_HR_POLICIES)
    return HrPoliciesDocument.model_validate(DEFAULT_HR_POLICIES)


def save_hr_policies(
    db: Session, auth: AuthContext, document: HrPoliciesDocument
) -> HrPoliciesDocument:
    payload = document.model_dump()
    existing = db.query(SystemConfig).filter(SystemConfig.key == HR_POLICIES_KEY).one_or_none()
    before = existing.value if existing and isinstance(existing.value, dict) else None
    if existing is None:
        db.add(SystemConfig(key=HR_POLICIES_KEY, value=payload, updated_by=auth.user_id))
    else:
        existing.value = payload
        existing.updated_by = auth.user_id
        flag_modified(existing, "value")
    audit_service.log_from_auth(
        db,
        auth,
        action="hr_policies.updated",
        entity_type="system_config",
        before_state={"welcome_title": (before or {}).get("welcome_title")} if before else None,
        after_state={"welcome_title": payload.get("welcome_title"), "sections": len(payload.get("sections") or [])},
    )
    return document
