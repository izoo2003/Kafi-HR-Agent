"""CV parsing — PDF/DOCX text + heuristic structured fields."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def _extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        import pdfplumber

        parts: list[str] = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                parts.append(page.extract_text() or "")
        return "\n".join(parts)
    if suffix in {".docx", ".doc"}:
        import docx

        document = docx.Document(str(path))
        return "\n".join(p.text for p in document.paragraphs)
    # Plain text fallback (tests / pasted CVs)
    return path.read_text(encoding="utf-8", errors="ignore")


def _first_email(text: str) -> str | None:
    m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return m.group(0) if m else None


def _first_phone(text: str) -> str | None:
    m = re.search(r"(\+?\d[\d\s\-()]{8,}\d)", text)
    return m.group(1).strip() if m else None


def _guess_name(text: str, email: str | None) -> str | None:
    for line in text.splitlines()[:8]:
        line = line.strip()
        if not line or "@" in line or re.search(r"\d{3,}", line):
            continue
        if 2 <= len(line.split()) <= 5 and len(line) < 60:
            return line
    if email:
        local = email.split("@")[0].replace(".", " ").replace("_", " ")
        return local.title()
    return None


def _guess_skills(text: str) -> list[str]:
    catalog = [
        "Python",
        "FastAPI",
        "Flask",
        "Django",
        "JavaScript",
        "TypeScript",
        "React",
        "SQL",
        "PostgreSQL",
        "MySQL",
        "MongoDB",
        "Docker",
        "Kubernetes",
        "AWS",
        "GCP",
        "Azure",
        "LangChain",
        "LLM",
        "RAG",
        "Machine Learning",
        "Excel",
        "HR",
        "Payroll",
    ]
    lower = text.lower()
    found = [s for s in catalog if s.lower() in lower]
    return found


def _guess_years(text: str) -> float:
    m = re.search(r"(\d+)\+?\s*\+?\s*years?", text, re.I)
    if m:
        return float(m.group(1))
    # crude: count year-like ranges
    ranges = re.findall(r"(20\d{2})\s*[-–]\s*(20\d{2}|present|current)", text, re.I)
    total = 0.0
    for start, end in ranges:
        end_y = 2026 if end.lower() in {"present", "current"} else int(end)
        total += max(0, end_y - int(start))
    return float(total) if total else 0.0


def _guess_education_level(text: str) -> str | None:
    lower = text.lower()
    if "ph.d" in lower or "phd" in lower or "doctorate" in lower:
        return "phd"
    if "master" in lower or "m.s" in lower or "mba" in lower:
        return "masters"
    if "bachelor" in lower or "b.s" in lower or "b.sc" in lower or "bs " in lower:
        return "bachelors"
    if "diploma" in lower:
        return "diploma"
    return None


def parse_cv(file_path: str | Path) -> dict[str, Any]:
    path = Path(file_path)
    if not path.exists():
        return {
            "full_name": None,
            "email": None,
            "phone": None,
            "education": [],
            "experience": [],
            "years_experience": 0.0,
            "skills": [],
            "raw_text": "",
            "education_level": None,
        }

    raw = _extract_text(path)
    email = _first_email(raw)
    phone = _first_phone(raw)
    name = _guess_name(raw, email)
    skills = _guess_skills(raw)
    years = _guess_years(raw)
    level = _guess_education_level(raw)

    education = []
    if level:
        education.append(
            {
                "degree": level,
                "field": "",
                "institution": "",
                "year": None,
                "level": level,
            }
        )

    return {
        "full_name": name,
        "email": email,
        "phone": phone,
        "education": education,
        "experience": [],
        "years_experience": years,
        "skills": skills,
        "raw_text": raw[:50000],
        "education_level": level,
    }
