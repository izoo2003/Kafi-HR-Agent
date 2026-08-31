"""HR policies document stored in system_config (`hr.policies`)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


HrPolicyIcon = Literal["documents", "timings", "sop", "leave", "confidentiality"]
HrPolicyListStyle = Literal["ol", "ul", "paragraphs"]


class HrPolicyItem(BaseModel):
    text: str = Field(min_length=1)
    quoted: bool = False
    children: list[str] = []


class HrPolicySection(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    icon: HrPolicyIcon
    status: str = "info"
    list_style: HrPolicyListStyle = "ul"
    items: list[HrPolicyItem] = Field(min_length=1)


class HrPoliciesDocument(BaseModel):
    welcome_title: str = Field(min_length=1)
    welcome_subtitle: str = ""
    sections: list[HrPolicySection] = Field(min_length=1)
