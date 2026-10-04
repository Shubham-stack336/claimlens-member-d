"""Pydantic models for the claimlens_docs side of the shared contract.

These mirror contracts/schemas.py (work division, section 4.1). Field names
and types follow the frozen contract; anything extra is optional, so adding
it is an allowed additive change. When this package moves into the monorepo,
replace these classes with imports from contracts.schemas.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

BBox = list[float]  # [x0, y0, x1, y1] in PDF points, origin top-left


class Chunk(BaseModel):
    chunk_id: str
    doc_id: str
    section_path: str
    page: int  # 1-based
    text: str
    bbox: BBox
    tags: list[str] = []  # WAITING_PERIOD, EXCLUSION, DEFINITION


class ParsedDocument(BaseModel):
    doc_id: str
    doc_type: Literal["policy", "letter"]
    n_pages: int
    has_text_layer: bool
    chunks: list[Chunk]
    # Optional additions
    pages_without_text: list[int] = []


class RejectionReason(BaseModel):
    reason_id: str
    text: str
    category: str
    page: int
    bbox: BBox
    # Optional additions
    clause_refs: list[str] = []


class RejectionExtraction(BaseModel):
    claim_no: str | None = None
    policy_no: str | None = None
    admission_date: date | None = None
    discharge_date: date | None = None
    claimed_amount: float | None = None
    rejected_amount: float | None = None
    reasons: list[RejectionReason] = []
    # Optional additions
    letter_date: date | None = None


class WaitingPeriod(BaseModel):
    kind: str  # initial, specified_disease, pre_existing
    months: int  # a "30 days" wait is rounded to 1 month; use days when it is set
    chunk_id: str | None = None
    # Optional additions
    days: int | None = None  # set only when the policy states the wait in days


class PolicyFacts(BaseModel):
    policy_start: date | None = None
    policy_end: date | None = None
    sum_insured: float | None = None
    waiting_periods: list[WaitingPeriod] = []
    confirmed_by_user: bool = False
    # Optional additions
    policy_no: str | None = None
    first_inception_date: date | None = None  # waiting periods count from this date
    room_rent_limit_per_day: float | None = None
    source_chunk_ids: dict[str, str] = {}  # fact name -> chunk it was read from
    notes: list[str] = []


class LocateResult(BaseModel):
    found: bool
    match_score: float  # 0..1
    page: int | None = None
    bbox: BBox | None = None
    chunk_id: str | None = None
    # Optional additions
    matched_text: str | None = None
    reason: str | None = None  # why a close match was still rejected


class InjectionFlag(BaseModel):
    pattern: str
    start: int
    end: int
    snippet: str


class SanitizedText(BaseModel):
    text: str  # PII masked; send this, wrapped by `delimited`, to the LLM
    delimited: str  # text wrapped in data delimiters, ready to paste into a prompt
    redactions: dict[str, int] = Field(default_factory=dict)
    injection_flags: list[InjectionFlag] = []

    @property
    def suspicious(self) -> bool:
        return bool(self.injection_flags)
