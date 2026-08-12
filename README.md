# Keshi Research

Public research artifacts of the Keshi project for [Pearl Network](https://pearlresearch.ai) (PRL).

Keshi is an independent community infrastructure project for Pearl Network. It is not affiliated with, or endorsed by, Pearl Research Labs. It runs its own `pearld` full node and Blockbook indexer, computes every figure itself, and documents the source and formula behind every number.

This repository is the public home of that research: the dated observation notes, the pre-registered analyses, the consensus-change register, the metric definitions, the attestation spec, the datasets, and the scripts that reproduce every published table.

## Contents

| Path | What |
|---|---|
| `docs/metrics.md` | Metric definitions: source, formula, window and caveats for every number Keshi publishes. The language policy is binding here. |
| `docs/registry/PCCR.md` | Pearl Consensus Change Register: a dated, code-evidenced ledger of every consensus change on Pearl mainnet. |
| `docs/research/OBS-*.md` | Dated observation notes. Each states its status and its data. |
| `docs/research/PREREG-*.md` | Pre-registered analyses, frozen at their stated commit. |
| `docs/research/datasets/DS-*/` | Append-only datasets. Each carries a `MANIFEST.md` with the sha256 of every file. |
| `docs/research/outreach/` | Draft standards proposals (PIP drafts), clearly labeled as drafts. |
| `docs/specs/keshi-attest-v0.md` | The attestation spec, version 0. |
| `docs/fixtures/` | Conformance vectors for the scan and extraction tooling. |
| `scripts/` | Reproduce scripts. `scripts/ds002-reproduce.sh` regenerates every published table from the datasets alone: no API, no database. |

## Reproducibility and integrity

- Datasets are append-only. Verify files against the dataset's `MANIFEST.md` before use; the MANIFEST is the integrity root.
- Pre-registrations are frozen and never edited. Corrections ship as new numbered documents or as dated errata, never as silent edits (see `docs/research/ERRATA-POLICY.md`).
- Negative results are published with their exact search space, never as proof of absence.

## Citation and DOI

Dataset versions are also deposited on Zenodo with a DOI. The concept DOI [10.5281/zenodo.21863620](https://doi.org/10.5281/zenodo.21863620) always resolves to the latest version. Cite the DOI where one exists, and see `docs/research/DATA-LICENCE.md` for the suggested citation and schema.

## Licence

- Code (the `scripts/` reproduce tooling) is MIT, see `LICENSE`.
- Research datasets under `docs/research/datasets/` and the prose documents are CC BY 4.0, see `docs/research/DATA-LICENCE.md`.

## Relationship to the Keshi platform

The live dashboard, API, collector and infrastructure are maintained in separate repositories and are not part of this one. This repository holds the public research record and the artifacts needed to reproduce it.
