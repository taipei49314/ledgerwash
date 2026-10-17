# Spec 5 migration-continuity revalidation

Date: 2026-10-17 (Asia/Taipei). Task: LW-003; EC execution account: T-551.

The bounded correction passed its preregistered contracts and EC pool replay.
Each fixed real epoch loses exactly the prior 170 `DONE_TIME_BACKDATED`
identities and keeps its 102 `DONE_TIME_UNESTABLISHED` identities. All other
finding identities, coverage and residuals are unchanged. Both real epochs
still return **block** with incomplete coverage.

This is technical validation of representation continuity. It does not
authenticate a migration actor, the prior task record, execution or time.
In particular, the self-consistent forged-parent control still passes default
mode and is blocked by strict mode's incomplete-coverage gate.

## Fixed scope and sources

The human authorized the legitimate/forged controls, bounded rule correction
and pool revalidation in the same session. The
[migration preregistration](spec5-migration-PREREG.md) was committed first at
`b1aef39497541fe1e3c669fc3d52fcb290f2b87d`. Implementation and tests were reviewed
at `a59fc21bad45e4a230d11aa1a501956cfb2fc1fa` before dispatch.

Only `DONE_TIME_BACKDATED` gains the exception. The unchanged task at JSON birth,
supported manifest, canonical task hash, content-addressed regular archive,
raw archive/row hashes and seven task fields must agree. The archive must equal
the birth commit's actual first-parent `LEDGER.md`, before that parent had the
structured manifest or this task path. Missing, contradictory, unsupported or
nonregular inputs do not qualify. See the preregistration for the exact contract.
This is narrower than complete EC migration/guard verification; coverage remains
explicitly unverified. `DONE_TIME_UNESTABLISHED`, other rules and gates are unchanged.

The declaration, dependency lock, workload entry, original 21 cases, coverage
controls and corpus pins were unchanged. The
[original preregistration](spec5-PREREG.md),
[first pool reconciliation](SPEC5-VALIDATION.md) and its failed predictions are
preserved. This follow-up does not retrospectively turn those predictions into PASS.

| Evidence | Bound identity |
|---|---|
| Native CI | [38956981581](https://github.com/taipei49314/ledgerwash/actions/runs/38956981581), candidate `a59fc21bad45e4a230d11aa1a501956cfb2fc1fa` |
| EC pool | [38957954641](https://github.com/taipei49314/estate-consolidation/actions/runs/38957954641), attempt 1, job `117165493877` |
| EC source | `4e47b63ffc1b33c99236e66e08c18ba525ab067e` |
| Actual runner | `LAPTOP-50KP71KA-workload`, generation `8b1bcfb4b5dc0588.1` |
| Declaration SHA256 | `ebf5c0448897bc058c861a78770fcc81a0696ccc2b7520f532d6b44835381945` |
| Private receipt | EC commit `3421fe1d0f5d4657fafeea5a931af434b28aca1f`, ref `sweep-receipts/38957954641/1/workload-spec5-verify` |
| Prior comparison receipt | EC commit `b24c196a3af8434585f1fa2a7e60dec524b416c2`, run `38918945942`, candidate `ed4bc99285239a82cb9d236c7fe724a7c09f16d1` |

The workflow succeeded from 19:51:12Z to 20:22:08Z on 2026-10-16. The workload
finished at 20:21:48Z after 1810.844 seconds on Windows 11 / Python 3.12.10.
No step timed out; suite time was 280.563 seconds and real-ledger time was
1249.750 seconds, within the unchanged limits. Requested, actual and final
product SHAs match; saved initial/final git-status outputs are empty.

Receipt publication is `preserved`, with matching run, attempt, EC SHA and host.
All 83 selected saved files match the publication manifest's SHA256 and byte
length: root outputs, the original/control result JSONs and every real-ledger
output. Full private identities and hash comparisons remain in EC T-551 evidence.

## Supplementary controls

All **128 tests** passed with zero failures, errors or skips, including all
21 named `test_migration_continuity_contract[...]` JUnit cases. The original
107 tests remain passing. Native CI also passed all nine Windows/macOS/Linux
and Python 3.11/3.12/3.13 jobs, each with 128 tests and qualify. Its checkout was
the synthetic PR merge `23e85e92b25b5c93b2c80407b39a3c7dc1c44cc5` (candidate
`a59fc21` into PR #3 base `14bed98`); the EC pool checked out the exact candidate
SHA. That historical native CI run does not establish raw-byte equality across
operating systems. The later [v0.5.0 release verification](../releases/v0.5.0-VALIDATION.md)
adds a separately preregistered, bounded raw-byte comparison with hosted producers
and independent EC verification; it does not change this run's scope or result.

| Cases | Observed result |
|---|---|
| `lf`, `bom-crlf`, `escaped-pipes` | Zero findings; default pass, strict block; target migration coverage remains unverified |
| `label-only`, `invented-archive`, `wrong-archive-digest`, `wrong-row-digest`, `wrong-row-id`, `changed-closure`, `boolean-line`, `older-source`, `missing-parent-ledger`, `late-label`, `changed-archive`, `changed-task`, `duplicate-id`, `structured-parent`, `unsupported-manifest`, `symlink-archive` | One high BACKDATED at the expected target; default and strict block; no scan crash |
| `forged-parent` | Zero findings; default pass, strict block — the preregistered escape is reproduced |
| `unusable-time` | One high UNESTABLISHED, no BACKDATED; default and strict block |

The paired tests assert identical default/strict findings and coverage, with
the target's task profile and migration history explicitly unverified. Before
dispatch, read-only review tightened the target-specific coverage assertion and
made the incorrect-digest case bind history/manifest/path consistently while
leaving the raw archive bytes unchanged. These final tests are in the tested SHA.

## Preserved suites and real-epoch predictions

Qualify retains all 19 distinct rule IDs across its two corpora with exact
plants. Independent seed 1/17 raw JSON replay is equal. Original 21 results
remain baseline 17 pass / 4 block, candidate 16 pass / 5 block and strict
21 block; A3 is the only declared delta and frozen fourteen identities are
unchanged. All 36 coverage controls retain their contracts: three complete,
zero-finding strict passes and 33 incomplete strict blocks, with paired findings,
coverage and independent-process replay equal.

The frozen PR2 judge remains `dc133028fb7405ed61c315ea3efbee26f134d015`.
All 12 real scans (two epochs, three judges, two seeds) completed with raw replay
equal. Frozen findings have zero additions/removals relative to that judge.

| Fixed epoch | Old candidate findings | New candidate findings | BACKDATED | UNESTABLISHED | Result |
|---|---:|---:|---:|---:|---|
| Historical `b8761e95bbd92c4cd1d1917cbf70ff84e74c97f8` | 478 | 308 | 170 → 0 | 102 → 102 | block; coverage incomplete |
| Pinned current `1b92c81036db6196af558b33cb455e2fdad42dce` | 489 | 319 | 170 → 0 | 102 → 102 | block; coverage incomplete |

The comparison against the prior candidate uses rule, path, locator, severity,
before/after and fingerprint, not just totals. Removed identities are exactly
the prior BACKDATED set; no identity was added, and all other identities,
coverage and residuals match. Both epochs contain the same affected 170 task
identities; this is not 340 distinct tasks. Default/strict findings and coverage
remain equal. All migration follow-up predictions held.

The retained 102 UNESTABLISHED findings still concern unusable closure times:
98 have range/masked timestamp info findings and four have malformed timestamp
warn findings, as previously triaged. They do not establish fraudulent completion.
The earlier P4 zero prediction, P1 A4B/A4C findings-silent prose and original
P2 differ=1 prediction remain not-held as recorded in the first report.

## Acceptance boundary

The authorized controls, correction and pool revalidation are delivered.
Human product acceptance and PR merge/release are separate decisions. The
self-consistent forged-parent escape and append-only backdated-committer escape
remain disclosed; strict rejects their incomplete evidence. No new model round,
trusted-time or execution-authenticity claim is made.

NOT_RUN：工作機規則（POLICY work-machine-local），no local product/test execution,
fixture generation, scan, build, lint or dependency installation. Local receipt
review only reads saved remote outputs and compares their recorded fields/hashes.
