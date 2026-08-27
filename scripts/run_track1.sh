#!/usr/bin/env bash
set -euo pipefail

workspace_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${workspace_dir}/src${PYTHONPATH:+:${PYTHONPATH}}"

python_bin="${PYTHON_BIN:-python3}"
: "${MVA_VCF:?Set MVA_VCF to the absolute path of the gated proband VCF}"
vcf_path="${MVA_VCF}"
transcript_fasta="${MVA_TRANSCRIPT_FASTA:-${workspace_dir}/data/public/NM_001211.6.fasta}"
clinvar_vcf="${MVA_CLINVAR_VCF:-${workspace_dir}/data/public/clinvar_20260826_GRCh38.vcf.gz}"
analysis_path="${MVA_ANALYSIS:-${workspace_dir}/outputs/private/track1_analysis.json}"
submission_path="${MVA_SUBMISSION:-${workspace_dir}/outputs/private/track1_submission.csv}"

"${python_bin}" -m mva_solver analyze \
  --vcf "${vcf_path}" \
  --transcript-config "${workspace_dir}/config/bub1b_mane_nm_001211.6.json" \
  --transcript-fasta "${transcript_fasta}" \
  --clinvar-vcf "${clinvar_vcf}" \
  --output "${analysis_path}"

"${python_bin}" -m mva_solver build-submission \
  --analysis "${analysis_path}" \
  --output "${submission_path}"
