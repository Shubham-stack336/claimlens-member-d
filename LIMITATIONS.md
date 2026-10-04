# ClaimLens: known limitations

ClaimLens is a 30-hour hackathon prototype. It gives evidence, not legal advice, and it can be wrong.

## Data and evaluation
- **Synthetic data only.** The policy and all rejection letters in `eval/` were written by the team for testing. They are not real insurer documents.
- **The eval set is small (9 cases)** and the extraction rules were written while looking at these same letters, so extraction scores on this set are optimistic. Real letters will be worded differently and scores will be lower.
- **Gold labels are our own judgement** on a synthetic policy, not a legal opinion.
- **Retrieval and verdict metrics** are only reported when the pipeline's predictions are passed to `python -m eval.run --predictions`. Otherwise they are shown as "not measured".
- **The injected-fault benchmark** uses a fixed set of fabricated quotes (invented, number changed, meaning flipped, two clauses spliced) and real quotes with harmless changes. Catching all of them shows the grounding gate works on these kinds of fakes, not that the verifier catches every possible hallucination. A fabricated quote that changes only an ordinary word (not a number or a word such as "not", "only", "excluded") and stays above 90% similar would be accepted.
- **PDF tests use PDFs we render ourselves** from the synthetic text (`eval/make_pdfs.py`). Real insurer PDFs with columns, tables, headers and footers will be harder to sectionize.

## Extraction
- Letter and policy extraction use regular expressions and keywords. Unusual wording, tables, or scanned PDFs may give empty or wrong fields. Every policy fact is shown to the user to confirm or correct before the rule checks use it.
- Reason categories are found by keywords. A reason that mentions two categories gets the first match in a fixed order (pre-existing, waiting period, missing documents, limit, exclusion). Anything else goes to a human.
- Only English, and only day-first Indian date formats.

## Ingestion and grounding
- Scanned pages are detected (`pages_without_text`, `has_text_layer`) but not read: there is no OCR.
- Sections are found by numbering, heading font size and all-caps lines. Two-column layouts, tables and running headers/footers are not handled and can end up inside a clause chunk.
- Heading lines are not chunks, so a quote of a heading alone is not grounded.
- Highlight boxes cover the whole chunk (clause or line) that contains the quote, not the exact words. A quote that crosses a page break is boxed on its first page only.
- `locate_quote(doc_id, ...)` looks documents up in an in-process registry filled by `ingest_document`; a different worker process must call `register_document` (for example after loading chunks from the database).

## Rule checks
- Waiting periods are counted from the first-policy inception date with calendar months; a policy that counts differently (for example, 30-day months) needs a corrected fact.
- Continuity of cover, portability, and moratorium rules are not modelled.

## Privacy and security
- PII masking uses patterns for phone numbers, email, Aadhaar-like and PAN-like numbers. It will miss names, addresses and anything in an unusual format, and it may mask a harmless 10- or 12-digit number.
- Upload validation checks extension, size and the `%PDF-` header. It does not scan PDFs for malicious content.
- The prompt-injection guard flags common instruction-like phrases and always wraps document text as delimited data. A determined attacker can word instructions that no pattern matches; the delimiters reduce, not remove, that risk.
- Uploaded files are purged after a retention window (24 hours by default). There is no authentication, so anyone with a case link could view it before then.

## Deployment
- The Dockerfiles for the backend and frontend and `render.yaml` target the monorepo layout and have not been built in this repo. Free hosting tiers sleep when idle and may not offer the `vector` extension.

## Not done
- No authentication, no scaling, no compliance testing, no OCR, health insurance only.
