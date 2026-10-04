# ClaimLens: document intelligence, grounding, evaluation and deployment (Member 4)

Turns PDFs into structured data the rest of ClaimLens can trust, proves that cited clauses really exist,
and measures the system on synthetic cases. No LLM is used in this package.

## What the backend calls (contract 4.3 / 4.5)

```python
from claimlens_docs import (
    ingest_document,       # (path, doc_id, doc_type) -> ParsedDocument
    extract_rejection,     # (ParsedDocument) -> RejectionExtraction, every reason with page + bbox
    extract_policy_facts,  # (ParsedDocument) -> PolicyFacts, every fact with its source chunk_id
    sanitize_for_llm,      # (text) -> SanitizedText: PII masked, injection flags, delimited for the prompt
    locate_quote,          # (doc or doc_id, quote) -> LocateResult {found, match_score, page, bbox, chunk_id}
)
from claimlens_docs.rules import waiting_period_elapsed, event_within_policy_period, amount_within_limit
```

The Pydantic models are in `claimlens_docs/schemas.py` and mirror `contracts/schemas.py`. Extra fields are optional.

## Modules

| Module | What it does |
|---|---|
| `ingest.py` | PyMuPDF: lines with bounding boxes, reading order, pages with no text layer |
| `structure.py` | Sectionizer: one chunk per clause, `section_path` like `4 Waiting Periods > 4.2`, tags `WAITING_PERIOD` / `EXCLUSION` / `DEFINITION` |
| `grounding.py` | `locate_quote`: exact, then fuzzy (rapidfuzz) match; rejects a close match if any number or meaning word (`not`, `only`, `excluded`, `covered`...) differs |
| `letter.py` | Claim/policy numbers, dates, amounts, each rejection reason with category, clause refs, page and bbox |
| `policy_facts.py` | Policy period, inception, sum insured, waiting periods, room-rent limit; user corrections |
| `parsers.py` | Day-first Indian dates, "Rs. 1,25,000/-" amounts |
| `rules/checks.py` | `waiting_period_elapsed`, `event_within_policy_period`, `amount_within_limit`; `RuleResult.to_dict()` gives the contract shape |
| `security/` | `redact` (PII), `validate_upload` (PDF magic bytes, 10 MB), `detect_injection` + `wrap_as_data` + `sanitize_for_llm`, `purge_expired` (TTL) |
| `eval/` | 9 synthetic cases (3 supported), metrics, injected-fault benchmark, PDF rendering, fixtures, `--gate` for CI |
| `deploy/`, `docker-compose.yml` | Dockerfiles (non-root, healthchecks), Postgres 16 + pgvector, Render blueprint |

## Setup

```bash
pip install -e ".[dev]"
pytest -q                      # unit + end-to-end PDF tests
ruff check . && mypy claimlens_docs
python -m eval.run             # evaluation report -> eval/report.json
python -m eval.run --gate      # same, exits 1 if any metric is below target (used in CI)
python -m eval.make_pdfs       # render the synthetic policy and letters to eval/data/pdf/
python -m eval.make_fixtures   # regenerate fixtures/*.json for contracts/fixtures/
python -m eval.demo_rules      # rule checks on the synthetic cases
```

Measuring the full pipeline (retrieval recall@3 and verdict agreement need M3's output):

```bash
python -m eval.run --predictions eval/predictions.json
```

`predictions.json` format, one entry per case, one item per rejection reason in order:

```json
{"case_01": {"reasons": [{"retrieved_clause_ids": ["4.2", "6.2", "4.1"], "verdict": "SUPPORTED"}]}}
```

`--grounding exact` runs the benchmark with the old exact-match check for comparison; `--grounding module:fn`
plugs in any `(quote, policy_text) -> bool` function.

## Current results (synthetic data, 9 cases)

Produced by `python -m eval.run` on this commit. Exact counts on a small synthetic set, not general accuracy.

| Metric | Result |
|---|---|
| Letter extraction matches gold (text) | 9 of 9 |
| Letter extraction matches gold (rendered PDF → ingest → extract) | 9 of 9 |
| Policy facts match gold | 9 of 9 |
| Fabricated citations caught by `locate_quote` | 34 of 34 |
| Real quotes accepted (verbatim, reformatted, one-letter typo) | 42 of 42 |
| Retrieval recall@3, verdict agreement | not measured until M3's predictions are passed |

With the exact-match check instead, the same benchmark accepts only 18 of 42 real quotes, which is why grounding is fuzzy.

## Deployment

`docker-compose.yml` and `deploy/Dockerfile.backend|frontend`, `deploy/render.yaml` are written for the monorepo layout
(`backend/`, `frontend/`, `ai/`, `docint/`, `contracts/`). In this repo, `docker compose up db` starts Postgres with
pgvector, and `deploy/Dockerfile.docs` builds and runs the tests and eval gate. Copy `.env.example` to `.env` first.

See [LIMITATIONS.md](LIMITATIONS.md). All data here is synthetic.
