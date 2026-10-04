"""Heuristic extraction of the policy facts the rule checks need.

Policies are worded very differently, so every fact keeps the snippet it was
read from and is shown to the user to confirm or correct (US3). A fact that
cannot be found is left as None rather than guessed.
"""

import re
from dataclasses import asdict, dataclass, field, fields
from datetime import date
from decimal import Decimal

from .letter import AMOUNT_TEXT, DATE_TEXT
from .parsers import parse_indian_date, parse_inr_amount


@dataclass
class Fact:
    value: object
    unit: str | None = None
    start: int | None = None  # character span of the source snippet
    end: int | None = None
    snippet: str | None = None
    confirmed_by_user: bool = False


@dataclass
class PolicyFacts:
    policy_number: Fact | None = None
    first_inception_date: Fact | None = None
    period_start: Fact | None = None
    period_end: Fact | None = None
    sum_insured: Fact | None = None
    initial_waiting: Fact | None = None
    specified_disease_waiting: Fact | None = None
    pre_existing_waiting: Fact | None = None
    room_rent_limit_per_day: Fact | None = None
    notes: list = field(default_factory=list)

    def to_dict(self) -> dict:
        def clean(v):
            if isinstance(v, (date, Decimal)):
                return str(v)
            if isinstance(v, dict):
                return {k: clean(x) for k, x in v.items()}
            if isinstance(v, list):
                return [clean(x) for x in v]
            return v
        return clean(asdict(self))


PATTERNS = {
    "policy_number": re.compile(r"Policy\s*(?:No\b\.?|Number)\s*[:\-]?\s*([A-Z0-9][A-Z0-9/\-]+)", re.I),
    "first_inception_date": re.compile(
        rf"(?:First\s+)?(?:Policy\s+)?Inception\s+Date\s*[:\-]?\s*({DATE_TEXT})", re.I
    ),
    "sum_insured": re.compile(rf"Sum\s+Insured\s*[:\-]?\s*({AMOUNT_TEXT})", re.I),
}
PERIOD = re.compile(
    rf"Policy\s+Period\s*[:\-]?\s*(?:From\s+)?({DATE_TEXT})\s*(?:to|till|until|-)\s*({DATE_TEXT})", re.I
)
DURATION = re.compile(r"(\d+)\s*(days?|months?|years?)\b", re.I)
PERCENT_OF_SI = re.compile(r"(\d+(?:\.\d+)?)\s*%\s*of\s+(?:the\s+)?sum\s+insured", re.I)
LINE = re.compile(r"[^\n]+")


def _fact(value, m: re.Match, text: str, unit: str | None = None, group: int = 0) -> Fact:
    start, end = m.span(group)
    return Fact(value=value, unit=unit, start=start, end=end, snippet=text[start:end].strip())


def _waiting_kind(line: str) -> str | None:
    lower = line.lower()
    if "pre-existing" in lower or "pre existing" in lower:
        return "pre_existing_waiting"
    if "specified" in lower or "specific" in lower:
        return "specified_disease_waiting"
    if "initial" in lower or "first policy commencement" in lower or "first 30 days" in lower:
        return "initial_waiting"
    return None


def extract_policy_facts(text: str) -> PolicyFacts:
    facts = PolicyFacts()

    m = PATTERNS["policy_number"].search(text)
    if m:
        facts.policy_number = _fact(m.group(1), m, text)

    for name, parse in (("first_inception_date", parse_indian_date), ("sum_insured", parse_inr_amount)):
        m = PATTERNS[name].search(text)
        if m:
            try:
                unit = "INR" if name == "sum_insured" else None
                setattr(facts, name, _fact(parse(m.group(1)), m, text, unit=unit))
            except ValueError:
                facts.notes.append(f"Found {name} but could not parse {m.group(1)!r}")

    m = PERIOD.search(text)
    if m:
        try:
            facts.period_start = _fact(parse_indian_date(m.group(1)), m, text)
            facts.period_end = _fact(parse_indian_date(m.group(2)), m, text)
        except ValueError:
            facts.notes.append("Found a policy period but could not parse its dates")

    # Waiting periods: one line at a time, keep the first duration on the line.
    for line in LINE.finditer(text):
        line_text = line.group(0)
        if "waiting period" not in line_text.lower() and "first policy commencement" not in line_text.lower():
            continue
        kind = _waiting_kind(line_text)
        duration = DURATION.search(line_text)
        if kind is None or duration is None or getattr(facts, kind) is not None:
            continue
        amount, unit = int(duration.group(1)), duration.group(2).lower()
        if not unit.endswith("s"):
            unit += "s"
        setattr(facts, kind, Fact(
            value=amount, unit=unit, start=line.start(), end=line.end(), snippet=line_text.strip()
        ))

    # Room rent: either a rupee amount or a percentage of the sum insured.
    for line in LINE.finditer(text):
        line_text = line.group(0)
        if "room rent" not in line_text.lower():
            continue
        pct = PERCENT_OF_SI.search(line_text)
        amount = re.search(AMOUNT_TEXT, line_text)
        value = None
        if pct and facts.sum_insured:
            value = (facts.sum_insured.value * Decimal(pct.group(1)) / 100).quantize(Decimal("1"))
            facts.notes.append(f"Room rent limit computed as {pct.group(1)}% of sum insured")
        elif amount:
            value = parse_inr_amount(amount.group(0))
        if value is not None:
            facts.room_rent_limit_per_day = Fact(
                value=value, unit="INR/day", start=line.start(), end=line.end(), snippet=line_text.strip()
            )
            break

    return facts


def apply_corrections(facts: PolicyFacts, corrections: dict) -> PolicyFacts:
    """Apply the user's edits from the confirm-facts form (US3).

    corrections maps a fact name to its new value, e.g. {"pre_existing_waiting": 48}.
    Edited facts are marked confirmed_by_user so the audit trail shows who decided.
    """
    known = {f.name for f in fields(PolicyFacts)} - {"notes"}
    for name, value in corrections.items():
        if name not in known:
            raise KeyError(f"Unknown policy fact: {name}")
        current = getattr(facts, name)
        if current is None:
            setattr(facts, name, Fact(value=value, confirmed_by_user=True))
        else:
            current.value = value
            current.confirmed_by_user = True
    return facts
