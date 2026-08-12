# OBS-002: Full-chain script-usage census

Dated observation note. Recorded 2026-08-06 (tip ~96,349). Produced by an
agent-assisted scan over our parity-verified local index (Blockbook backend
`pearld:1.3.0`; tip hash matched `blockbook.pearlresearch.ai` at scan time);
witnesses of all 58,732 candidate script-path transactions fetched and their
tapscript leaves parsed with a script parser (not byte-grep). Zero fetch errors
reported. Data: `scan_summary.json.gz` (per-pattern tx sets),
`phase2_summary.json`, `p2mr_rows.json.gz` (all P2MR outputs with amounts/spends).

**Status: provisional** (single-pass, agent-produced). Before publishing any
figure externally, re-derive it from the Keshi database (the index stores
`script_class` per output) and diff against these JSONs.

## Headline numbers (heights 0–96,348)

- Outputs: 7,772,083 = 7,624,402 P2TR + **8,055 P2MR** + 139,626 OP_RETURN
  (96,929 coinbase witness commitments + 42,697 non-coinbase payloads).
- **OP_CAT: zero executions in chain history.** Caveat: scripts committed in
  never-revealed tree branches are invisible; the claim is about executions.
- **OP_CHECKXMSSSIG: 4 transactions ever**, all team proofs-of-concept
  (56,313/56,331, repeated 63,606/63,624; XMSS pubkey second half is an
  ascending `0x40…0x5f` test-vector pattern).
- **P2MR: 8,055 outputs carrying 47.31M PRL**, May 4 → present, 99.4% spent,
  51 unspent. Spend pattern: single-leaf `OP_0 <pk> CHECKSIGADD <pk>
  CHECKSIGADD OP_2 NUMEQUAL` (8,021 such spends), a 2-of-2 escrow with no
  on-chain timeout branch. Pattern-matches pearl-otc.com's per-trade escrow
  design; attribution is inferred from design + scale/era, not signed evidence.
- Inscriptions: 7,582 reveal txs (`OP_FALSE OP_IF` envelopes; tags `prl-20`
  5,366, `pearlscription` 1,953, `ord` 197); Pearlscriptions' indexer reports
  30,481 inscription records (batching explains the difference).
- OP_RETURN metaprotocol: 42,697 PRC-20/PRC-721 JSON outputs since 2026-05-22.
- Hashlocks: 506 HTLC-shaped leaves, clustered ~height 57k, operator unknown.
- Activity collapsed ~30× after early June; last ~6,300 blocks contain ~108
  multisig + 11 inscription txs.

## Why it matters for the roadmap

- Phase 10.1 (script classifier) is validated as **unserved by every explorer**
  and cheaper than planned; this census is its prototype.
- The P2MR escrow finding and "OP_CAT never executed" are publishable
  observations once re-derived per the verification standard.
- The token/inscription economy is a measurement subject, not a build target:
  it is already two rival standards deep and shrinking.
