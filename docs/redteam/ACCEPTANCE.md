# LW-002 acceptance — spec 4 verification coverage

Implementation accepted at `3be4d2a22dcbfe35c689a02657ffb48b49a01025`.
The documentation closeout is a later commit with no implementation, contract,
workload declaration or test changes. PR #3 is stacked on PR #2 and retained for
product review. This task does not merge or release the product.

## Result and consumer behavior

Engine 0.4.0 / spec 4 / envelope 2 adds per-check verification coverage and
`finding_verdict`. Default `verdict` retains the existing finding threshold.
`--require-complete` additionally blocks incomplete evidence. Existing rule IDs,
severities and findings remain stable in the frozen original suite and two pinned
real EC epochs. Mechanical completeness does not authenticate execution.

The completeness profile covers canonical task identity/history, bidirectional
receipt attachment, receipt/request identities and intent hashes, before/after
record digests and chain continuity, immutable birth blobs, source fingerprints,
and supplied closed contracts. Unknown legacy/migration shapes and malformed or
unsupported adapter inputs remain explicit gaps. Complete lifecycle, currently
claimed task and repair controls guard legitimate data.

## Remote evidence

| Evidence | Accepted source | Result |
|---|---|---|
| Baseline pool | `749911514d560e04db2b18eefeffe8ae2c311b99` | 54 tests; frozen PR2 21 cases, 17 pass / 4 block; raw replay equal |
| Implementation native CI | `3be4d2a22dcbfe35c689a02657ffb48b49a01025` | 9 jobs across Windows/macOS/Linux and Python 3.11–3.13; 92 tests each |
| Final coverage pool | `3be4d2a22dcbfe35c689a02657ffb48b49a01025` | 92 tests, zero failures/errors/skips; qualify 14 rules; 21 original cases; 36 controls; 12 real scans; raw seed replay equal |

Baseline: [EC run 36844522913](https://github.com/taipei49314/estate-consolidation/actions/runs/36844522913).
Native implementation: [run 36850853398](https://github.com/taipei49314/ledgerwash/actions/runs/36850853398).
Final pool: [EC run 36851276481](https://github.com/taipei49314/estate-consolidation/actions/runs/36851276481).

The frozen PR2 judge is `dc133028fb7405ed61c315ea3efbee26f134d015`; its archived
source and immutable red-team input hashes are in this repository. Original
default results remain 17 pass / 4 block. Strict blocks all 21 because their
verification evidence is incomplete; it does not label every attack as proven
fraud. A4C's status warning and A4B's NO_OPERATION_HISTORY block are preserved.

## Pinned real-ledger regression and limitations

The historical epoch is `b8761e95bbd92c4cd1d1917cbf70ff84e74c97f8` and the pinned
current epoch is `1b92c81036db6196af558b33cb455e2fdad42dce`. Each is scanned by
frozen PR2, candidate default and candidate strict with seeds 1 and 17: 12 scans.
This is a fixed corpus comparison, not a claim about later EC main commits.

Both pinned real ledgers retain their original finding verdict `block`. Historical
has 206 findings and current has 217; candidate default finding records
equal frozen PR2, with zero added/removed finding identities
at each epoch. Default and strict findings/coverage are equal; each judge's two
seed outputs have identical raw bytes and no engine error or timeout.

| Epoch | Verified checks | Unverified checks | Mismatch checks | Complete |
|---|---:|---:|---:|---|
| Historical | 16,132 | 693 | 324 | false |
| Pinned current | 18,714 | 693 | 324 | false |

Counts describe checks, not distinct records or confirmed offenses. Gaps retain
unsupported task/migration history profiles, modeled last snapshot/chain bindings
that cannot be established, old receipt identity/digest/contract fields and one
unorderable recorded_at claim. Comparisons downstream of unsupported histories
can report mismatch without establishing fabrication. Both epochs retain the
same single operation-ordering residual. Strict is therefore blocked; no EC
historical data was changed to remove the diagnostics.

The final pool ran on LAPTOP-SET654P2, generation `8b1bcfb4b5dc0588.1`, with EC
source `6739090f4d71fe0138090ada06df81f40c8490a9`. The approved declaration digest is
`d31cdf5a07455e3f97f04fccffcbb1352a2e006cb4774dbd64d0f175dfa0beda`. The private
receipt commit is `53f6f3087ec7ae47c7b5aee4817412ef498dd350`, ref
`sweep-receipts/36851276481/1/workload-redteam-verify`. Forty-eight selected output
blob hashes/lengths match the publication manifest, including all 12 raw real
scan stdout files and workload step stdout/stderr. Workload App 5088775 reports
success on the exact accepted product SHA.

Earlier coverage run 36847034203 failed at the serial real-ledger parent's
20-minute limit after 9 of 12 scan outputs. Its private timeout evidence is
retained; it is not final acceptance. The repair runs the two fixed epochs with
two workers, preserving every judge/seed/check and fixed record order. The parent
wait is 1350 seconds and the approved EC timeout remains 30 minutes. Final
acceptance uses a fresh complete run after the repair. Superseded runs 36845522927
and 36846541366 are cancelled and not used as acceptance.


Raw private corpus scans, check paths, findings and complete logs remain only in
EC's private receipt ref. The public product repository records aggregate
acceptance and source identities. EC integration PR #109 is merged; EC task T-484
accounts for registry, full-history checkout, dispatch and receipt verification.

The independently sourced runner evidence deliverable is design only:
`INDEPENDENT-RUNNER-DESIGN.md`. Artifact authenticity, trustworthy execution time,
authority interpretation, model accuracy, signing and a live collector are not
implemented or claimed. Native CI covers the nine listed runtimes; pool raw-byte
replay covers one EC Windows runtime, not cross-platform byte equality.

NOT_RUN：工作機規則（POLICY work-machine-local），no local product execution,
tests, fixture generation, dependency installation, build, lint or measurement.
