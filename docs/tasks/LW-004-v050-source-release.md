# LW-004 — v0.5.0 source release preparation

- Owner: `LAPTOP-01AGNPJU`.
- Status: CLAIMED (2026-10-17, Asia/Taipei); execution capability review in progress.
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

NOT_RUN：工作機規則（POLICY work-machine-local），no local product/test execution,
dependency installation, uv, build, fixture generation or cross-platform probe.
Local work is limited to reading, editing, git/gh and EC governance tools.
