from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class VariantCall:
    chrom: str
    pos: int
    variant_id: str
    ref: str
    alt: str
    qual: float
    filters: str
    genotype: str
    ad_ref: int | None
    ad_alt: int | None
    depth: int | None
    genotype_quality: int | None
    phased_genotype: str | None
    phase_set: str | None

    @property
    def key(self) -> tuple[str, int, str, str]:
        return self.chrom, self.pos, self.ref, self.alt

    @property
    def is_heterozygous(self) -> bool:
        return self.genotype in {"0/1", "1/0", "0|1", "1|0"}

    @property
    def is_pass(self) -> bool:
        return self.filters == "PASS"

    @property
    def allele_balance(self) -> float | None:
        if self.ad_ref is None or self.ad_alt is None:
            return None
        total = self.ad_ref + self.ad_alt
        return self.ad_alt / total if total else None

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["allele_balance"] = self.allele_balance
        return result


@dataclass(frozen=True)
class Consequence:
    region: str
    consequence: str
    transcript_position: int | None
    coding_position: int | None
    protein_position: int | None
    reference_codon: str | None
    alternate_codon: str | None
    reference_amino_acid: str | None
    alternate_amino_acid: str | None
    hgvs_c: str | None
    hgvs_p: str | None
    nearest_splice_distance: int | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ClinVarRecord:
    chrom: str
    pos: int
    ref: str
    alt: str
    variation_id: str
    allele_id: str
    significance: str
    review_status: str
    conditions: str
    hgvs: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
