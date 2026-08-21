"""Gemini narrative summary for a computed salary sheet (incl. payment modes)."""
from __future__ import annotations

import logging
from calendar import month_name
from collections import Counter
from dataclasses import dataclass

from app.core.config import Settings
from app.core.exceptions import BusinessRuleViolation
from app.core.gemini_client import generate_content_with_fallback
from app.schemas.payroll import PayrollComputeResult
from app.services.payroll_service import _normalize_payment_mode

logger = logging.getLogger(__name__)


@dataclass
class PayrollAiSummaryResult:
    period_month: int
    period_year: int
    payment_mode_counts: dict[str, int]
    employee_count: int
    total_net_payable: float
    summary_text: str


def payment_mode_counts(result: PayrollComputeResult) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for emp in result.employees:
        counts[_normalize_payment_mode(emp.payment_mode)] += 1
    return {
        "IBFT": int(counts.get("IBFT", 0)),
        "Cash": int(counts.get("Cash", 0)),
        "Cheque": int(counts.get("Cheque", 0)),
    }


def _facts_block(result: PayrollComputeResult, modes: dict[str, int]) -> str:
    total_net = sum(float(e.net_payable or 0) for e in result.employees)
    total_gross = sum(float(e.gross_salary or 0) for e in result.employees)
    total_tax = sum(float(e.monthly_tax or 0) for e in result.employees)
    month_label = f"{month_name[result.period_month]} {result.period_year}"
    company = (result.company_name or "Kafi Commodities").strip()
    lines = [
        f"Company: {company}",
        f"Period: {month_label}",
        f"Employees on sheet: {len(result.employees)}",
        f"Total gross salary: {total_gross:,.2f}",
        f"Total monthly tax: {total_tax:,.2f}",
        f"Total net payable: {total_net:,.2f}",
        "Payment mode counts (use these exact numbers):",
        f"- IBFT: {modes['IBFT']}",
        f"- Cash: {modes['Cash']}",
        f"- Cheque: {modes['Cheque']}",
    ]
    # Compact per-mode net totals for the model
    by_mode_net: dict[str, float] = {"IBFT": 0.0, "Cash": 0.0, "Cheque": 0.0}
    for emp in result.employees:
        mode = _normalize_payment_mode(emp.payment_mode)
        by_mode_net[mode] = by_mode_net.get(mode, 0.0) + float(emp.net_payable or 0)
    lines.append("Net payable by payment mode:")
    for mode in ("IBFT", "Cash", "Cheque"):
        lines.append(f"- {mode}: {by_mode_net[mode]:,.2f}")
    return "\n".join(lines)


def generate_payroll_ai_summary(
    result: PayrollComputeResult, settings: Settings
) -> PayrollAiSummaryResult:
    api_keys = settings.resolved_gemini_payroll_api_keys()
    if not api_keys:
        raise BusinessRuleViolation(
            "Payroll AI summary is not configured. Set GEMINI_PAYROLL_API_KEY "
            "(or GEMINI_API_KEY as fallback)."
        )

    modes = payment_mode_counts(result)
    facts = _facts_block(result, modes)
    month_label = f"{month_name[result.period_month]} {result.period_year}"

    prompt = f"""You are an HR payroll analyst for a Pakistani commodities company.
Write a clear, professional salary-sheet summary report for management.

Use ONLY the facts below. Do not invent employees, amounts, or payment counts.
Always include a dedicated "Payment mode summary" section with the IBFT / Cash / Cheque
headcounts and their net payable totals exactly as given.

Facts:
{facts}

Output structure (plain text, no markdown tables):
1) Title line: Salary sheet summary — {month_label}
2) Overview (2–4 sentences: headcount, total gross, total tax, total net)
3) Payment mode summary (IBFT / Cash / Cheque counts + net by mode)
4) Brief notes / next steps (1–3 short bullets for finance prep, e.g. IBFT batching)

Tone: calm, precise, back-office. No fluff. Currency as PKR figures already given.
"""

    try:
        response = generate_content_with_fallback(
            prompt=prompt,
            api_keys=api_keys,
            models=settings.resolved_gemini_payroll_models(),
            pool_id="payroll_summary",
        )
        text = (getattr(response, "text", None) or "").strip()
    except Exception as exc:
        logger.exception("Payroll AI summary failed")
        raise BusinessRuleViolation(f"Could not generate payroll AI summary: {exc}") from exc

    if not text:
        raise BusinessRuleViolation("Payroll AI summary returned empty text")

    total_net = sum(float(e.net_payable or 0) for e in result.employees)
    return PayrollAiSummaryResult(
        period_month=result.period_month,
        period_year=result.period_year,
        payment_mode_counts=modes,
        employee_count=len(result.employees),
        total_net_payable=round(total_net, 2),
        summary_text=text,
    )
