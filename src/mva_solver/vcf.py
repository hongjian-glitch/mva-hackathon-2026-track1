from __future__ import annotations

import subprocess
from pathlib import Path

from .models import VariantCall


_QUERY_FORMAT = (
    "%CHROM\\t%POS\\t%ID\\t%REF\\t%ALT\\t%QUAL\\t%FILTER\\t"
    "[%GT\\t%AD\\t%DP\\t%GQ\\t%PGT\\t%PID]\\n"
)


def _nullable_int(value: str) -> int | None:
    return None if value in {"", "."} else int(value)


def _nullable_text(value: str) -> str | None:
    return None if value in {"", "."} else value


def parse_query_line(line: str) -> VariantCall:
    fields = line.rstrip("\n").split("\t")
    if len(fields) != 13:
        raise ValueError(f"Expected 13 bcftools fields, received {len(fields)}: {line!r}")
    ad = fields[8].split(",") if fields[8] not in {"", "."} else []
    return VariantCall(
        chrom=fields[0],
        pos=int(fields[1]),
        variant_id=fields[2],
        ref=fields[3].upper(),
        alt=fields[4].upper(),
        qual=float(fields[5]),
        filters=fields[6],
        genotype=fields[7],
        ad_ref=_nullable_int(ad[0]) if len(ad) >= 1 else None,
        ad_alt=_nullable_int(ad[1]) if len(ad) >= 2 else None,
        depth=_nullable_int(fields[9]),
        genotype_quality=_nullable_int(fields[10]),
        phased_genotype=_nullable_text(fields[11]),
        phase_set=_nullable_text(fields[12]),
    )


def query_region(vcf_path: str | Path, chrom: str, start: int, end: int) -> list[VariantCall]:
    command = [
        "bcftools",
        "query",
        "-r",
        f"{chrom}:{start}-{end}",
        "-f",
        _QUERY_FORMAT,
        str(vcf_path),
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return [parse_query_line(line) for line in completed.stdout.splitlines() if line]
