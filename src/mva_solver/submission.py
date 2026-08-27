from __future__ import annotations

import csv
import io
import json
import math
import re
from pathlib import Path
from typing import Any

from .secure_io import secure_write_text


FIELDS = [
    "proband_id",
    "chrom_1",
    "pos_1",
    "ref_1",
    "alt_1",
    "chrom_2",
    "pos_2",
    "ref_2",
    "alt_2",
    "epcr",
    "finding_type",
    "notes",
]

_CHROM_RE = re.compile(r"^chr(?:[1-9]|1[0-9]|2[0-2]|X|Y|M|MT)$")


def _call_by_key(analysis: dict[str, Any], key: list[Any]) -> dict[str, Any]:
    wanted = tuple(key)
    for item in analysis["candidates"]:
        call = item["call"]
        observed = (call["chrom"], call["pos"], call["ref"], call["alt"])
        if observed == wanted:
            return call
    raise ValueError(f"Ranked pair references missing candidate {wanted}")


def build_row(analysis: dict[str, Any], proband_id: str = "PROBAND01") -> dict[str, Any]:
    if analysis.get("schema_version") != "1.0":
        raise ValueError("Analysis schema_version must be 1.0")
    if analysis.get("transcript", {}).get("assembly") != "GRCh38":
        raise ValueError("Analysis assembly must be GRCh38")
    pairs = analysis.get("ranked_pairs", [])
    if not pairs:
        raise ValueError("Analysis has no ranked compound-heterozygous pair")
    top_pair = pairs[0]
    if len(top_pair.get("variant_keys", [])) != 2:
        raise ValueError("Top prediction must contain exactly two variants")
    phase_status = top_pair.get("phase_status")
    if phase_status not in {"unphased", "trans", "cis"}:
        raise ValueError("Top pair has missing or invalid phase_status")
    if phase_status == "cis":
        raise ValueError("Refusing to submit a recessive pair demonstrated to be in cis")
    first = _call_by_key(analysis, top_pair["variant_keys"][0])
    second = _call_by_key(analysis, top_pair["variant_keys"][1])

    def challenge_chrom(value: str) -> str:
        return value if value.startswith("chr") else f"chr{value}"

    phase_note = (
        "Shared read-backed PGT/PID supports trans configuration."
        if phase_status == "trans"
        else "Phase is not established; parental or long-range phasing is required."
    )
    return {
        "proband_id": proband_id,
        "chrom_1": challenge_chrom(first["chrom"]),
        "pos_1": first["pos"],
        "ref_1": first["ref"],
        "alt_1": first["alt"],
        "chrom_2": challenge_chrom(second["chrom"]),
        "pos_2": second["pos"],
        "ref_2": second["ref"],
        "alt_2": second["alt"],
        "epcr": "0.99",
        "finding_type": "primary",
        "notes": f"Locally prioritized recessive candidate pair. {phase_note}",
    }


def write_submission(
    analysis_path: str | Path,
    output_path: str | Path,
    proband_id: str = "PROBAND01",
) -> None:
    analysis = json.loads(Path(analysis_path).read_text())
    row = build_row(analysis, proband_id=proband_id)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerow(row)
    secure_write_text(output_path, buffer.getvalue(), validator=preflight)


def preflight(path: str | Path) -> list[str]:
    errors: list[str] = []
    with Path(path).open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDS:
            errors.append(f"Unexpected columns: {reader.fieldnames}")
        rows = list(reader)
    if any(None in row for row in rows):
        errors.append("Submission contains fields beyond the required header")
    if not rows:
        errors.append("Submission contains no prediction rows")
    if len(rows) > 10:
        errors.append("Submission contains more than 10 rows")
    probands = {row.get("proband_id", "").strip() for row in rows}
    if probands and probands != {"PROBAND01"}:
        errors.append("Submission must contain only proband_id PROBAND01")

    seen_predictions: set[frozenset[tuple[str, int, str, str]]] = set()
    observed_epcr: list[float] = []
    for index, row in enumerate(rows, start=1):
        try:
            epcr = float(row["epcr"])
        except (KeyError, ValueError):
            errors.append(f"Row {index}: invalid EPCR")
            continue
        if not math.isfinite(epcr) or not 0 < epcr <= 1:
            errors.append(f"Row {index}: EPCR is outside (0, 1]")
        else:
            observed_epcr.append(epcr)
        if row.get("finding_type") not in {"primary", "secondary"}:
            errors.append(f"Row {index}: invalid finding_type")

        variants: list[tuple[str, int, str, str]] = []
        for suffix in ("1", "2"):
            values = [
                row.get(f"chrom_{suffix}", "").strip(),
                row.get(f"pos_{suffix}", "").strip(),
                row.get(f"ref_{suffix}", "").strip(),
                row.get(f"alt_{suffix}", "").strip(),
            ]
            if suffix == "2" and not any(values):
                continue
            if not all(values):
                errors.append(f"Row {index}: variant {suffix} is incomplete")
                continue
            chrom, pos_text, ref, alt = values
            if not _CHROM_RE.fullmatch(chrom):
                errors.append(f"Row {index}: chrom_{suffix} is not a canonical chrN value")
            try:
                pos = int(pos_text)
                if pos <= 0:
                    raise ValueError
            except ValueError:
                errors.append(f"Row {index}: pos_{suffix} is not a positive integer")
                continue
            if ref != ref.upper() or alt != alt.upper():
                errors.append(f"Row {index}: ref_{suffix}/alt_{suffix} must be uppercase")
            if not ref or not alt or ref == alt:
                errors.append(f"Row {index}: ref_{suffix}/alt_{suffix} is invalid")
            variants.append((chrom, pos, ref, alt))

        if len(variants) != len(set(variants)):
            errors.append(f"Row {index}: a variant is repeated within the pair")
        if variants:
            prediction = frozenset(variants)
            if prediction in seen_predictions:
                errors.append(f"Row {index}: duplicate prediction")
            seen_predictions.add(prediction)

    if len(observed_epcr) != len(set(observed_epcr)):
        errors.append("EPCR values must be unique to make ranking deterministic")
    if observed_epcr != sorted(observed_epcr, reverse=True):
        errors.append("Rows must be sorted by strictly descending EPCR")
    return errors
