# DS-005 coinbase-tag census manifest

Produced by scripts/coinbase-tag-census.py sha256 5c43b6d03a05, per plan item 2.2
(task DS-005-coinbase-tags-v1).
Generated: 2026-08-10T19:43:27Z
Tool commit (toolCommit): 7eed53a297e3961c3cb77864232cf3e4e57d00dd

Snapshot: heights 0..97000 inclusive, 97001 blocks. Block hash at height
97000: cf8c59199fe086435c697fa453bba91a73b9fddbe8857a94e7498520cfd4ffa6.
Source: raw blocks from the local Blockbook over loopback,
coinbase isolated by the prevout anchor (32 zero bytes plus 0xffffffff)
and validated by the BIP34 height push against the requested height; the
genesis coinbase carries no height push and is validated by its fixed
04ffff001d prefix instead. Every row archives the full coinbase scriptSig
hex, the trailing 4-byte sequence field, and the coinbase's first payout
address, so any reanalysis reads blocks.jsonl.gz and never refetches.

Population: every canonical block in 0..97000. Emit refuses unless each
height appears exactly once, so 97001 is the count of all canonical
blocks in the span, never a decoded-only subset. Tag-family counts use
the 97001 parse-valid blocks as denominator; the 0 parse-error
rows are archived in the JSONL and listed in summary.json, never dropped.
Pool labels in the crosstab are payout-address matches against the
migrations/0001_core.sql seed; unlabeled means any other or missing
payout address.

| File | sha256 |
|---|---|
| blocks.jsonl.gz | a7864cd62da6e0036ca44125f13c111529405de9dd798d92d03930fa8e2f5bbc |
| summary.json | 53d0e9edc9b1fce0d137cb409e389cc568c66813774ef3efdca96e5260b9470d |
This dataset is append-only (roadmap SS6.5): corrections ship as a new
version directory with an errata note, never as an edit here.
