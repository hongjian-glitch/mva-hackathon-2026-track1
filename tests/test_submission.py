from __future__ import annotations

import csv
import json
import os
import tempfile
import unittest
from pathlib import Path

from mva_solver.submission import FIELDS, build_row, preflight, write_submission


class SubmissionTest(unittest.TestCase):
    @staticmethod
    def analysis(phase_status: str = "unphased") -> dict:
        return {
            "schema_version": "1.0",
            "transcript": {"assembly": "GRCh38"},
            "candidates": [
                {"call": {"chrom": "15", "pos": 100, "ref": "A", "alt": "G"}},
                {"call": {"chrom": "15", "pos": 200, "ref": "C", "alt": "T"}},
            ],
            "ranked_pairs": [
                {
                    "variant_keys": [["15", 100, "A", "G"], ["15", 200, "C", "T"]],
                    "phase_status": phase_status,
                }
            ],
        }

    @staticmethod
    def row(**overrides: str) -> dict[str, str]:
        base = {
            "proband_id": "PROBAND01",
            "chrom_1": "chr15",
            "pos_1": "100",
            "ref_1": "A",
            "alt_1": "G",
            "chrom_2": "chr15",
            "pos_2": "200",
            "ref_2": "C",
            "alt_2": "T",
            "epcr": "0.99",
            "finding_type": "primary",
            "notes": "synthetic",
        }
        base.update(overrides)
        return base

    @staticmethod
    def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    def test_builds_one_compound_heterozygous_row(self) -> None:
        row = build_row(self.analysis())
        self.assertEqual(row["chrom_1"], "chr15")
        self.assertEqual(row["chrom_2"], "chr15")
        self.assertEqual(row["epcr"], "0.99")

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "submission.csv"
            with path.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerow(row)
            self.assertEqual(preflight(path), [])

    def test_preflight_rejects_incomplete_pair(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "submission.csv"
            self.write_rows(path, [self.row(alt_2="")])
            self.assertTrue(any("incomplete" in error for error in preflight(path)))

    def test_preflight_rejects_wrong_proband_and_representation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "submission.csv"
            self.write_rows(
                path,
                [self.row(proband_id="OTHER", chrom_1="15", ref_1="a")],
            )
            errors = preflight(path)
            self.assertTrue(any("PROBAND01" in error for error in errors))
            self.assertTrue(any("canonical" in error for error in errors))
            self.assertTrue(any("uppercase" in error for error in errors))

    def test_preflight_rejects_nan_ties_and_unsorted_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "submission.csv"
            self.write_rows(
                path,
                [
                    self.row(epcr="0.20"),
                    self.row(
                        pos_1="300",
                        pos_2="400",
                        epcr="0.20",
                    ),
                    self.row(pos_1="500", pos_2="600", epcr="nan"),
                    self.row(pos_1="700", pos_2="800", epcr="0.50"),
                ],
            )
            errors = preflight(path)
            self.assertTrue(any("outside" in error for error in errors))
            self.assertTrue(any("unique" in error for error in errors))
            self.assertTrue(any("descending" in error for error in errors))

    def test_preflight_rejects_swapped_duplicate_pair(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "submission.csv"
            self.write_rows(
                path,
                [
                    self.row(epcr="0.99"),
                    self.row(
                        chrom_1="chr15",
                        pos_1="200",
                        ref_1="C",
                        alt_1="T",
                        chrom_2="chr15",
                        pos_2="100",
                        ref_2="A",
                        alt_2="G",
                        epcr="0.50",
                    ),
                ],
            )
            self.assertTrue(any("duplicate prediction" in error for error in preflight(path)))

    @unittest.skipUnless(os.name == "posix", "POSIX mode check")
    def test_written_submission_is_owner_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            analysis_path = Path(temp_dir) / "analysis.json"
            output_path = Path(temp_dir) / "private" / "submission.csv"
            analysis_path.write_text(json.dumps(self.analysis()))
            write_submission(analysis_path, output_path)
            self.assertEqual(output_path.stat().st_mode & 0o777, 0o600)

    def test_builder_propagates_phase_and_rejects_cis(self) -> None:
        trans = build_row(self.analysis("trans"))
        self.assertIn("supports trans", trans["notes"])
        with self.assertRaisesRegex(ValueError, "in cis"):
            build_row(self.analysis("cis"))

    @unittest.skipUnless(os.name == "posix", "POSIX mode check")
    def test_existing_private_directory_is_hardened(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            private_dir = Path(temp_dir) / "private"
            private_dir.mkdir(mode=0o755)
            private_dir.chmod(0o755)
            analysis_path = Path(temp_dir) / "analysis.json"
            analysis_path.write_text(json.dumps(self.analysis()))
            write_submission(analysis_path, private_dir / "submission.csv")
            self.assertEqual(private_dir.stat().st_mode & 0o777, 0o700)


if __name__ == "__main__":
    unittest.main()
