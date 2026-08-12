# OBS-003: Phase 7 acceptance at the fork boundary, and first full-corpus census

Dated observation note. Recorded 2026-08-06 (tip ~96,395), from the deployed
Phase 7 API (`/v1/metrics/{series}`, `/v1/certs/census`) over the complete
decoded corpus (96,397 canonical certificates, decoder v1).

## 1. The fork-discontinuity acceptance (roadmap Phase 7, binding): PASSED

Prediction: the new arithmetic accounting must show a clean discontinuity at
the rank-penalty activation (height 96,251) of the magnitude OBS-001 measured,
or it must not ship. Boundary-local (last/first 100 blocks around 96,251, 7d
window):

| Series | Pre | Post | Verdict |
|---|---|---|---|
| rank (mode) | 1024 in 49/100 | 128 in 83/100 | PASS: reproduces OBS-001 (49% / 84%) |
| declared-arithmetic (median) | 4.40e13 MACs | 4.33e12 MACs | PASS: 10× collapse |
| proven-arithmetic (median) | 2.10e6 MACs | 5.24e5 MACs | PASS: 4× clean step (1.05e6 → 5.24e5 across 25-block medians) |
| attestation-ratio (median, per block) | 9.54e-8 | 1.21e-7 | PASS: steps *up* (m·n shrank) |

The 7d MAC-weighted aggregate ratio is **5.98e-10**, far below the per-block
median because Σdeclared is dominated by the largest declared shapes. Exactly
the median-vs-MAC-weighted distinction `metrics.md#attestation-ratio` requires
quoting explicitly.

## 2. The MoE window WAS used: hypothesis refuted

**`moeBlocks = 1,929` over the entire chain.** MoE certificates are only
consensus-valid inside the window 71,935–91,630 (19,695 blocks), so ~9.8% of
that window carried a production MoE proof. This **refutes the working
hypothesis** (roadmap Open questions; echoed in OBS-001) that the MoE
capability went essentially unused. The governance story is therefore
sharper, not weaker: a hard-forked capability with *real production usage* was
retracted ~44 days later by a softfork that no PIP documents (PCCR-0003).

Errata applied to OBS-001, whose zero-MoE observation was over a post-window
sample where zero is consensus-required and supports no usage inference.

## 3. The chain's most common shape matches the official stack AND a published model

Top declared shape over the whole corpus:

```
m 32768 · n 57344 · k 8192 · rank 128 · tile 2×64: 15,902 blocks (~16.5%)
```

- **tile 2×64 is the official kernel's exact wgmma fragment** (h=2, w=64; the
  F9 fingerprint), and rank 128 is a compiled official rank;
- **(n 57344, k 8192) is Llama-3.3-70B-Instruct-pearl's fused gate/up layer**
  (pearl-notes §mining stack, F4).

So roughly a sixth of the chain is *consistent with* official-stack mining of
a published model. That is the strongest real-inference signal yet, and the
n=3 fixture sample (which matched no model) badly under-represented the
corpus.
Per the roadmap's binding reframing: this is "consistent with the published
vLLM-plugin shape signature", **not** a claim that inference occurred; the
discrimination bound is Phase 8's T3 mixture test. Caveat: m = 32,768 exceeds
typical vLLM batch bounds (~16k), a Phase 8 question, not a conclusion.

Also new against the fixture-era picture:

- Full-chain rank histogram: 64 → 28,417 · 128 → 46,611 · 256 → 10,863 ·
  512 → 5,836 · 1024 → 4,668 · **32 → 1** · 0 → 1 (genesis). The early chain
  mined heavily at rank 64 (an official compiled kernel), and exactly one
  block used rank 32, the old reference default.
- Per-pool rank crosstab is live for five labeled pools + the unattributed
  remainder (always shown, never redistributed).

## Method / caveats

- All figures from the public API of the deployed release
  `ba3db02ecb3b-w81398ae`; reproducible with two curl commands per table.
- Census is whole-window aggregate (REPEATABLE READ snapshot); series carry
  ≤5,000 newest points per window; boundary-local slices used above.
- Shape-consistency statements are geometry only (T1/T2 screens); no
  distributional test has run yet (Phase 8.2), and no claim of served
  inference is made or implied.
