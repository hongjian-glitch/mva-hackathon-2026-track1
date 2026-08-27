from __future__ import annotations

import subprocess
from pathlib import Path

from .models import ClinVarRecord, VariantCall


_QUERY_FORMAT = (
    "%CHROM\\t%POS\\t%ID\\t%REF\\t%ALT\\t%INFO/ALLELEID\\t"
    "%INFO/CLNSIG\\t%INFO/CLNREVSTAT\\t%INFO/CLNDN\\t%INFO/CLNHGVS\\n"
)


def records_at_position(vcf_path: str | Path, call: VariantCall) -> list[ClinVarRecord]:
    command = [
        "bcftools",
        "query",
        "-r",
        f"{call.chrom}:{call.pos}-{call.pos}",
        "-f",
        _QUERY_FORMAT,
        str(vcf_path),
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    records: list[ClinVarRecord] = []
    for line in completed.stdout.splitlines():
        fields = line.split("\t")
        if len(fields) != 10:
            continue
        records.append(
            ClinVarRecord(
                chrom=fields[0],
                pos=int(fields[1]),
                ref=fields[3].upper(),
                alt=fields[4].upper(),
                variation_id=fields[2],
                allele_id=fields[5],
                significance=fields[6],
                review_status=fields[7],
                conditions=fields[8],
                hgvs=fields[9],
            )
        )
    return records
