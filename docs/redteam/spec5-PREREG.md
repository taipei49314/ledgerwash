# spec 5 PREREG — negative-space escape closure (locked before any run)

Locked before implementation, before any scan, and before any push that triggers
CI. Written against the red-team findings in `docs/redteam/ACCEPTANCE.md` (the
original 21-case suite) and the takeover record in `docs/tasks/LW-002-redteam-coverage.md`.
Judge for all predictions below: the spec 5 candidate built from the branch that
carries this file. The frozen PR2 judge (`dc133028fb7405ed61c315ea3efbee26f134d015`)
remains the baseline in every replay. No product code, test, fixture or scan is
executed on the work machine (EC POLICY `work-machine-local`); every run happens
on GitHub-hosted CI or the EC pool.

## Root cause being closed

The 2026-10-01 unknown-state red-team round showed that every structural escape
walks the same negative space: **the keys that gate verification (timestamps,
the `time` field, `expected_head` type, directory depth) are held by the
audited writer, and in several rules "absent / empty / wrong type / wrong depth"
is equivalent to "pass".** Spec 4 made these states visible as residuals and
blockable under `--require-complete`; spec 5 promotes the five mechanically
distinct patterns to findings so the default gate sees them too. Frozen rule
IDs, severities and default outputs do not change (SPEC §10 changelog records
each addition).

## New rules (spec 5, engine 0.5.0)

| rule | severity | pattern | closes |
|---|---|---|---|
| `DONE_TIME_UNESTABLISHED` | high | DONE, zero receipts, and the closure `time` is missing, empty, unparseable or redaction-shaped, while the ledger does contain receipts | R2a (time omitted), R3 task side, R5 (redaction as era kill switch at task level) |
| `DONE_TIME_BACKDATED` | high | DONE, zero receipts, `time` parses before the earliest receipt `recorded_at`, but the task file's birth commit is dated on/after that earliest receipt — the pre-system carve-out claim is contradicted by the file's own git history | R2b (backdated time) |
| `ERA_UNDETERMINABLE` | warn | receipts exist but none has a parseable `recorded_at`; era-aware verification is unenforceable ledger-wide (fired once per scan) | R3 ledger side, R5 ledger side (A09 shape) |
| `RECEIPT_ORPHAN` | warn | a receipt's nonempty string `task_id` names no loaded task record (mirror of DANGLING_REF for receipt→task identity) | R9 (orphan receipts) |
| `PIN_NOT_COMMIT` | warn | a receipt's `expected_head` resolves to an existing non-commit object; fingerprint anchoring requires a commit, so claimed digests are silently unverified | R1 (existing blob-sha anchor kills fingerprint verification at zero findings) |

Design boundaries, declared in advance:

- `DONE_TIME_UNESTABLISHED` has **no birth-date carve-out**: an unusable closure
  time is surfaced regardless of file age. Honest pre-system tasks carry usable
  times (round-0 corpus); a redacted or empty time is mechanically
  indistinguishable from an erased one, and R5 showed the redaction shape is
  writer-self-certified.
- `DONE_TIME_BACKDATED` keeps a carve-out (birth before earliest receipt ⇒ no
  finding): that is the honest legacy shape the era carve-out was built for.
  An attacker must rewrite history to defeat it, which breaks fingerprints and
  chain pins elsewhere.
- Ledgers with **zero loaded receipts** keep residual-only semantics (SPEC §3
  "no-ledger ≠ clean-ledger"): the new DONE rules require at least one loaded
  receipt so the receipt system is demonstrably present at the epoch.
- Timestamps remain self-declared claims (SPEC §3.1); git commit dates are used
  only as file-history corroboration, never trusted as execution truth.

## Prediction 1 — the preserved original 21 cases (replay vs frozen PR2 judge)

For every one of the 21 preserved cases: the candidate's **frozen-14 findings
are byte-identical to the baseline judge's** (rule, path, locator, before,
after, fingerprint, severity), except as listed. New-rule deltas:

| case | predicted candidate delta | predicted candidate finding_verdict |
|---|---|---|
| `A3-MALFORM-TIME` | +1 `DONE_TIME_UNESTABLISHED` (high) on T-800 (DONE, zero receipts, `time="yesterday-ish"`, ledger has a dated receipt) | **block** (baseline: pass) |
| every other case (20) | no new-rule findings | unchanged vs baseline |

Explicit non-predictions (held as part of the preregistration):

- `A2-BACKDATE-TIME` is predicted **not** to fire `DONE_TIME_BACKDATED`: the
  fixture commits everything at `2026-09-28T00:00:00Z`, so the task file's
  birth (00:00Z) predates the era receipt's recorded_at (10:00Z) and the
  pre-system carve-out applies. The fixture's fixed dating masks the attack it
  encodes; the realistic variant (file born inside the receipt era) is covered
  by dedicated unit fixtures and qualify plants, and stays an honest
  documented limit of the preserved suite.
- `A1-DELETE-RECEIPTS` and `A4-SUBDIR-RECEIPT`/`A4B`/`A4C` stay findings-silent
  in default mode (zero-loaded-receipts and hidden-entry semantics remain
  residual/coverage territory per the design boundaries above); strict mode
  keeps blocking all 21 cases because coverage stays incomplete everywhere.

## Prediction 2 — qualify corpora (frozen finding matrix)

Main corpus additions (all inside the planted branch; the clean control gains
nothing and keeps zero findings/residuals):

| plant | expected findings |
|---|---|
| `T-912` (c2: DONE, zero receipts, `time=2025-06-01`, file born in the receipt era) | `DONE_TIME_BACKDATED` 1 |
| `T-913` (c0 at 2025-12-01: DONE, zero receipts, pre-system closure time, file born before the first receipt) | silent (backdate carve-out) |
| `T-914` (c0: DONE, zero receipts, `time=""`) | `DONE_TIME_UNESTABLISHED` 1 |
| `T-910` (existing redacted-time case) | additionally `DONE_TIME_UNESTABLISHED` 1 (total across main corpus: 2) |
| `r915` (c3: receipt bound to nonexistent `T-999`) | `RECEIPT_ORPHAN` 1 |
| `r916` (c2: receipt whose `expected_head` is the existing blob sha of `evidence/notes/clean-note.md`) | `PIN_NOT_COMMIT` 1 |

Negspace corpus (new, era-dead by construction): `ERA_UNDETERMINABLE` 1,
`DONE_TIME_UNESTABLISHED` 1 (task with no `time` key), `RECEIPT_ORPHAN` 1
(receipt bound to absent `T-802`), `NO_OPERATION_HISTORY` 0 (system_start
unestablishable — the A09 shape now surfaces as the ERA warning instead of
silence), everything else 0.

Observation deltas on the main corpus, declared now: loaded task count
11 → 14 (`{"1": 14}`); self-signing `{"same": 2, "differ": 1}` (r916's actor
differs from T-902's owner).

## Prediction 3 — paired coverage controls (36)

The three complete-positive controls (`COMPLETE-LIFECYCLE`,
`COMPLETE-CLAIMED`, `COMPLETE-REPAIR`) keep `default findings == []` — no new
rule fires on a complete ledger. Incomplete controls may gain new-rule
findings; their `expected_rule`/`expected_check` assertions are
presence-only and unaffected.

## Prediction 4 — pinned real EC epochs (b8761e95, 1b92c81)

Frozen-14 finding identities: **zero added, zero removed** (same contract as
spec 4 acceptance). New-rule additions cannot be counted without running; they
are declared MEASURE-AND-DISCLOSE: every new-rule finding on a real epoch is
reported per rule with locators, classified against this document's rule
definitions, and shown to the human before any acceptance. Expected sources:
legacy privacy-masked DONE tasks with no receipts
(`DONE_TIME_UNESTABLISHED`), and at most a handful of
`RECEIPT_ORPHAN`/`PIN_NOT_COMMIT` shapes. `ERA_UNDETERMINABLE` and
`DONE_TIME_BACKDATED` are predicted 0 on both epochs (receipts carry parseable
`recorded_at`; pre-system task files predate the receipt era in git history).

## Falsification

The replay harness hard-fails if any frozen-14 identity changes, if a new-rule
delta differs from Prediction 1, if a complete control gains findings, or if
raw replay bytes differ across seeds. The real-epoch run hard-fails on any
removed finding or frozen-rule addition. A wrong prediction above is recorded
as `not-held` in the closeout, never patched into the prediction after the
fact.

## Amendment 1 (2026-10-16, after the first CI run — recorded, original text above unchanged)

Prediction 2's observation deltas were wrong on one number: self-signing
`differ` is **12**, not 1. Eleven pre-existing mimo receipts
(r902a–f, r903a/b, r904a, r905a, r906a) already had `actor != owner`; only
r916 is new. The original prediction silently under-counted because the old
assertion never checked `differ`. Not-held as written; the corrected
expectation `{"same": 2, "differ": 12}` ships with the test, not by editing
this document's original text. No scan-behavior prediction changed: the CI
failures were a test-fixture date-forwarding bug and this assertion, not an
engine or rule delta.

NOT_RUN：工作機規則（POLICY work-machine-local），no product code, tests,
fixtures, scans, builds or dependency installation ran on this machine; all
verification is GitHub-hosted CI and the EC pool, per the task record.
