#!/usr/bin/env python3
"""Exercise a submission against the pinned public scorer with synthetic gold.

This checks formatting and exact tuple representation only. It deliberately does
not claim that the challenge's private answer key matches the submission.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sys
from pathlib import Path


PINNED_SPACE_REVISION = "d27c33953ecb0cfd7fa316c7cd93ff0ffb05cc1d"
PINNED_EVALUATOR_SHA256 = "6d18b581e65a45e1ccc120071d588e740c2e42e983ff50704c60a40232b19180"


def load_evaluator(path: Path):
    observed_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    if observed_sha256 != PINNED_EVALUATOR_SHA256:
        raise ValueError(
            "Official evaluator checksum mismatch: "
            f"expected {PINNED_EVALUATOR_SHA256}, observed {observed_sha256}"
        )
    spec = importlib.util.spec_from_file_location("mva_official_evaluation", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import evaluator from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument(
        "--evaluator",
        type=Path,
        default=Path("official_challenge_space/evaluation.py"),
    )
    args = parser.parse_args()

    evaluator = load_evaluator(args.evaluator)
    submissions = evaluator.load_submission(str(args.submission))
    if set(submissions) != {"PROBAND01"}:
        raise ValueError(f"Expected only PROBAND01, observed {sorted(submissions)}")
    rows = submissions["PROBAND01"]
    if len(rows) != 1 or len(rows[0].variants) != 2:
        raise ValueError("Ceiling-targeting artifact must contain exactly one paired row")

    synthetic_gold = rows[0].variants
    result = evaluator.score_proband("PROBAND01", rows, synthetic_gold)
    if result.rank_points != 100.0 or result.f_max != 1.0:
        raise AssertionError(result)
    print(
        "official_contract_ok "
        f"space_revision={PINNED_SPACE_REVISION} rank_points=100.0 f_max=1.0 "
        "gold=synthetic_from_submission"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
