# Errata and revision policy

How corrections to published research artifacts are made, numbered, and
surfaced. Required by the roadmap's verification standard before the first
external report; binding for every dated note, dataset, and pre-registration
in `docs/research/`.

## Principles

1. Nothing is silently rewritten. A published number or claim changes only
   through a visible, dated correction that names what was wrong and what
   replaced it.
2. The strength of the correction matches the strength of the error. A typo
   is an edit; a wrong number is an erratum; a wrong verdict is a new
   numbered document.
3. Struck claims stay visible. When a claim is withdrawn, later documents
   list it as struck rather than absorbing it, so a reader who saw the old
   claim can find its retraction.

## By artifact class

**Dated observation notes (OBS-NNN).** Editable for typography and clarity;
any change to a number, table, verdict, or caveat ships as a dated errata
block inside the note (the pattern OBS-001 and OBS-004 already use:
`> **Errata YYYY-MM-DD (source):** ...`). If the correction reverses the
note's central finding, a new numbered note supersedes it and the old note
gains a pointer, not a rewrite.

**Pre-registrations (PREREG-NNN).** Frozen at a named commit and never
edited in §§2 onward. Corrections ship as the next PREREG number with a
stated reason. A frozen document may gain a clearly marked non-normative
pointer line (for example, to the document that supersedes a section), and
the freeze commit recorded in tooling moves only alongside a new document.

**Datasets (docs/research/datasets/).** Append-only. A defective or
incomplete dataset is never edited in place: the correction is a new
version directory plus a dated errata note in the consuming OBS document
stating what the prior version lacked. Known instance: DS-002's
`summary.json` predates the coverage fields (`snapshotTip`,
`unscannedCandidates`, `unhashedBlocks`; PREREG-002 §7.2 and §2); the
scanner now emits them, and OBS-005 carries the dated erratum with DS-002's
actual values.

**Metric definitions (docs/metrics.md).** Definitions may be tightened;
any change that alters what an already published number means requires an
erratum in every published note that used the old definition.

## Surfacing

Corrections appear in three places: the errata block in the affected
document, the consolidated list in the affected document's web rendering
(the research pages render the full document, so the block travels with
it), and the changelog entry of the commit that ships them. External
artifacts (Zenodo deposits, arXiv versions) get a new version whose
description names the errata; prior versions remain retrievable.
