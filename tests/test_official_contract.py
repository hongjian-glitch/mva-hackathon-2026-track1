from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from mva_solver.submission import FIELDS
from scripts.check_official_scorer import load_evaluator


EVALUATOR = Path("official_challenge_space/evaluation.py")


@unittest.skipUnless(EVALUATOR.exists(), "pinned official Space mirror is not present")
class OfficialScorerContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evaluator = load_evaluator(EVALUATOR)
        cls.truth = frozenset(
            {
                ("chr1", 100, "A", "G"),
                ("chr1", 200, "C", "T"),
            }
        )

    @staticmethod
    def row(**overrides: str) -> dict[str, str]:
        row = {
            "proband_id": "PROBAND01",
            "chrom_1": "chr1",
            "pos_1": "100",
            "ref_1": "A",
            "alt_1": "G",
            "chrom_2": "chr1",
            "pos_2": "200",
            "ref_2": "C",
            "alt_2": "T",
            "epcr": "0.99",
            "finding_type": "primary",
            "notes": "synthetic fixture",
        }
        row.update(overrides)
        return row

    def score(self, rows: list[dict[str, str]]):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "submission.csv"
            with path.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(rows)
            loaded = self.evaluator.load_submission(str(path))["PROBAND01"]
            return self.evaluator.score_proband("PROBAND01", loaded, self.truth)

    def test_exact_pair_at_rank_one_reaches_ceiling(self) -> None:
        result = self.score([self.row()])
        self.assertEqual(result.rank_points, 100.0)
        self.assertEqual(result.f_max, 1.0)

    def test_pair_order_is_irrelevant(self) -> None:
        result = self.score(
            [
                self.row(
                    pos_1="200",
                    ref_1="C",
                    alt_1="T",
                    pos_2="100",
                    ref_2="A",
                    alt_2="G",
                )
            ]
        )
        self.assertEqual(result.rank_points, 100.0)
        self.assertEqual(result.f_max, 1.0)

    def test_chromosome_prefix_mismatch_fails_exact_match(self) -> None:
        result = self.score([self.row(chrom_1="1", chrom_2="1")])
        self.assertEqual(result.rank_points, 0.0)
        self.assertEqual(result.f_max, 0.0)

    def test_false_row_above_truth_reduces_both_metrics(self) -> None:
        false_row = self.row(
            pos_1="300",
            alt_1="T",
            pos_2="400",
            alt_2="A",
            epcr="1.0",
            finding_type="secondary",
        )
        result = self.score([false_row, self.row(epcr="0.9")])
        self.assertEqual(result.rank_points, 50.0)
        self.assertLess(result.f_max, 1.0)

    def test_evaluator_checksum_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "evaluation.py"
            path.write_text("# not the pinned evaluator\n")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                load_evaluator(path)


if __name__ == "__main__":
    unittest.main()
