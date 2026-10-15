# LW-003 — spec 5: negative-space escape closure

- Owner: `LAPTOP-01AGNPJU`.
- Status: CLAIMED — implementation and replay in flight; no merge or release claimed.
- Human instruction (2026-10-16, Asia/Taipei): 「開始實驗 直接朝你規劃 你執行
  遇到重大決策問我」, following the status review that surfaced PR #2/#3 and
  the pending red-team dispositions.
- Product parent: PR #3 head `14bed98aff9bfbe58d9f44b3c867f7e96b88ae59`
  (spec 4, v0.4.0). This work stacks on that branch and does not modify the
  preserved 21-case suite, the frozen PR2 baseline, PR #2 or PR #3.

## Bounded scope

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
