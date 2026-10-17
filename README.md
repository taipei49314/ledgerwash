# ledgerwash

**Flags weakened evidence in agent work ledgers — handoff receipts, task records, handoff
summaries — at a pinned git revision.** 標出 agent 工作帳本裡被弱化的證據。

checkwash guards the diff; ledgerwash guards the ledger. Local-first. Deterministic. No LLM.
No network. Read-only: does not execute the subject, does not enforce anything.

This repository has a local **v0.3 engine**. There is no Release, no PyPI package, and no
1.0 claim. Read [SPEC.md](SPEC.md) (contract) and [ARCHITECTURE.md](ARCHITECTURE.md)
(layers; SPEC wins on conflict). Frozen acceptance is `tests/test_gates.py` (A1–A9).

## Try it

Python 3.11+, git, [uv](https://docs.astral.sh/uv/). From this checkout:

```powershell
uv sync --extra dev
uv run ledgerwash --version
uv run ledgerwash qualify
uv run python -m pytest
uv run ledgerwash scan <repo> --at <pinned-sha> --out findings.json
```

`scan` with no `--at` pins to the target's `HEAD`; recording that sha is then the caller's
duty. Exit 0 is not proof the ledger is honest; it means no in-scope finding was at or above
`fail_on` (default `high`). A repo with no ledger at all is reported through residuals —
no-ledger is not a clean-ledger.

## Consumer recipe: judging a ledger

Pin the commit first (write the sha down), then one invocation:

```powershell
uv run ledgerwash scan <repo> --at <pinned-sha>
```

Record the judge's identity with the verdict: `block @ ledgerwash 0.3.0, spec 3, epoch
b8761e95…, adapter ec-ledger, exit 1`. A pass that cannot name the judge is not
reproducible (SPEC §8).

The S4 sample also demonstrates that a completely fabricated artifact can pass
when its receipts, hashes and timestamps agree internally. Record independent
execution evidence (for example, the CI run and exact source SHA) alongside a
ledgerwash verdict when claiming that verification actually happened. A spec 3
pass alone does not establish artifact authenticity; see [S4 report](docs/s4/REPORT-2.md).

## Writing receipts that verify

`raw-git-blob-bytes` fingerprints are sha256 over the bytes git stores — the blob — never
the worktree file. In a repo with `core.autocrlf=true`, hashing the worktree file bakes
CRLF into the digest while the blob stores LF, and every receipt becomes unverifiable at
its anchor (the S4 round reproduced this live; the tool now hints at it):

```python
import hashlib, subprocess
blob = subprocess.run(["git", "cat-file", "blob", f"{commit}:{path}"],
                      capture_output=True).stdout
digest = hashlib.sha256(blob).hexdigest()
```

At write time the receipt's birth commit does not exist yet, so hash the exact bytes you
are about to commit, and pin line endings (`* -text` in `.gitattributes`) to remove the
ambiguity entirely.

## Round-0 pedigree

Thirteen of the fourteen rules formalize a preregistered human triage of a real 462-row
agent task ledger (91 real weakening instances, 4 categories, 205 raw signals → ~98% naive
false-positive rate): era-aware fingerprint anchors (birth / expected_head instead of
current HEAD), a closed fingerprint contract table, routed pins that never claim death from
local unreachability, timestamp quality as a first-class check instead of a silent skip,
and the legacy digit-masked redaction convention (`TIMESTAMP_REDACTED`) kept apart from
genuinely malformed timestamps. On that same corpus, excluding the timestamp-quality classes
(112 `TIMESTAMP_MALFORMED` in spec 1; 107 `TIMESTAMP_REDACTED` + 5 prose `TIMESTAMP_MALFORMED`
in spec 2; 203 findings in total either way), the spec 1 and spec 2 outputs reproduce the
human triage exactly: 91 findings ([docs/recon/RECON.md](docs/recon/RECON.md)). The
fourteenth rule, `NO_OPERATION_HISTORY` (spec 3), comes from the S4 escape sample
([docs/s4/REPORT.md](docs/s4/REPORT.md)), not from round 0; on the same corpus it flags
three more DONE tasks, closed after the receipt system existed yet with zero receipts, that
the human triage missed (T-291, T-293, T-297; [docs/s4/REPORT-2.md](docs/s4/REPORT-2.md)),
so the same subset is 91 + 3 = 94 under spec 3.

## Provenance

Incubated 2026-09-27→28 inside
[taipei49314/agent-rd](https://github.com/taipei49314/agent-rd) — round-0 corpus
validation (PASS: 4 categories, 91 instances), S3 prototype, adversarial review pass — and
graduated to this independent repository on 2026-09-28 by human instruction. The
preregistered acceptance reconciliation ships with the repository in
[docs/recon/](docs/recon/) (PREREG, RECON report, raw finding envelopes); the incubation
record (proposal, round-0 triage) remains in agent-rd.
