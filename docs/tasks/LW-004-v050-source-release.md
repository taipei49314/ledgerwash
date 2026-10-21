# LW-004 — v0.5.0 source release preparation

- Owner: `LAPTOP-01AGNPJU`.
- Status: **DONE** — source release published; final candidate/main CI and
  publication gates completed. Reconciled on 2026-10-22 from primary records.
  The [v0.5.0 Release](https://github.com/taipei49314/ledgerwash/releases/tag/v0.5.0)
  is the publication record and binds the final SHA/CI. Earlier blockers and
  failures below remain preserved.
- Starting main: `e2cec7fac5d1e11fd2b948c16fb5f64e656282c7`.
- Human instruction in Codex session `01a14509-7e7a-7501-84b0-858cc8fd298c`:
  「好，照你建議做，先修鎖檔、走 EC pool 補跨平台驗證，再補齊發版文件；確認最後候選 SHA 與 CI 都通過後，發 GitHub v0.5.0 原始碼版，PyPI 先不做。遇到新的阻擋再停下來告訴我。」

## Completed publication — 2026-10-22 reconciliation

Nelson authorized this record cleanup at 2026-10-21T16:18:07Z:
「好，照建議收尾：LW-004、LW-005 補紀錄後結案，其他已完成的更新摘要、清掉過時待辦，尚未驗收或失敗的先保留，CheckWash 不動。」

- [PR #5](https://github.com/taipei49314/ledgerwash/pull/5) merged at
  2026-10-17T15:55:36Z as `85cf8e6f99fcc576240cb6783b65b98a3341dfb1`.
- [Final candidate CI 39045076548/1](https://github.com/taipei49314/ledgerwash/actions/runs/39045076548)
  at `b1deec0f1721dfc2be61244266ce07ae82708f28` and
  [merged-main CI 39047181031/1](https://github.com/taipei49314/ledgerwash/actions/runs/39047181031)
  at `85cf8e6f` both passed all nine cells, each with 154 tests and qualify.
  The candidate and merge trees are identical, as recorded in the Release.
- [GitHub v0.5.0](https://github.com/taipei49314/ledgerwash/releases/tag/v0.5.0)
  was published at 2026-10-17T16:16:16Z and fixes the release source and retained
  EC P1–P5 evidence. EC T-553 was already completed; it is not reopened.

The original source-release scope is complete. PyPI and distribution work was
separately authorized under LW-005. Earlier blockers below are historical and
remain preserved; this reconciliation reruns nothing and changes no tag,
artifact, acceptance verdict or private SPEC6 status.

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

## Proposed unblock route (subsequently approved below)

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

## Human-approved resumption

The human resolved the venue blocker in the same session:
「好，接受這個調整：用 GitHub-hosted 九格矩陣產出固定 SHA 的結果，再由 EC pool 核對來源、逐位元比對並驗證鎖檔安裝流程。全部通過後補齊文件，確認最後候選 SHA 與 CI，再發 GitHub v0.5.0 原始碼版；PyPI 不做，遇到新的阻擋再停下告訴我。」

The [release verification preregistration](../releases/v0.5.0-PREREG.md) fixes
the comparison and installation acceptance before implementation/execution.
The operator may transport the original GitHub artifact ZIPs into immutable EC
evidence. EC independently checks public primary GitHub run/job/artifact metadata
and the service's ZIP SHA256 before consuming those bytes. No new App permissions,
host configuration or product network behavior is introduced.

NOT_RUN：工作機規則（POLICY work-machine-local），no local product/test execution,
dependency installation, uv, build, fixture generation or cross-platform probe.
Local work is limited to reading, editing, git/gh and EC governance tools.

## Registry-base interruption and explicit resumption

The first hosted producer attempt `39038424178` at `90eea1b` left three Windows
receipts incomplete at the clean-source guard. The scoped repair `77efe40`
pinned checkout line endings and retained status output; the replacement
producer run `39038979988` passed all nine cells. All failed original ZIPs and
JUnit files were retained, not overwritten.

EC #190 then passed its first integrity run, but its merge preflight refused
after evidence publications advanced the render-sensitive registry base.
T-553 was marked BLOCKED and publication stopped. The human explicitly resumed:

「好，照你建議做，恢復 T-553，更新 EC #190 分支、固定新 base／head 並重跑 CI；這輪 CI 期間不要再寫帳本。通過後完成 EC 比對與鎖檔安裝驗證、補齊文件，確認最後候選 SHA 與 CI，再發 GitHub v0.5.0 原始碼版。PyPI 不做，遇到新的阻擋再停下告訴我。」

Resume was published first. EC #190 incorporated base `fde473c` with head
`cc4ed11`, passed fresh integrity `39041471125`, then merged as `8b353f8` through
`ec_pr` with no base drift. No ledger writes occurred during that CI window
through the merge. The complete identities and immutable evidence references
are in the [release validation report](../releases/v0.5.0-VALIDATION.md).

## Verification delivered and final publication gate

EC run `39043521622`, attempt 1, at EC source `718350a` independently verified
product `77efe40ef12f2407f2d788ea2cdc6761cea31e1b`. Its private receipt
`11e0fca62bcb3d0d391f20289d380607b3cbc60c` records P1–P5 passing: all nine
producer suites/qualify, original ZIP provenance and service digests, all
40 raw outputs across five fixtures, fresh uv locked installation, 154 installed
tests, qualify and matching installed replay. Source and lock remained clean.

The subsequent product changes are documentation only: this task record,
README, SPEC clarification, the historical migration report cross-reference,
release validation and a selected saved-evidence summary. The immutable
preregistration, engine, fixtures, tests, workflows, workload and lock are
unchanged from the verified implementation. The exact comparison and final
candidate/main CI identities are recorded in the GitHub Release notes after
those gates pass. No PyPI, wheel or sdist publication is authorized here.
