# MVA Hackathon 2026 — Track 1 solver

This repository contains a locally executed pipeline for the "Rare Disease,
Real Kid" MVA Hackathon 2026. It reproduces the official Track 1 submission
contract without sending participant variants to external services. The gated
source files and participant-derived outputs are excluded from the public
repository.

The live Track 1 leaderboard is already at the mathematical ceiling (100 rank
points and F-max 1.000). The project objective is therefore to match that score
with an independently reproducible analysis, then distinguish the entry on
scientific rigor, auditability, and scalability.

## Privacy boundary

Controlled-access data, patient-derived intermediates, rendered clinical
documents, and candidate outputs are ignored by version control. The solver
makes no network requests. Separate scripts download generic public reference
resources, which are then intersected locally.

## Reproduce locally

Prerequisites: Python 3.11+ and `bcftools` 1.20+.

```bash
PYTHONPATH=src python -m mva_solver analyze \
  --vcf /absolute/private/path/to/proband.vcf.gz \
  --transcript-config config/bub1b_mane_nm_001211.6.json \
  --transcript-fasta data/public/NM_001211.6.fasta \
  --clinvar-vcf data/public/clinvar_20260826_GRCh38.vcf.gz \
  --output outputs/private/track1_analysis.json

PYTHONPATH=src python -m mva_solver build-submission \
  --analysis outputs/private/track1_analysis.json \
  --output outputs/private/track1_submission.csv

PYTHONPATH=src python -m unittest discover -s tests -v
```

Fetch and verify the pinned public evaluator before running the five official
contract tests:

```bash
bash scripts/fetch_official_evaluator.sh
```

The resulting CSV is preflighted against the public official schema. Live
leaderboard upload is intentionally a separate, explicit action.

The supplied VCF filename and all participant-derived paths stay outside the
public release. The convenience script therefore requires `MVA_VCF` to be set:

```bash
MVA_VCF=/absolute/private/path/to/proband.vcf.gz bash scripts/run_track1.sh
```

## Source-of-truth pins

- Dataset revision: `59e322d27f399006b398d366d33e703e48a29914`
- Challenge Space revision: `d27c33953ecb0cfd7fa316c7cd93ff0ffb05cc1d`
- MANE Select transcript: `NM_001211.6` / `ENST00000287598.11`
- ClinVar snapshot file date: `2026-08-22`

See `docs/CONTRACT.md` and `docs/PROVENANCE.md` for the evaluator and artifact
contract.

## Scope

This approach is deliberately phenotype-informed and target-gene-first. It
is not yet a gene-agnostic WGS prioritizer: it does not re-call FASTQs or model
SV/CNV, repeat, mitochondrial, deep-intronic, or transcriptome evidence. Its
strength is a narrow, auditable answer to the disclosed MVA case; its limits are
reported explicitly rather than hidden behind the leaderboard score.

## Verification

```bash
bash scripts/fetch_official_evaluator.sh
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python scripts/privacy_check.py
PYTHONPATH=src python scripts/check_official_scorer.py \
  --submission outputs/private/track1_submission.csv
```

The official-scorer check uses the submitted pair itself as synthetic truth.
It proves exact contract compatibility, not agreement with the private answer
key.

## License and required acknowledgement

The submission materials are released under [CC BY 4.0](LICENSE), as required
by the challenge rules.

> “This work was made possible through the Hackathon, organized by Sage
> Bionetworks in partnership with the MVA Society, Hugging Face, and BEACON
> (The Benchmarking, Evaluation, and Assessment Consortium for Science), with
> prize sponsorship from AWS and Anthropic. We are deeply grateful to the child
> and their family who generously contributed their data and their story to
> advance research into this rare disease. We acknowledge their trust in making
> this Hackathon possible.”

Proposed Synapse citation pending organizer confirmation:

> Sage Bionetworks. (2026). *Rare Disease, Real Kid. The 2026 MVA Hackathon*.
> Synapse project syn76251147.
> https://www.synapse.org/Synapse:syn76251147/wiki/642892

The public project page displayed no formal citation or DOI when checked on
2026-08-26. Replace the proposed citation if the organizers provide preferred
wording before release.
