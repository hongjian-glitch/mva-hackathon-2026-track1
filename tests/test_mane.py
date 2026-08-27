from __future__ import annotations

import unittest

from mva_solver.mane import Exon, Transcript, annotate_call
from mva_solver.models import VariantCall


def call(pos: int, ref: str, alt: str) -> VariantCall:
    return VariantCall(
        chrom="1",
        pos=pos,
        variant_id=".",
        ref=ref,
        alt=alt,
        qual=100.0,
        filters="PASS",
        genotype="0/1",
        ad_ref=10,
        ad_alt=10,
        depth=20,
        genotype_quality=99,
        phased_genotype=None,
        phase_set=None,
    )


class ManeAnnotationTest(unittest.TestCase):
    def setUp(self) -> None:
        # Transcript is ATG TTA AAT TAA: M-L-N-stop.
        self.sequence = "ATGTTAAATTAA"
        self.transcript = Transcript(
            assembly="GRCh38",
            gene="TEST",
            chrom="1",
            genomic_start=100,
            genomic_end=201,
            strand="+",
            transcript="NM_TEST.1",
            protein="NP_TEST.1",
            transcript_length=12,
            cds_transcript_start=1,
            cds_transcript_end=12,
            exons=(
                Exon(100, 105, 1, 6),
                Exon(196, 201, 7, 12),
            ),
        )

    def test_stop_gain(self) -> None:
        result = annotate_call(call(104, "T", "G"), self.transcript, self.sequence)
        self.assertEqual(result.consequence, "stop_gained")
        self.assertEqual(result.hgvs_c, "NM_TEST.1:c.5T>G")
        self.assertEqual(result.hgvs_p, "NP_TEST.1:p.L2*")

    def test_missense(self) -> None:
        result = annotate_call(call(198, "T", "G"), self.transcript, self.sequence)
        self.assertEqual(result.consequence, "missense_variant")
        self.assertEqual(result.hgvs_p, "NP_TEST.1:p.N3K")

    def test_intronic(self) -> None:
        result = annotate_call(call(150, "A", "G"), self.transcript, self.sequence)
        self.assertEqual(result.consequence, "intron_variant")
        self.assertEqual(result.nearest_splice_distance, 45)


if __name__ == "__main__":
    unittest.main()
