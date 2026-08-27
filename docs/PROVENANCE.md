# Provenance and privacy record

## Controlled-access inputs

- Hugging Face dataset: `SageBio/mva-hackathon-2026-data`
- Pinned revision: `59e322d27f399006b398d366d33e703e48a29914`
- Dataset access verified under the configured local Hugging Face account.
- Raw and derived participant data is excluded from version control.

## Public evaluator

- Space: `SageBio/rare-disease-real-kid-mva-hackathon-2026`
- Pinned revision: `d27c33953ecb0cfd7fa316c7cd93ff0ffb05cc1d`

## Synapse project

- Project: `syn76251147`
- Title: *Rare Disease, Real Kid. The 2026 MVA Hackathon*
- Wiki: https://www.synapse.org/Synapse:syn76251147/wiki/642892
- The public project page displayed no formal citation or DOI association when
  checked on 2026-08-26. Release materials use a conventional project citation
  provisionally and must adopt organizer-preferred wording if supplied.

## Public annotation resources

- NCBI RefSeq MANE Select transcript `NM_001211.6`, retrieved 2026-08-26.
- Matching protein `NP_001202.5` and Ensembl transcript `ENST00000287598.11`.
- ClinVar GRCh38 VCF with `fileDate=2026-08-22`, retrieved 2026-08-26.
- UniProt reviewed record `O60566`, retrieved 2026-08-26.

Exact source URLs, retrieval dates, local filenames, and SHA-256 digests are in
`references/public_resources.tsv`. `scripts/fetch_public_references.sh`
downloads the generic public resources and refuses checksum drift. Participant
coordinates or phenotypes are never included in those requests.

## Controlled-data handling

Controlled source files remain in the participant workspace and are excluded
from this repository. The solver makes no network requests. Separate retrieval
scripts download only generic public references, and participant coordinates or
phenotypes are never included in those requests. Operational compliance records
and controlled-input hashes remain private and are not part of the release.

Controlled-input hashes and machine/run metadata are recorded only in the
private run manifest; they are not part of the proposed public release.
