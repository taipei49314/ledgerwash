# LW-001 — v0.3 stabilization and EC pool acceptance

- Owner: `LAPTOP-16NUA5I8`
- Status: IN_PROGRESS
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

## Bounded delivery

Restore the existing spec 3 contracts without adding rules or changing the spec:

1. Read trees and receipt birth history at the resolved epoch SHA, including a
   receipt path's latest addition after deletion/recreation and renamed paths.
2. Report nested bool/int drift without crashing.
3. Skip dependent chain/anchor checks when a task's receipt ordering is unknown,
   retaining timestamp findings and explicit verification residuals.
4. Keep malformed receipt task IDs as residuals without crashing observations.
5. Add regression tests and an exact-SHA EC pool workload that runs the complete
   suite, frozen gates, qualify and independent-process JSON replay.

## Validation and next step

NOT_RUN：工作機規則（POLICY work-machine-local），this work machine does not run
product code, pytest, qualify, lint, builds or dependency installation.

ledgerwash is an independent repository. Product work stays here; only EC workload
approval/routing/dispatch will be recorded in EC. The current EC registry and
workflow choices do not include ledgerwash. Prepare the concrete declaration and
entry point for review before requesting the new-workload human gate (POLICY
governance-first L2, independent-repos). No pool acceptance is claimed yet.

S4's internally consistent forged artifact remains outside spec 3's authenticity
boundary. Spec 4, model experiments, release and publication are outside this task.

PR disposition: pending creation; retain for review and validation until the exact
head is accepted. Update this same task for subsequent work; do not create a new
product task for each patch.
