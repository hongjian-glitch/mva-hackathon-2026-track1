# Official Track 1 contract

Pinned challenge Space revision:
`d27c33953ecb0cfd7fa316c7cd93ff0ffb05cc1d`.

The official evaluator accepts at most ten CSV rows for one proband. A row can
contain either one candidate or one two-variant compound-heterozygous pair.
Rows are sorted by descending EPCR before scoring.

For a two-variant ground truth, a full match requires exact equality of both
variants in the same row. Full-match rank points are 100 at rank 1, 50 at ranks
2–3, 25 at ranks 4–5, and 10 at ranks 6–10. A one-of-two partial match receives
half credit. F-max is the maximum individual-variant F1 across all EPCR
thresholds.

The ceiling is therefore reached by one rank-1 row containing exactly the full
causal pair, with no higher-confidence false-positive row.

Important scorer detail: `finding_type` is parsed but does not exclude a row
from automated scoring. Secondary rows can still change rank and F-max despite
the UI wording.

Official sources:

- https://huggingface.co/spaces/SageBio/rare-disease-real-kid-mva-hackathon-2026/blob/d27c33953ecb0cfd7fa316c7cd93ff0ffb05cc1d/evaluation.py
- https://huggingface.co/spaces/SageBio/rare-disease-real-kid-mva-hackathon-2026/blob/d27c33953ecb0cfd7fa316c7cd93ff0ffb05cc1d/tabs/submit_track1.py
- https://huggingface.co/spaces/SageBio/rare-disease-real-kid-mva-hackathon-2026/blob/d27c33953ecb0cfd7fa316c7cd93ff0ffb05cc1d/static/templates/track1_submission_template.csv

`scripts/fetch_official_evaluator.sh` downloads `evaluation.py` from the
pinned revision and refuses it unless SHA-256 equals
`6d18b581e65a45e1ccc120071d588e740c2e42e983ff50704c60a40232b19180`.
The evaluator mirror is intentionally excluded from version control.
