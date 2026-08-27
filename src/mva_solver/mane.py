from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import Consequence, VariantCall


_BASES = "TCAG"
_AMINO_ACIDS = (
    "FFLLSSSSYY**CC*W"
    "LLLLPPPPHHQQRRRR"
    "IIIMTTTTNNKKSSRR"
    "VVVVAAAADDEEGGGG"
)
_GENETIC_CODE = dict(
    zip((a + b + c for a in _BASES for b in _BASES for c in _BASES), _AMINO_ACIDS)
)


@dataclass(frozen=True)
class Exon:
    genomic_start: int
    genomic_end: int
    transcript_start: int
    transcript_end: int


@dataclass(frozen=True)
class Transcript:
    assembly: str
    gene: str
    chrom: str
    genomic_start: int
    genomic_end: int
    strand: str
    transcript: str
    protein: str
    transcript_length: int
    cds_transcript_start: int
    cds_transcript_end: int
    exons: tuple[Exon, ...]

    @classmethod
    def from_json(cls, path: str | Path) -> "Transcript":
        raw: dict[str, Any] = json.loads(Path(path).read_text())
        exons = tuple(Exon(**item) for item in raw.pop("exons"))
        raw.pop("ensembl_transcript", None)
        return cls(exons=exons, **raw)

    def validate(self) -> None:
        if self.strand != "+":
            raise ValueError("This minimal MANE annotator currently supports positive-strand transcripts only")
        expected_tx = 1
        for exon in self.exons:
            if exon.transcript_start != expected_tx:
                raise ValueError(f"Non-contiguous transcript coordinates at {exon}")
            genomic_len = exon.genomic_end - exon.genomic_start + 1
            transcript_len = exon.transcript_end - exon.transcript_start + 1
            if genomic_len != transcript_len:
                raise ValueError(f"Exon length mismatch at {exon}")
            expected_tx = exon.transcript_end + 1
        if expected_tx - 1 != self.transcript_length:
            raise ValueError("Transcript length does not match exon map")


def load_fasta(path: str | Path) -> str:
    lines = Path(path).read_text().splitlines()
    sequence = "".join(line.strip() for line in lines if line and not line.startswith(">"))
    if not sequence:
        raise ValueError(f"No FASTA sequence found in {path}")
    return sequence.upper()


def _nearest_splice_distance(transcript: Transcript, position: int) -> int:
    return min(
        min(abs(position - exon.genomic_start), abs(position - exon.genomic_end))
        for exon in transcript.exons
    )


def annotate_call(call: VariantCall, transcript: Transcript, sequence: str) -> Consequence:
    transcript.validate()
    if len(sequence) != transcript.transcript_length:
        raise ValueError(
            f"Sequence length {len(sequence)} does not match {transcript.transcript_length}"
        )
    if call.chrom.removeprefix("chr") != transcript.chrom.removeprefix("chr"):
        raise ValueError(f"Variant {call.key} is not on transcript chromosome {transcript.chrom}")

    exon = next(
        (
            item
            for item in transcript.exons
            if item.genomic_start <= call.pos <= item.genomic_end
        ),
        None,
    )
    if exon is None:
        return Consequence(
            region="intronic",
            consequence="intron_variant",
            transcript_position=None,
            coding_position=None,
            protein_position=None,
            reference_codon=None,
            alternate_codon=None,
            reference_amino_acid=None,
            alternate_amino_acid=None,
            hgvs_c=None,
            hgvs_p=None,
            nearest_splice_distance=_nearest_splice_distance(transcript, call.pos),
        )

    tx_position = exon.transcript_start + (call.pos - exon.genomic_start)
    observed_ref = sequence[tx_position - 1 : tx_position - 1 + len(call.ref)]
    if observed_ref != call.ref:
        raise ValueError(
            f"Reference mismatch for {call.key}: transcript has {observed_ref} at {tx_position}"
        )

    if tx_position < transcript.cds_transcript_start:
        region = "five_prime_utr"
    elif tx_position > transcript.cds_transcript_end:
        region = "three_prime_utr"
    else:
        region = "coding"

    if region != "coding":
        return Consequence(
            region=region,
            consequence=f"{region}_variant",
            transcript_position=tx_position,
            coding_position=None,
            protein_position=None,
            reference_codon=None,
            alternate_codon=None,
            reference_amino_acid=None,
            alternate_amino_acid=None,
            hgvs_c=None,
            hgvs_p=None,
            nearest_splice_distance=0,
        )

    coding_position = tx_position - transcript.cds_transcript_start + 1
    if len(call.ref) != 1 or len(call.alt) != 1:
        return Consequence(
            region="coding",
            consequence="coding_indel",
            transcript_position=tx_position,
            coding_position=coding_position,
            protein_position=(coding_position + 2) // 3,
            reference_codon=None,
            alternate_codon=None,
            reference_amino_acid=None,
            alternate_amino_acid=None,
            hgvs_c=f"{transcript.transcript}:c.{coding_position}{call.ref}>{call.alt}",
            hgvs_p=None,
            nearest_splice_distance=0,
        )

    codon_c_start = ((coding_position - 1) // 3) * 3 + 1
    codon_tx_start = transcript.cds_transcript_start + codon_c_start - 1
    reference_codon = sequence[codon_tx_start - 1 : codon_tx_start + 2]
    codon_offset = (coding_position - 1) % 3
    alternate_codon = (
        reference_codon[:codon_offset]
        + call.alt
        + reference_codon[codon_offset + 1 :]
    )
    reference_aa = _GENETIC_CODE[reference_codon]
    alternate_aa = _GENETIC_CODE[alternate_codon]
    protein_position = (coding_position + 2) // 3

    if alternate_aa == reference_aa:
        consequence = "synonymous_variant"
    elif alternate_aa == "*":
        consequence = "stop_gained"
    elif reference_aa == "*":
        consequence = "stop_lost"
    else:
        consequence = "missense_variant"

    return Consequence(
        region="coding",
        consequence=consequence,
        transcript_position=tx_position,
        coding_position=coding_position,
        protein_position=protein_position,
        reference_codon=reference_codon,
        alternate_codon=alternate_codon,
        reference_amino_acid=reference_aa,
        alternate_amino_acid=alternate_aa,
        hgvs_c=f"{transcript.transcript}:c.{coding_position}{call.ref}>{call.alt}",
        hgvs_p=(
            f"{transcript.protein}:p.{reference_aa}{protein_position}{alternate_aa}"
        ),
        nearest_splice_distance=0,
    )
