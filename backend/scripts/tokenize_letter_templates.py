"""One-shot: turn sample-filled official letters into {{placeholder}} templates."""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

from app.reporting.employee_letters import _iter_paragraphs, _set_paragraph_text

ROOT = Path(__file__).resolve().parents[1] / "config" / "letter_templates"

SALARY_PARA = (
    "Your Monthly Total Employment Cost to the company would be "
    "Rs{{salary_rs}}/= (Rupees {{salary_words}} rupees Only.), "
    "Breakup of salary will be Rs.{{salary_rs}}/= Basic Salary Rs.{{salary_basic}}/= "
    "Accommodation/House Rent, Rs.{{salary_hra}}/=, Fuel Medical & Mobile Expense "
    "{{salary_allowance}} (PERSONAL AND OFFICIAL) respectively."
)

APPOINTMENT_REPLACEMENTS = [
    (
        "Your Monthly Total Employment Cost to the company would be Rs195,000/= "
        "(Rupees One Lack Ninety Five Thousand rupees Only.), Breakup of salary will be "
        "Rs.195,000/= Basic Salary Rs.120,000/= Accommodation/House Rent, Rs.45,000/=, "
        "Fuel Medical & Mobile Expense 30,000 (PERSONAL AND OFFICIAL) respectively.",
        SALARY_PARA,
    ),
    ("January 01, 2026", "{{dated}}"),
    ("01-January-2026", "{{date_joined_long}}"),
    ("42301-0279498-1", "{{cnic}}"),
    ("Mr. Amir Ahmed Durrani", "{{honorific}} {{full_name}}"),
    ("S/o. Mr. Atta Muhammad", "{{filiation}} {{father_honorific}} {{father_name}}"),
    ("as a Sales & Marketing", "as {{a_or_an}} {{role_title}}"),
    ("Sales & Marketing", "{{role_title}}"),
]

CONTRACT_REPLACEMENTS = [
    (
        "Your Monthly Total Employment Cost to the company would be Rs195,000/= "
        "(Rupees One Lack Ninety Five Thousand rupees Only.), Breakup of salary will be "
        "Rs.195,000/= Basic Salary Rs.120,000/= Accommodation/House Rent, Rs.45,000/=, "
        "Fuel Medical & Mobile Expense 30,000 (PERSONAL AND OFFICIAL) respectively.",
        SALARY_PARA,
    ),
    ("January 05, 2026", "{{dated}}"),
    ("05-Januairy 2026", "{{date_joined_contract}}"),
    ("05-Jan-2026", "{{date_joined_short}}"),
    ("42301-0279498-1", "{{cnic}}"),
    ("Mr. Amir Ahmed Durrani", "{{honorific}} {{full_name}}"),
    ("S/o. Mr. Mr. Atta Muhammad", "{{filiation}} {{father_honorific}} {{father_name}}"),
    ("Amir Ahmed Durrani", "{{full_name}}"),
    ("a International Sales & Marketing", "{{a_or_an}} {{role_title}}"),
    ("International Sales & Marketing", "{{role_title}}"),
    ("0330-8252974", "{{phone_and_email}}"),
    ("1. Asad Khan (Manager International business) = (03480254656)", "{{ref_pro_1}}"),
    ("2. Adeel Ahmed (Sales & Marketing Manager) = (03158180454)", "{{ref_pro_2}}"),
    ("3. Syed Javeer Abid (sales Coordinator) = (03366756958", "{{ref_pro_3}}"),
    ("1.Saira Kanwal (Mother) = (03427700007)", "{{ref_blood_1}}"),
]


def _apply(path: Path, replacements: list[tuple[str, str]]) -> None:
    doc = Document(str(path))
    for paragraph in _iter_paragraphs(doc):
        text = paragraph.text
        if not text.strip():
            continue
        updated = text
        compact = " ".join(text.split())
        if "Monthly Total Employment Cost" in compact and "195" in compact:
            trailing = " " if text.endswith(" ") else ""
            updated = SALARY_PARA + trailing
        else:
            for old, new in replacements:
                if old in updated:
                    updated = updated.replace(old, new)
        if updated != text:
            _set_paragraph_text(paragraph, updated)
    for node in doc.element.iter(qn("w:t")):
        if not node.text:
            continue
        updated = node.text
        for old, new in replacements:
            if old in updated:
                updated = updated.replace(old, new)
        if updated != node.text:
            node.text = updated
    doc.save(str(path))
    print("tokenized", path.name)


def main() -> None:
    _apply(ROOT / "appointment_letter.docx", APPOINTMENT_REPLACEMENTS)
    _apply(ROOT / "employment_contract.docx", CONTRACT_REPLACEMENTS)


if __name__ == "__main__":
    main()
