# LW-003 — spec 5: negative-space escape closure

- Owner: `LAPTOP-01AGNPJU`.
- Status: DONE for the authorized implementation and remote validation delivery
  (2026-10-17). Migration-continuity controls and exact pool predictions passed.
  Earlier validation and failed predictions remain preserved; human product
  acceptance and PR merge/release remain separate.
- Human instruction (2026-10-16, Asia/Taipei): 「開始實驗 直接朝你規劃 你執行
  遇到重大決策問我」, following the status review that surfaced PR #2/#3 and
  the pending red-team dispositions.
- Product parent: PR #3 head `14bed98aff9bfbe58d9f44b3c867f7e96b88ae59`
  (spec 4, v0.4.0). This work stacks on that branch and does not modify the
  preserved 21-case suite, the frozen PR2 baseline, PR #2 or PR #3.

## Bounded scope

Resumption (2026-10-17, direct human instruction in the same Codex session):
「好，照你建議做，先預註冊合法遷移／偽造遷移的對照案例，再修正 spec 5 判則，走 EC pool 重驗。」
This resolves the earlier wait for direction within the bounded correction.
The [migration preregistration](../redteam/spec5-migration-PREREG.md) fixes the
continuity contract, forged controls and remaining self-consistent forgery limit
before implementation. EC records only the new pool dispatch and receipt review;
the completed T-549 account and original pool results are not reopened.

1. Lock `docs/redteam/spec5-PREREG.md` before any run (done, same commit as
   this file).
2. Spec bump 4 → 5 (v0.5.0): five new rule IDs closing the negative-space
   escapes from the 2026-10-01 red-team round (R1, R2, R3, R5, R9); frozen
   rules unchanged.
3. Implement, plant the qualify corpora, extend the replay comparison to
   frozen-identity-plus-declared-delta, and let GitHub-hosted CI run the full
   suite on the pushed branch.
4. Real-epoch replay on the EC pool under a separate human-approved workload
   declaration; PR #2/#3 merge disposition and any acceptance stay with the
   human.

Out of scope: artifact authenticity / runner-evidence implementation (design
only per LW-002), R7 default-exit semantics (SPEC §3/§9 design, pending human
decision), release, publication, model-based adversarial rounds.

## Handover checks

Branch base = PR #3 head, fetched 2026-10-16 from origin; working tree clean
before the branch was cut. `main` fast-forwarded `9a45423..230b804`. LW-001/
LW-002 are DONE with delivery retained in PRs #2/#3 (open, stacked); no
unpublished commits were found on origin. The other work machine's local
state was not inspected from here — absence on GitHub is not evidence of
absence locally (same caveat LW-001 recorded).

NOT_RUN：工作機規則（POLICY work-machine-local），this machine read, edited and
ran git/gh only; no pytest, qualify, scan, fixture build, venv, build or lint
was executed locally. All product verification is remote.

## Follow-up scope and pre-run record (2026-10-16)

Human instruction in Codex session 01a14509-7e7a-7501-84b0-858cc8fd298c:
「好，照你建議做，先補回填 commit 日期的對抗案例並修正文義，再走 EC pool 做 spec 5 驗收。」

Owner remains LAPTOP-01AGNPJU. Refreshed PR #4 at
`d43627e765d9ba2a4494e841ae582f122fc7f59a`; this checkout was clean and had no
unpublished commits. Other local sessions/checkouts were not inspected.
The bounded follow-up adds a supplementary append-only backdated-commit case,
its positive control and corrected capability wording, then integrates and runs
the existing spec5-verify declaration through EC. Amendment 2 records predictions
before the new tests. No engine predicate/default-gate change is intended.
Product PRs #2/#3/#4 remain for human merge disposition; no release is included.

## Remote validation closeout (2026-10-16)

The authorized follow-up is delivered at implementation/test source
`ed4bc99285239a82cb9d236c7fe724a7c09f16d1`. Native CI passed all nine jobs, each
with 107 tests and qualify. EC T-549 integrated the unchanged declaration through
PR #189 and dispatched pool run `38918945942`, attempt 1, on LAPTOP-F2NFAMQI.
The complete pool run passed: 107 tests, original 21, 36 paired controls and
12 pinned real scans; source remained clean, replay bytes were equal and no
step timed out. Both supplementary append-only cases passed.

The [validation reconciliation](../redteam/SPEC5-VALIDATION.md) records a material
not-held prediction: each real epoch gained 170 DONE_TIME_BACKDATED findings,
contrary to the predicted zero. All share the structured-task migration birth
date; representative source evidence confirms old tasks existed before their
JSON paths. Another 102 high time-unestablished findings have 98 range/masked
timestamp info findings and four malformed timestamp warn findings. These are mechanical
diagnostics, not established fabricated completion. Private per-finding triage
stays in EC; public aggregates and provenance are in the report.

P1's A4B/A4C findings-silent sentence and P2's original self-signing differ=1
also remain explicitly not-held as written. The original preregistration is
preserved. No predicate was altered after seeing these results.

Unblock condition: human decides how verified migration provenance should affect
the new high findings. A further change should first preregister legitimate and
forged migration controls, then validate a bounded rule change through the pool.
The present follow-up does not implement that new design or approve these
findings. Product acceptance and PR merge/release remain with the human.

## Migration-continuity revalidation closeout (2026-10-17)

The later human instruction above authorized this bounded resumption. Prereg
`b1aef39497541fe1e3c669fc3d52fcb290f2b87d` preceded implementation/tests at
`a59fc21bad45e4a230d11aa1a501956cfb2fc1fa`. Native CI `38956981581` passed all
nine jobs on synthetic PR merge `23e85e92b25b5c93b2c80407b39a3c7dc1c44cc5`,
each with 128 tests and qualify. EC T-551 dispatched the exact candidate with the unchanged
spec5-verify declaration once in run `38957954641`, attempt 1, on
LAPTOP-50KP71KA. The pool passed 128 tests including all 21 new named controls,
the original 21 cases, 36 coverage controls and 12 fixed real scans. Sources
remained clean, replay bytes were equal and no step timed out. All 83 selected
receipt files matched publication SHA256 and byte length.

The [new reconciliation](../redteam/SPEC5-MIGRATION-VALIDATION.md) records all
follow-up predictions held: 478/489 findings become 308/319, exactly the prior
170 BACKDATED identities removed per epoch, zero new identities, 102
UNESTABLISHED retained. Other findings, coverage, residuals and frozen rules
remain unchanged. Both epochs still block with incomplete coverage.

The narrow exception checks representation continuity, not historical truth or
authority. The consistent forged-parent case deliberately remains a default
escape and strict block; the append-only backdated-committer limitation also
remains. The original not-held predictions and report stay untouched. This
closes the authorized delivery, without product acceptance, merge or release.
