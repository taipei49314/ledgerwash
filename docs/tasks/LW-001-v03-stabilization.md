# LW-001 — v0.3 stabilization and EC pool acceptance

- Owner: `LAPTOP-16NUA5I8`
- Status: DONE — implementation and acceptance delivered in PR #2; merge pending review.
- Human instruction (2026-10-01, Asia/Taipei): 「先讀EC怎麼記帳 工作流 然後接手legerwash」; clarification: 「在github」; chosen scope: 「先穩定 v0.3：修缺口並補 pool 驗收」.
- Product baseline: `230b804245c535a719404a62855523e81d144ea4` (spec 3, v0.3.0).
- EC rules reviewed at `293924e1b299aa908958612855ea785c04344e15`: CURRENT, POLICY, PLAN, governance README and mechanical workflows. `ec_status status` passed source consistency (481 rows, 20 policies); its expired GitHub snapshot is not a live observation.

## Handover checks

GitHub has one merged PR (#1), no open PRs and no issues at takeover. Only remote
`main` exists, pinned to the baseline above; the new checkout is clean and has no
unpublished commits. Other checkouts and the other work machine's unpublished work
are **未核對**; absence on GitHub is not evidence of their absence locally.

The baseline has nine successful GitHub-hosted CI jobs (3 OS × Python 3.11–3.13),
[run 36538975835](https://github.com/taipei49314/ledgerwash/actions/runs/36538975835).
This is historical verification of the baseline, not acceptance of this patch.

## Delivered scope

Restore the existing spec 3 contracts without adding rules or changing the spec:

1. Read trees and receipt birth history at the resolved epoch SHA, including a
   receipt path's latest addition after deletion/recreation and renamed paths.
2. Report nested bool/int drift without crashing.
3. Skip dependent chain/anchor checks when a task's receipt ordering is unknown,
   retaining timestamp findings and explicit verification residuals.
4. Keep malformed receipt task IDs as residuals without crashing observations.
5. Add regression tests and an exact-SHA EC pool workload that runs the complete
   suite, frozen gates, qualify and independent-process JSON replay.

## Validation and delivery

Implementation and regression fixtures are complete. A separate read-only review
confirmed coverage of all four fixes and the EC Windows workload environment;
no product code was executed by that review. The entry point also retains a
structured failure report if the dependency lock is unreadable.

NOT_RUN：工作機規則（POLICY work-machine-local），this work machine did not run
product code, pytest, qualify, lint, builds or dependency installation.

Candidate `5a7687a469f878b1bdbd9f9e7b5dc036406a6489` passed nine GitHub-hosted CI
jobs, **53 tests each**, and qualify ([run 36834317163](https://github.com/taipei49314/ledgerwash/actions/runs/36834317163)).
The approved EC Windows pool workload also passed **53 tests, zero failures,
errors or skips**, qualify and byte-identical independent-process JSON replay
([run 36836523378](https://github.com/taipei49314/estate-consolidation/actions/runs/36836523378)).
Its requested/actual source SHAs agree; the source checkout remained clean.
Host: `LAPTOP-QL063DVV`; generation: `8b1bcfb4b5dc0588.1`.

Raw logs, JUnit, dependency locks and result/check records are retained in EC's
private ref `sweep-receipts/36836523378/1/workload-v03-verify`. These findings are
synthetic regression coverage, not artifact authenticity or model accuracy.

ledgerwash is an independent repository. Its workload was explicitly approved by
the human and connected through EC task
[T-480](https://github.com/taipei49314/estate-consolidation/blob/main/governance/tasks/T-480.json).
[EC PR #108](https://github.com/taipei49314/estate-consolidation/pull/108) passed pool
integrity and merged; App access, registry hash and both repository choice lists
are aligned. Product details and fixes remain in this repository.

This final evidence update changes only this task document. The PR's latest head
will receive a fresh exact-SHA pool check and the ordinary nine CI checks before
being marked ready; their immutable run/check records live outside the source
tree to avoid changing the tested head just to append another run ID.

S4's internally consistent forged artifact remains outside spec 3's authenticity
boundary. Spec 4, model experiments, release and publication are outside this task.

PR disposition: [PR #2](https://github.com/taipei49314/ledgerwash/pull/2) retained for
review, with implementation and acceptance delivered. No merge or release is
claimed. Subsequent fixes within this same bounded goal update this task.
