# LW-003 — spec 5 validation and prediction reconciliation

Technical validation completed at `ed4bc99285239a82cb9d236c7fe724a7c09f16d1`.
The workload passed, but the real-epoch `DONE_TIME_BACKDATED = 0` prediction
failed: each epoch gained 170 such findings. Product acceptance remains pending
a human decision on migration semantics. No product merge or release is claimed.
This later documentation closeout changes no engine predicates, tests, fixtures
or workload declaration.

## Supplementary adversarial case and corrected claim

The follow-up documents an append-only default-mode escape. Starting from a
complete ledger, a new direct-child commit can carry an old committer date and
append a receipt-less DONE task without changing prior tracked files. Default
mode passes; `--require-complete` blocks its missing operation history. The
otherwise identical in-era commit-date control produces high
`DONE_TIME_BACKDATED` and default block. This reproduces a limit, not successful
detection or an engine repair.

Amendment 2 was committed at `1384013ce183b29d740a560c762a9005638500ff` before
these tests ran. Both named cases are present and pass in pool JUnit:
`test_append_only_commit_date_limit[append-only-backdated-escape]` and
`test_append_only_commit_date_limit[in-era-date-positive-control]`.

## Remote evidence

| Evidence | Fixed source | Result |
|---|---|---|
| Native CI | product `ed4bc99` | Nine Windows/macOS/Linux × Python 3.11–3.13 jobs; 107 tests and qualify per job |
| EC integration | PR #189 head `f24f0880` | Integrity passed, including 1,526 main-suite tests and preceding contract checks; merged as `319e177c` |
| Spec 5 pool | product `ed4bc99`, EC `9581ec8d` | 107 tests, zero failures/errors/skips; qualify; original 21; 36 controls; 12 real scans; deterministic seed replay |

[Native CI](https://github.com/taipei49314/ledgerwash/actions/runs/38914306644),
[EC integration CI](https://github.com/taipei49314/estate-consolidation/actions/runs/38915176904),
[EC integration PR](https://github.com/taipei49314/estate-consolidation/pull/189),
[spec 5 pool run](https://github.com/taipei49314/estate-consolidation/actions/runs/38918945942).

Pool run `38918945942`, attempt 1, job `117033577216`, ran on
`LAPTOP-F2NFAMQI-workload`, generation `8b1bcfb4b5dc0588.1`, Windows Python
3.12.10. EC source was `9581ec8d30524aeac40ebb19019100d32f3a5ae7`; declaration
SHA256 was `ebf5c0448897bc058c861a78770fcc81a0696ccc2b7520f532d6b44835381945`.
Requested and actual product SHAs match; source remained clean and unchanged.
No workload step timed out. Planted replay scan exit 1 is the expected block.

Private receipt commit: `b24c196a3af8434585f1fa2a7e60dec524b416c2`, ref
`sweep-receipts/38918945942/1/workload-spec5-verify`. All 83 selected receipt
files match publication-manifest SHA256 and length: root outputs, nested result
JSONs and all real-ledger outputs. Raw private corpus scans and locators remain
in EC; this public report contains aggregates and source identities only.

## Predictions: held and not-held

The original [PREREG](spec5-PREREG.md) and its amendments remain unchanged.

| Prediction | Observed result | Reconciliation |
|---|---|---|
| P1 table: frozen fourteen rules unchanged; A3 alone gains high DONE_TIME_UNESTABLISHED | Baseline 17 pass / 4 block; candidate default 16 pass / 5 block; A3 gains the specified high finding on T-800; strict blocks all 21; seed replay equal | Held |
| P1 prose calls A4B/A4C findings-silent | A4B retains high NO_OPERATION_HISTORY / block; A4C retains STATUS_STATE_MISMATCH warn / default pass | Not-held as written: pre-existing prose error, not a frozen-rule regression |
| P2 finding plants and clean control | Qualify main covers 18 rule IDs, negspace covers 3, together all 19; exact planted counts/locators hold; T-913 stays silent; clean-control test passes | Held |
| P2 observations: task schema count 14; self-signing same 2 / differ 1 | Task schema count 14; same 2 / differ 12 | Original differ 1 not-held; Amendment 1 already records the correction; other stated counts hold |
| P3 paired controls | All 36 pass their contracts; three complete controls have zero findings and strict pass; 33 incomplete controls strict block | Held |
| P4 frozen identities | Zero frozen-rule additions/removals and zero new-rule removals at both epochs | Held |
| P4 ERA_UNDETERMINABLE = 0 | Zero at both epochs | Held |
| P4 DONE_TIME_BACKDATED = 0 | 170 at each epoch | Not-held; migration-birth confound below |
| P4 measure and disclose other new rules | 102 DONE_TIME_UNESTABLISHED at each epoch; RECEIPT_ORPHAN and PIN_NOT_COMMIT both zero | Measured and disclosed; not human-accepted by workload PASS |
| Amendment 2 append-only escape and positive control | Both named pool tests pass; default escape reproduced, strict mitigation retained | Held |

## Real-epoch migration confound

Fixed historical epoch: `b8761e95bbd92c4cd1d1917cbf70ff84e74c97f8`.
Fixed current epoch: `1b92c81036db6196af558b33cb455e2fdad42dce`.
Frozen PR2 judge: `dc133028fb7405ed61c315ea3efbee26f134d015`.
Each epoch was scanned by baseline, candidate default and candidate strict,
with seeds 1 and 17: all 12 scans completed with identical per-judge replay bytes.

| Epoch | Baseline findings | Candidate findings | New BACKDATED | New UNESTABLISHED |
|---|---:|---:|---:|---:|
| Historical | 206 | 478 | 170 | 102 |
| Pinned current | 217 | 489 | 170 | 102 |

The same 272 added finding identities appear at both epochs; these are 272
distinct additions repeated in two scans, not 544 different task records.
All affected paths already have unsupported history/profile coverage gaps.
All 170 BACKDATED messages cite the same task-file birth date, coinciding with
structured-task migration. A migrated JSON file's introduction is not the
underlying task's original creation or completion. The current rule compares
those dates without validating the migration relationship, so its high findings
must not be interpreted as established fabricated completion.
The migration explanation is corroborated by representative original task and
pre-migration ledger reads; this review does not claim that every migration
archive binding was independently verified. Per-finding locators and categories
are retained in the private EC triage account.

Of 102 UNESTABLISHED additions, 98 also carry TIMESTAMP_REDACTED info findings
(range or digit-masked forms), and four carry TIMESTAMP_MALFORMED warn findings.
They cannot all be described as privacy redactions. The diagnostics establish
unorderable claimed times under this parser, not why the values have those forms.

Both real epochs remain finding-verdict block and coverage incomplete. Default
and strict findings and coverage are equal. Historical coverage counts remain
16,132 verified / 693 unverified / 324 mismatch; pinned current remains
18,714 / 693 / 324. Each retains the same operation-ordering residual. These
are check counts, not distinct offenses. No historical data was edited.

## Acceptance boundary and recommended follow-up

The pool result establishes reproducibility and the stated mechanical contracts.
It does not validate the failed zero prediction or settle whether migrated
legacy records should receive high BACKDATED findings. Human product acceptance
is pending; merging spec 5 before resolving that meaning is not recommended.

A follow-up should first preregister legitimate-migration and forged-migration
controls, then decide how verified migration provenance affects file-birth
corroboration. Merely trusting a writer-supplied migration label would introduce
another escape. That rule/design change is not part of this documentation and
test follow-up; neither the original predictions nor the measured findings were
rewritten to make the run look successful.

Native nine-job CI is not a cross-platform raw-byte comparison; pool replay
covers one Windows runtime. Mechanical completeness and claimed dates do not
authenticate execution, trusted time or decision authority.

NOT_RUN：工作機規則（POLICY work-machine-local），no local product execution,
tests, fixture generation, dependencies, build, lint or measurement.
