#!/usr/bin/env bash
set -euo pipefail

workspace_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
output_dir="${MVA_EVALUATOR_DIR:-${workspace_dir}/official_challenge_space}"
space_revision='d27c33953ecb0cfd7fa316c7cd93ff0ffb05cc1d'
expected_sha256='6d18b581e65a45e1ccc120071d588e740c2e42e983ff50704c60a40232b19180'
evaluator_url="https://huggingface.co/spaces/SageBio/rare-disease-real-kid-mva-hackathon-2026/resolve/${space_revision}/evaluation.py?download=true"

temp_dir="$(mktemp -d)"
trap 'rm -rf "${temp_dir}"' EXIT

curl -fL --retry 3 "${evaluator_url}" -o "${temp_dir}/evaluation.py"
observed_sha256="$(shasum -a 256 "${temp_dir}/evaluation.py" | awk '{print $1}')"
if [[ "${observed_sha256}" != "${expected_sha256}" ]]; then
  echo "Evaluator checksum mismatch: expected ${expected_sha256}, observed ${observed_sha256}" >&2
  exit 2
fi

mkdir -p "${output_dir}"
install -m 0644 "${temp_dir}/evaluation.py" "${output_dir}/evaluation.py"
echo "official_evaluator_ok=${output_dir}/evaluation.py"
