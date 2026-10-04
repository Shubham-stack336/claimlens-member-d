# ClaimLens: known limitations

ClaimLens is a 30-hour hackathon prototype. It gives evidence, not legal advice, and it can be wrong.

## Data and evaluation
- **Synthetic data only.** The policy and all rejection letters in `eval/` were written by the team for testing. They are not real insurer documents.
- **The eval set is small (9 cases)** and the extraction rules were written while looking at these same letters, so extraction scores on this set are optimistic. Real letters will be worded differently and scores will be lower.
- **Gold labels are our own judgement** on a synthetic policy, not a legal opinion.
- **Retrieval and verdict metrics** are only reported when the pipeline's predictions are passed to `python -m eval.run --predictions`. Otherwise they are shown as "not measured".
- **The injected-fault benchmark** uses a fixed set of fabricated quotes. Catching all of them shows the grounding gate works on these kinds of fakes, not that the verifier catches every possible hallucination. The default run uses a simple exact-match check; the real number comes from running it with the verifier's `locate_quote`.

## Extraction
- Letter and policy extraction use regular expressions and keywords. Unusual wording, tables, or scanned PDFs may give empty or wrong fields. Every policy fact is shown to the user to confirm or correct before the rule checks use it.
- Reason categories are found by keywords. A reason that mentions two categories gets the first match in a fixed order (pre-existing, waiting period, missing documents, limit, exclusion). Anything else goes to a human.
- Only English, and only day-first Indian date formats.

## Rule checks
- Waiting periods are counted from the first-policy inception date with calendar months; a policy that counts differently (for example, 30-day months) needs a corrected fact.
- Continuity of cover, portability, and moratorium rules are not modelled.

## Privacy and security
- PII masking uses patterns for phone numbers, email, Aadhaar-like and PAN-like numbers. It will miss names, addresses and anything in an unusual format, and it may mask a harmless 10- or 12-digit number.
- Upload validation checks extension, size and the `%PDF-` header. It does not scan PDFs for malicious content.
- Uploaded files are purged after a retention window (24 hours by default). There is no authentication, so anyone with a case link could view it before then.

## Not done
- No authentication, no scaling, no compliance testing, weak or no OCR, health insurance only.
