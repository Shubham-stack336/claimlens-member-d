# ClaimLens: rules, extraction, safety and evaluation (Member D)

Deterministic, unit-tested code around the AI pipeline. No LLM is used in this part.

| Module | What it does |
|---|---|
| `claimlens_docs/parsers.py` | `parse_indian_date` (day first), `parse_inr_amount` ("Rs. 1,25,000/-") |
| `claimlens_docs/rules/checks.py` | `waiting_period_elapsed`, `event_within_policy_period`, `amount_within_limit` |
| `claimlens_docs/letter.py` | Claim/policy numbers, dates, amount and each rejection reason (with text span and category) |
| `claimlens_docs/policy_facts.py` | Policy period, inception, sum insured, waiting periods, room-rent limit; user corrections |
| `claimlens_docs/security/` | `redact` (PII masking), `validate_upload` (PDF, magic bytes, 10 MB), `purge_expired` |
| `eval/` | 9 synthetic cases with gold labels, metrics, injected-fault benchmark, `report.json` |

## Setup

```bash
pip install pytest           # the code itself uses only the standard library
pytest -q                    # unit tests
python -m eval.run           # evaluation report
python -m eval.demo_rules    # rule checks on the synthetic cases
```

Measuring the full pipeline:

```bash
python -m eval.run --predictions eval/predictions.json --grounding claimlens_docs.grounding:locate_quote
```

`predictions.json` format, one entry per case, one item per rejection reason in order:

```json
{"case_01": {"reasons": [{"retrieved_clause_ids": ["4.2", "6.2", "4.1"], "verdict": "SUPPORTED"}]}}
```

The grounding function must take `(quote, policy_text)` and return true if the quote is found.

See [LIMITATIONS.md](LIMITATIONS.md). All data here is synthetic.
