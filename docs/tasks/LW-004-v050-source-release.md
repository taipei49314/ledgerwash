# LW-004 — v0.5.0 source release preparation

- Owner: `LAPTOP-01AGNPJU`.
- Status: BLOCKED (2026-10-17, Asia/Taipei): EC has no admitted macOS workload
  route for the required cross-platform comparison. Lock correction is delivered;
  verification and release have stopped under the human's stop-on-new-blocker instruction.
- Starting main: `e2cec7fac5d1e11fd2b948c16fb5f64e656282c7`.
- Human instruction in Codex session `01a14509-7e7a-7501-84b0-858cc8fd298c`:
  「好，照你建議做，先修鎖檔、走 EC pool 補跨平台驗證，再補齊發版文件；確認最後候選 SHA 與 CI 都通過後，發 GitHub v0.5.0 原始碼版，PyPI 先不做。遇到新的阻擋再停下來告訴我。」

## Authorized scope and order

1. Align the editable project version in `uv.lock` with the existing 0.5.0
   package and engine version, retaining dependency versions and hashes.
2. Establish the exact cross-platform comparison contract and verify the
   candidate through EC pool accounting. Check admitted execution capabilities
   before dispatch; existing nine-way native CI is not cross-platform byte
   comparison evidence. Preserve every failed or incomplete result.
3. Complete release documentation and disclose the existing spec 5 limits.
4. Pin the final candidate SHA, verify its applicable CI and pool evidence,
   then publish the GitHub `v0.5.0` source release. No PyPI or distribution
   package publication is included.

The human explicitly authorized the final source release after these conditions,
including the necessary scoped product PR delivery. Stop and report new blockers;
do not silently substitute another execution venue, narrow acceptance, provision
hosts or expand EC infrastructure scope.

EC only accounts for its own integration and dispatch. Product ownership and
release decisions remain in this repository. Existing completed EC tasks T-549
and T-551 are not reopened.

## Baseline evidence

PRs #2, #3 and #4 are merged. Main CI
[39009613782](https://github.com/taipei49314/ledgerwash/actions/runs/39009613782)
passed all nine OS/Python jobs, each with 128 tests and qualify. The migration
pool run and its exact tested source remain documented in
[SPEC5-MIGRATION-VALIDATION.md](../redteam/SPEC5-MIGRATION-VALIDATION.md).
Those results do not establish verification of later changes.

## Lock correction and execution blocker

Scope was published first at `5c1d728394ee999cc6108660253657a0fc19d56d`.
Commit `c3e255ec57f64f277bc579d63f41d8c53fbaa818` changes only the editable
`ledgerwash` package version from 0.4.0 to 0.5.0 in `uv.lock`. All external
dependency versions, URLs and hashes are unchanged. This is a source edit,
not a successful uv lock/install validation.

The EC routing review at source
`d1be5e0af5981f242554f2cf71fb1219ab03116f` found:

- The ordinary `pool-workload.yml` route requires self-hosted Windows X64 with
  `profile-ec-integrity` (line 52); its generation declares Python 3.12.10 and
  Windows MinGit. The current runner API lists 14 Windows listeners and no
  Linux or macOS listener.
- The separate HOST50 Linux container configuration remains
  `activation: approval_required`; its existence does not admit LedgerWash.
  There is no admitted macOS route in the current pool configuration.

Consequently, the requested Windows/macOS/Linux comparison cannot be completed
solely through the currently admitted EC pool. No cross-platform workload was
dispatched, no EC registry/profile/host was changed, and no tag/release was created.
No existing CI success is carried forward as evidence for this lock edit.

## Proposed unblock route (not yet approved or executed)

Use LedgerWash's existing GitHub-hosted Windows/macOS/Linux matrix with Python
3.11/3.12/3.13 to produce results from one pinned candidate and fixed fixture
epoch. Fix invocation and target-path representation in advance; preserve raw
stdout and `--out` bytes without post-hoc normalization, with default/strict
cases and expected exits. Retain source, runtime, run/attempt/job identities,
raw output digests and normal tests/qualify results.

EC pool would separately verify all nine expected producer identities and
source/fixture pins, compare the saved raw outputs, and validate the corrected
lock/install path. Its own new workload and evidence acquisition would be
declared and accounted for before dispatch. The report would explicitly say
GitHub-hosted producers plus EC pool verification, not all-platform EC execution.
This does not require host provisioning or PyPI publication.

Unblock condition: the human accepts this execution-venue change, or specifies
an admitted alternative capable of completing the original platform scope.
The source-release authorization remains conditional on the requested evidence
and final candidate CI; it is not used while this blocker remains.

NOT_RUN：工作機規則（POLICY work-machine-local），no local product/test execution,
dependency installation, uv, build, fixture generation or cross-platform probe.
Local work is limited to reading, editing, git/gh and EC governance tools.
