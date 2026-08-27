from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any

from .clinvar import records_at_position
from .mane import Transcript, annotate_call, load_fasta
from .models import ClinVarRecord, Consequence, VariantCall
from .secure_io import secure_write_text
from .vcf import query_region


_CONSEQUENCE_SCORE = {
    "stop_gained": 100.0,
    "stop_lost": 80.0,
    "coding_indel": 75.0,
    "missense_variant": 45.0,
    "synonymous_variant": 0.0,
}


def _phase_pair(left: VariantCall, right: VariantCall) -> tuple[str, str, float]:
    """Return phase status, evidence note, and a ranking adjustment.

    GATK's PGT/PID fields are only informative when both records share a PID.
    Unknown phase stays eligible; a demonstrated cis pair is strongly demoted.
    """
    if (
        not left.phase_set
        or left.phase_set != right.phase_set
        or not left.phased_genotype
        or not right.phased_genotype
    ):
        return (
            "unphased",
            "No shared PGT/PID evidence; trans configuration requires parental or long-range phasing.",
            0.0,
        )

    supported = {"0|1": 1, "1|0": 0}
    left_haplotype = supported.get(left.phased_genotype)
    right_haplotype = supported.get(right.phased_genotype)
    if left_haplotype is None or right_haplotype is None:
        return (
            "unphased",
            "Shared PID is present, but PGT values do not resolve the alternate haplotypes.",
            0.0,
        )
    if left_haplotype == right_haplotype:
        return (
            "cis",
            "Shared PGT/PID places both alternate alleles on the same haplotype.",
            -200.0,
        )
    return (
        "trans",
        "Shared PGT/PID places the alternate alleles on opposite haplotypes.",
        20.0,
    )


def _clinvar_score(records: list[ClinVarRecord]) -> float:
    terms: set[str] = set()
    conflicting = False
    for record in records:
        normalized = record.significance.lower().replace("_", " ")
        if "conflicting" in normalized:
            conflicting = True
        terms.update(
            term.strip()
            for term in normalized.replace(",", "|").replace("/", "|").split("|")
            if term.strip()
        )
    if conflicting:
        return 0.0
    pathogenic = bool(terms & {"pathogenic", "likely pathogenic"})
    benign = bool(terms & {"benign", "likely benign"})
    if pathogenic and benign:
        return 0.0
    if pathogenic:
        return 80.0
    if benign:
        return -100.0
    if any("uncertain significance" in term for term in terms):
        return 5.0
    return 0.0


def _quality_pass(call: VariantCall) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if not call.is_pass:
        reasons.append("FILTER is not PASS")
    if not call.is_heterozygous:
        reasons.append("genotype is not heterozygous")
    if call.depth is None or call.depth < 10:
        reasons.append("depth < 10")
    if call.genotype_quality is None or call.genotype_quality < 20:
        reasons.append("genotype quality < 20")
    balance = call.allele_balance
    if balance is None or not 0.25 <= balance <= 0.75:
        reasons.append("allele balance outside [0.25, 0.75]")
    return not reasons, reasons


def _candidate_payload(
    call: VariantCall,
    consequence: Consequence,
    clinvar: list[ClinVarRecord],
    same_protein_clinvar: list[dict[str, Any]],
) -> dict[str, Any]:
    qc_pass, qc_reasons = _quality_pass(call)
    score = _CONSEQUENCE_SCORE.get(consequence.consequence, -20.0)
    score += _clinvar_score(clinvar)
    if qc_pass:
        score += 20.0
    return {
        "call": call.to_dict(),
        "consequence": consequence.to_dict(),
        "clinvar_exact": [record.to_dict() for record in clinvar],
        "clinvar_same_protein_change": same_protein_clinvar,
        "qc_pass": qc_pass,
        "qc_reasons": qc_reasons,
        "variant_score": score,
    }


def analyze(
    vcf_path: str | Path,
    transcript_config: str | Path,
    transcript_fasta: str | Path,
    clinvar_vcf: str | Path,
) -> dict[str, Any]:
    transcript = Transcript.from_json(transcript_config)
    transcript.validate()
    sequence = load_fasta(transcript_fasta)
    calls = query_region(
        vcf_path,
        transcript.chrom,
        transcript.genomic_start,
        transcript.genomic_end,
    )

    all_records: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    calls_by_key = {call.key: call for call in calls}
    for call in calls:
        consequence = annotate_call(call, transcript, sequence)
        position_records = records_at_position(clinvar_vcf, call)
        records = [
            record
            for record in position_records
            if record.ref == call.ref and record.alt == call.alt
        ]
        same_protein_clinvar: list[dict[str, Any]] = []
        if consequence.hgvs_p and len(call.ref) == 1 and len(call.alt) == 1:
            for record in position_records:
                if record.ref != call.ref or len(record.alt) != 1 or record.alt == call.alt:
                    continue
                public_allele = replace(call, alt=record.alt)
                public_consequence = annotate_call(public_allele, transcript, sequence)
                if public_consequence.hgvs_p == consequence.hgvs_p:
                    same_protein_clinvar.append(
                        {
                            "record": record.to_dict(),
                            "hgvs_p": public_consequence.hgvs_p,
                            "interpretation": (
                                "Same amino-acid substitution from a different nucleotide allele; "
                                "not an exact variant match."
                            ),
                        }
                    )
        payload = _candidate_payload(
            call,
            consequence,
            records,
            same_protein_clinvar,
        )
        all_records.append(payload)
        if (
            payload["qc_pass"]
            and consequence.region == "coding"
            and consequence.consequence not in {"synonymous_variant"}
        ):
            candidates.append(payload)

    pairs: list[dict[str, Any]] = []
    for left, right in combinations(candidates, 2):
        left_key = tuple(left["call"][key] for key in ("chrom", "pos", "ref", "alt"))
        right_key = tuple(right["call"][key] for key in ("chrom", "pos", "ref", "alt"))
        left_call = calls_by_key[left_key]
        right_call = calls_by_key[right_key]
        phase_status, phase_note, phase_adjustment = _phase_pair(left_call, right_call)
        pair_score = (
            left["variant_score"]
            + right["variant_score"]
            + 30.0
            + phase_adjustment
        )
        pairs.append(
            {
                "variant_keys": [
                    [
                        left["call"]["chrom"],
                        left["call"]["pos"],
                        left["call"]["ref"],
                        left["call"]["alt"],
                    ],
                    [
                        right["call"]["chrom"],
                        right["call"]["pos"],
                        right["call"]["ref"],
                        right["call"]["alt"],
                    ],
                ],
                "pair_score": pair_score,
                "phase_status": phase_status,
                "phase_note": phase_note,
            }
        )
    pairs.sort(
        key=lambda item: (-item["pair_score"], tuple(map(tuple, item["variant_keys"])))
    )

    return {
        "schema_version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "privacy": "patient-derived; do not publish without review",
        "transcript": {
            "assembly": transcript.assembly,
            "gene": transcript.gene,
            "chrom": transcript.chrom,
            "transcript": transcript.transcript,
            "protein": transcript.protein,
        },
        "counts": {
            "gene_region_calls": len(calls),
            "coding_qc_pass_candidates": len(candidates),
            "candidate_pairs": len(pairs),
        },
        "records": all_records,
        "candidates": sorted(
            candidates, key=lambda item: item["variant_score"], reverse=True
        ),
        "ranked_pairs": pairs,
    }


def write_analysis(payload: dict[str, Any], output: str | Path) -> None:
    secure_write_text(output, json.dumps(payload, indent=2, sort_keys=True) + "\n")
