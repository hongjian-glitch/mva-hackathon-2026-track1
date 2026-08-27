#!/usr/bin/env bash
set -euo pipefail

workspace_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
output_dir="${MVA_PUBLIC_DIR:-${workspace_dir}/data/public}"
mkdir -p "${output_dir}"

curl -fL --retry 3 \
  'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=nuccore&id=NM_001211.6&rettype=gb&retmode=text' \
  -o "${output_dir}/NM_001211.6.gb"
curl -fL --retry 3 \
  'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=nuccore&id=NM_001211.6&rettype=fasta&retmode=text' \
  -o "${output_dir}/NM_001211.6.fasta"

clinvar_archive='https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/archive_2.0/2026'
clinvar_current='https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38'
if ! curl -fL --retry 3 \
  "${clinvar_archive}/clinvar_20260822.vcf.gz" \
  -o "${output_dir}/clinvar_20260826_GRCh38.vcf.gz"; then
  curl -fL --retry 3 \
    "${clinvar_current}/clinvar_20260822.vcf.gz" \
    -o "${output_dir}/clinvar_20260826_GRCh38.vcf.gz"
fi
if ! curl -fL --retry 3 \
  "${clinvar_archive}/clinvar_20260822.vcf.gz.tbi" \
  -o "${output_dir}/clinvar_20260826_GRCh38.vcf.gz.tbi"; then
  curl -fL --retry 3 \
    "${clinvar_current}/clinvar_20260822.vcf.gz.tbi" \
    -o "${output_dir}/clinvar_20260826_GRCh38.vcf.gz.tbi"
fi

curl -fL --retry 3 \
  'https://rest.uniprot.org/uniprotkb/O60566.txt' \
  -o "${output_dir}/uniprot_O60566_20260826.txt"

(
  cd "${output_dir}"
  shasum -a 256 -c "${workspace_dir}/references/public_resources.sha256"
)
