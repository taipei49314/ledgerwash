# Spec 5 migration-continuity correction — preregistration

Date: 2026-10-17 (Asia/Taipei). Task: LW-003; parent implementation `ed4bc99`,
documentation head `7abc3c9ba71cf75ec817844ca00fc9c7118d2ca2`.
Human instruction: 「好，照你建議做，先預註冊合法遷移／偽造遷移的對照案例，再修正 spec 5 判則，走 EC pool 重驗。」

This document is committed before the correction and its new tests execute.
It supplements, never rewrites, [the original PREREG](spec5-PREREG.md) and
[the first pool result](SPEC5-VALIDATION.md). The observed 170 BACKDATED and
102 UNESTABLISHED additions per epoch remain the prior result.

## Contract fixed before implementation

Only DONE_TIME_BACKDATED gains a narrow migration-continuity exception. A JSON
path introduced by a corroborated representation migration cannot, by its birth
alone, contradict the migrated task's claimed closure. This does not verify the
task's truth, pre-receipt existence, authority, execution or trusted time.

The exception requires all of the following, otherwise the existing predicate
still applies:

1. The current zero-operation task has exactly one migration history entry and
   is type-strictly identical to its record at its latest path-addition commit.
   Supported task/history field shapes and integer schema/line types are exact.
2. At that birth commit, an EC task-store v1 manifest binds the task's canonical
   SHA256 and its migration archive. The same migration provenance remains at
   the pinned scan epoch. Unsupported or ambiguous shapes do not qualify.
3. Migration source_commit equals the birth commit's actual first parent, not
   an arbitrary existing object, sibling, older ancestor or supplied date. That
   parent has no structured task-store manifest and no task at this path.
4. A safe, content-addressed archive is a regular Git blob at birth and at the
   scan epoch. Both copies have the declared raw SHA256 and equal the parent's
   actual LEDGER.md bytes. The task and manifests are regular blobs too.
5. The referenced positive integer line has its declared raw row SHA256. The
   archive contains one unambiguous six-column row for that ID. Its id,
   description, qualified status, parsed state, owner, time and evidence equal
   the task fields. Support EC's escaped pipes, backtick spans and raw CRLF/BOM
   preservation; no lossy hash normalization. Other migration/guard semantics
   are outside this exception.

No new finding ID, severity, coverage-completeness exception or default gate.
NO_OPERATION_HISTORY, DONE_TIME_UNESTABLISHED and the other seventeen rules
remain unchanged. An unusable closure time still cannot support the era check;
migration provenance does not turn it into an orderable time. Strict continues
to block unsupported migration coverage even when BACKDATED is absent.

## Supplementary controls and numeric predictions

All fixtures use a live receipt era, an in-era JSON birth commit, and a claimed
pre-era DONE closure except the explicit unusable-time control. These controls
are separate from the preserved original 21 cases.

| Case | Expected BACKDATED | Expected default / strict |
|---|---:|---|
| Valid unchanged migration, UTF-8/LF | 0 | pass / block |
| Valid unchanged migration, BOM + CRLF archive | 0 | pass / block |
| Valid row with escaped pipe and backtick pipe | 0 | pass / block |
| Label alone, no bound manifest/archive | 1 high | block / block |
| Self-consistent archive invented in migration commit, differs from parent ledger | 1 high | block / block |
| Incorrect archive digest | 1 high | block / block |
| Incorrect row digest | 1 high | block / block |
| Reference another task's row | 1 high | block / block |
| Changed closure time relative to authentic parent row | 1 high | block / block |
| Boolean line number in place of integer | 1 high | block / block |
| Source pin is an older ancestor instead of direct parent | 1 high | block / block |
| Missing parent LEDGER | 1 high | block / block |
| Migration label/provenance added after task birth | 1 high | block / block |
| Archive edited after task birth | 1 high | block / block |
| Task edited after birth, with current hashes recomputed | 1 high | block / block |
| Duplicate legacy task ID in archive | 1 high | block / block |
| Parent already has a structured manifest | 1 high | block / block |
| Unsupported manifest shape/version | 1 high | block / block |
| Symlink-mode archive containing otherwise matching blob bytes | 1 high | block / block |

For every pair, default/strict findings and coverage must be equal, and the
specific BACKDATED locator is checked. Unsupported/forged provenance must not
crash the scan. The valid cases have zero findings but incomplete migration
coverage. Positive acceptance here means matching this bounded contract, not
authentication of a legitimate actor.

Two explicit boundary controls:

- **Self-consistent forged parent:** append a fake legacy row to the parent,
  then migrate it with completely matching bytes, hashes and fields. Predict
  BACKDATED absent, default pass, strict block. The checker cannot authenticate
  the prior row; this remains a disclosed default-mode escape, not detection.
- **Migrated unusable time:** valid continuity with a redacted closure. Predict
  exactly one high DONE_TIME_UNESTABLISHED, no BACKDATED, default/strict block.

## Whole-run predictions

- Existing 107 tests remain passing; all new cases above pass their contracts.
  Qualify keeps 19 distinct rules across its two corpora and the original plants.
- Original 21: baseline 17 pass / 4 block, candidate 16 pass / 5 block, strict
  21 block; unchanged frozen fourteen identities and A3-only declared delta.
- All 36 coverage controls retain their contracts. Strict completeness and
  coverage counters are not relaxed by migration continuity.
- Fixed real epochs stay `b8761e95bbd92c4cd1d1917cbf70ff84e74c97f8` and
  `1b92c81036db6196af558b33cb455e2fdad42dce`; frozen PR2 judge remains
  `dc133028fb7405ed61c315ea3efbee26f134d015`. All 12 fresh scans and seed replay
  must succeed. Frozen identities must remain unchanged.
- Predict BACKDATED **0 per real epoch**, removing the prior 170 only relative
  to `ed4bc99`; predict UNESTABLISHED **102 per epoch**, unchanged. Thus total
  candidate findings should become **308 historical / 319 pinned-current**.
  Coverage and existing residuals remain unchanged and both epochs stay block.
  This is a falsifiable prediction, not assumed success: every remaining or
  unexpected finding will be disclosed. No known counterexample is removed
  from the corpus, and no original prediction is retroactively corrected.

## Execution and acceptance

Use the unchanged approved spec5-verify declaration and its existing full suite,
21-case replay, 36 controls and pinned real scans. Preserve all attempts and
private raw outputs. Supplementary case names and JUnit results, source SHA,
native CI and pool receipt are reconciled in a new report. The workload's frozen
baseline is PR2, not the old spec5 candidate: the 170 intended removals must be
compared explicitly against the preserved prior pool output.

No work-machine product execution. No new model calls, corpus epochs,
workload limits, publication or product PR merge. Technical PASS and the narrow
continuity exception do not grant human product acceptance.
