# LW-002 — red-team replay, verification coverage and real-ledger regression

- Owner: LAPTOP-16NUA5I8.
- Status: IN_PROGRESS.
- Human instruction (2026-10-01 Asia/Taipei): 「好 執行」, accepting the staged
  plan after the supplied REDTEAM-REPORT.md review.
- Product parent: PR #2 at dc133028fb7405ed61c315ea3efbee26f134d015. This task
  preserves its exact source as a hashed Git archive; PR #2 remains unchanged.

## Bounded scope and order

1. Replay all 21 original cases on the fixed PR2 judge on EC pool, preserving
   full stdout/stderr, fixture/judge identity, controls and independent-process
   replay. Original inputs are immutable copies in docs/redteam/inputs/.
2. Define and implement receipt/adapter verification coverage and an explicit
   strict consumer gate. Contract changes get a separate spec/version commit.
   Keep legitimate state transitions and historical import cases as controls;
   do not equate Git timestamps with trustworthy execution time.
3. Regress the pinned historical and current real EC epochs, explaining finding
   and coverage differences rather than demanding pass for an imperfect ledger.
4. Write a design for independently sourced runner evidence; do not implement
   network access, model experiments, signing infrastructure, release or deployment.

Product details remain here; EC accounts only the approved workload integration
and dispatch. A new declaration must be concrete and human reviewed before EC
registry changes or dispatch; the existing v03-verify grant is unchanged.

## Evidence quality

The submitted report tested baseline 230b804, not PR2. Its suite actually contains
21 cases (3 controls + 18 attacks). Its surviving results.json contains only A4C,
which has a status warning. A11's original base lacks after_record from the start;
A10 likewise lacks an initial snapshot. Preserve those originals, then add paired
controls rather than quietly revising the original result claims.

This work machine reads, edits and uses Git/GitHub; it does not execute product,
tests, fixtures, dependency installs, builds or lint.
NOT_RUN：工作機規則（POLICY work-machine-local），all product verification is remote.

PR disposition: deliver the bounded change in a separate PR stacked on PR #2,
retained for product review; no merge/release is claimed by this task.
