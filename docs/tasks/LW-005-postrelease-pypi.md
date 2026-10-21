# LW-005 — v0.5.0 archives and PyPI distribution

- Status: **DONE** — accepted archives/distributions published and public file
  hashes read back; reconciled on 2026-10-22. EC T-554 is already DONE.

Nelson authorized the bounded EC source archive verification and, conditional
on all checks succeeding, PyPI publication (2026-10-18 Asia/Taipei). EC T-554
owns workload admission and execution; T-553 remains completed.

The published tag remains `85cf8e6f99fcc576240cb6783b65b98a3341dfb1`.
The new verifier is separate from that source. It checks tag CI 39048676325
attempt 1, downloads both GitHub source formats, checks the complete tracked
path set and every Git blob, and builds distributions from those verified files.
The uv default build creates an sdist and then the wheel from that sdist.
The wheel payload and RECORD, package metadata and sdist source are checked
before a fresh non-editable installation runs all 154 original tests and qualify.
The suite's frozen PR2 controls intentionally execute their preserved old judge;
candidate imports must come from the installed wheel's site-packages.

Archive bounds: 32 MiB compressed, 64 MiB expanded including TAR metadata,
8 MiB per file, 2,000 entries. No links, special files, ambiguous/unsafe paths,
case collisions, missing/extra tracked files or byte normalization are allowed.
Completed downloads within the size bounds, generated results and available
failure records are retained in EC private receipts. Interrupted or oversized
downloads may fail before their bytes are saved.
No publisher credentials or uploads run on EC.

After acceptance, transfer the exact wheel/sdist and public manifest to GitHub
release assets. A separate manual `pypi-publish.yml` workflow on main will require
the accepted manifest SHA256, download those bytes, verify their source and
distribution digests against that manifest, then publish through PyPI Trusted
Publishing in the `pypi` environment. No rebuild or tag movement is allowed. The pending PyPI
publisher is project `ledgerwash`, owner `taipei49314`, repository `ledgerwash`,
workflow `pypi-publish.yml`, environment `pypi`. Account login, verified email
and 2FA are completed by the human; no API token is needed in chat.

The accepted manifest digest anchors the separately reviewed EC receipt. The
publication helper checks EC identity fields but does not independently query
private EC run evidence. Installation acceptance covers one EC Windows runtime;
it does not establish cross-platform wheel installation or reproducible builds.

EC registration PR #191 is merged. Pool run 39052901076 attempt 1 passed at
harness `f7a87b1d96dbf262f6007a0af809a5674546c6bf` and EC
`3744a5a385c1559a13df92408511ebf10be9996b`; the archived source is unchanged.
The [distribution acceptance report](../releases/v0.5.0-DISTRIBUTION.md) records
the 89 matching source files, installed 154-test suite and accepted file hashes.
The then-pending publisher setup, final workflow-source CI and accepted-manifest
dispatch were subsequently completed, as recorded below.

PR CI 39050726468 exposed Windows ZipInfo backslash normalization in both the
adversarial fixture writer and parser. The fixture now preserves raw member
names on every OS; the parser rejects original/normalized name mismatches,
including NUL truncation. The failed run remains evidence. Fresh hosted CI is
required before dispatch; no failure is relabeled as a pass.

Local validation: NOT_RUN：工作機規則（POLICY work-machine-local），product
tests, archive comparison, builds and installation must execute through admitted
EC pool or the authorized hosted CI workflow.

## Completed publication — 2026-10-22 reconciliation

This closes the remaining publication gate under Nelson's 2026-10-21T16:18:07Z
instruction quoted in [LW-004](LW-004-v050-source-release.md).

- [PR #6](https://github.com/taipei49314/ledgerwash/pull/6) merged at
  2026-10-17T17:32:13Z as `98ad19e665444185ae53ee62d29f4d0e3e0a63aa`.
  [Candidate CI 39053515857](https://github.com/taipei49314/ledgerwash/actions/runs/39053515857)
  and [main CI 39054192539](https://github.com/taipei49314/ledgerwash/actions/runs/39054192539)
  each passed nine cells with 176 tests, qualify and clean source.
- [Publish 39054732402/1](https://github.com/taipei49314/ledgerwash/actions/runs/39054732402)
  succeeded using the accepted manifest and main-only Trusted Publishing
  environment. It uploaded the accepted bytes without rebuilding.
- [PyPI 0.5.0 metadata](https://pypi.org/pypi/ledgerwash/0.5.0/json) was read
  back on 2026-10-22: wheel 44,492 bytes, SHA256
  `5a38efe79c38f8d4e2ea25dae231d174e597ffbc5ee2e3df4d312fdb7bc128e9`;
  sdist 243,541 bytes, SHA256
  `c555f688b229dc52fa5c4940d35442afd5f0f5696709ee6d1f8faf872e10ca83`.
  Upload times are 2026-10-17T17:40:24.274972Z and
  2026-10-17T17:40:25.463511Z respectively. These match the accepted assets
  recorded on the [Release](https://github.com/taipei49314/ledgerwash/releases/tag/v0.5.0).

Package/tag source remains `85cf8e6f99fcc576240cb6783b65b98a3341dfb1`;
publisher source is `98ad19e665444185ae53ee62d29f4d0e3e0a63aa`. The tag and
published bytes are unchanged. Installed-wheel acceptance still covers one EC
Windows runtime, not cross-platform wheel installation or reproducible builds.
The frozen package description's old "No PyPI package" sentence is historical;
the actual version/files and completed publication supersede it.

The earlier failed CI remains failed. This closure authorizes no upload,
rebuild, rerun, private SPEC6 continuation or new product acceptance.
