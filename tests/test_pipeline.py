from __future__ import annotations

import unittest

from mva_solver.models import ClinVarRecord, VariantCall
from mva_solver.pipeline import _clinvar_score, _phase_pair


def call(pgt: str | None, pid: str | None) -> VariantCall:
    return VariantCall(
        chrom="1",
        pos=100,
        variant_id=".",
        ref="A",
        alt="G",
        qual=100.0,
        filters="PASS",
        genotype="0/1",
        ad_ref=10,
        ad_alt=10,
        depth=20,
        genotype_quality=99,
        phased_genotype=pgt,
        phase_set=pid,
    )


class PhasePairTest(unittest.TestCase):
    def test_unknown_phase_is_not_rejected(self) -> None:
        status, _, adjustment = _phase_pair(call(None, None), call(None, None))
        self.assertEqual(status, "unphased")
        self.assertEqual(adjustment, 0.0)

    def test_shared_pid_resolves_trans(self) -> None:
        status, _, adjustment = _phase_pair(call("0|1", "block"), call("1|0", "block"))
        self.assertEqual(status, "trans")
        self.assertGreater(adjustment, 0)

    def test_shared_pid_resolves_cis(self) -> None:
        status, _, adjustment = _phase_pair(call("0|1", "block"), call("0|1", "block"))
        self.assertEqual(status, "cis")
        self.assertLess(adjustment, 0)

    def test_different_phase_blocks_are_unknown(self) -> None:
        status, _, _ = _phase_pair(call("0|1", "one"), call("1|0", "two"))
        self.assertEqual(status, "unphased")


def clinvar(significance: str) -> ClinVarRecord:
    return ClinVarRecord(
        chrom="1",
        pos=100,
        ref="A",
        alt="G",
        variation_id="1",
        allele_id="1",
        significance=significance,
        review_status="criteria_provided",
        conditions="synthetic",
        hgvs="synthetic",
    )


class ClinVarScoreTest(unittest.TestCase):
    def test_pathogenic_label_scores_positive(self) -> None:
        self.assertEqual(_clinvar_score([clinvar("Pathogenic/Likely_pathogenic")]), 80.0)

    def test_conflicting_pathogenicity_does_not_score_as_pathogenic(self) -> None:
        self.assertEqual(
            _clinvar_score([clinvar("Conflicting_classifications_of_pathogenicity")]),
            0.0,
        )

    def test_benign_label_scores_negative(self) -> None:
        self.assertEqual(_clinvar_score([clinvar("Likely_benign")]), -100.0)

    def test_uncertain_label_has_small_support_only(self) -> None:
        self.assertEqual(_clinvar_score([clinvar("Uncertain_significance")]), 5.0)


if __name__ == "__main__":
    unittest.main()
