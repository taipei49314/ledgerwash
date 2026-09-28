# ledgerwash

**Flags weakened evidence in agent work ledgers — handoff receipts, task records, handoff
summaries — at a pinned git revision.** 標出 agent 工作帳本裡被弱化的證據。

checkwash guards the diff; ledgerwash guards the ledger. Local-first. Deterministic. No LLM.
No network. Read-only: does not execute the subject, does not enforce anything.

This is an incubation build (S3 prototype, agent-rd backlog; see
`../../PROPOSAL.md` and `../../round0/FINDINGS.md`). No Release, no PyPI, no 1.0 claim. Read
[SPEC.md](SPEC.md) (contract) and [ARCHITECTURE.md](ARCHITECTURE.md) (layers; SPEC wins on
conflict). Frozen acceptance is `tests/test_gates.py`.

## Try it

Python 3.11+, git, [uv](https://docs.astral.sh/uv/). From this directory:

```powershell
uv sync --extra dev
uv run ledgerwash --version
uv run ledgerwash qualify
uv run python -m pytest
uv run ledgerwash scan <repo> --at <pinned-sha> --out findings.json
```

`scan` with no `--at` pins to the target's `HEAD`; recording that sha is then the caller's
duty. Exit 0 is not proof the ledger is honest; it means no in-scope finding was at or above
`fail_on` (default `high`).

## Consumer recipe: judging a ledger

Pin the commit first (write the sha down), then one invocation:

```powershell
uv run ledgerwash scan <repo> --at <pinned-sha>
```

Record the judge's identity with the verdict: `pass @ ledgerwash 0.1.0, spec 1, epoch
b8761e95…, adapter ec-ledger, exit 0`. A pass that cannot name the judge is not
reproducible (SPEC §8).

## Round 0 pedigree

The thirteen rules formalize the round-0 human triage of the EC corpus (91 real instances,
4 categories, 205 raw signals → ~98% naive false-positive rate): era-aware fingerprint
anchors (birth / expected_head instead of current HEAD), a closed fingerprint contract
table, routed pins that never claim death from local unreachability, timestamp quality as a
first-class check instead of a silent skip, and the EC legacy redaction convention
(`TIMESTAMP_REDACTED`) kept apart from genuinely malformed timestamps.
