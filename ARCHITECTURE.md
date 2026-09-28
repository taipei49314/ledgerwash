# ledgerwash ARCHITECTURE (v0.1)

Layers — [SPEC.md](SPEC.md) wins on conflict:

- `epoch.py` — read-only git snapshot reader pinned to a ref. The only module that runs git.
- `models.py` — Finding, severity ladder, type-strict equality, fingerprint canonicalization.
- `adapters/ec_ledger.py` — layout constants, the closed fingerprint contract table, and the
  corpus loader. Owns ALL layout knowledge; rules never parse paths themselves.
- `rules/` — pure functions `(corpus, epoch) -> list[Finding]`, one module per rule family.
- `engine.py` — orchestration: load corpus, run rules in fixed order, sort, fingerprint,
  build the envelope, decide the verdict. Never interprets rule semantics.
- `cli.py` — `scan` / `qualify` subcommands and exit codes.
- `qualify_corpus.py` — deterministic synthetic ledger builder (the red-by-design fixture).
  `ledgerwash qualify` scans a freshly built corpus and asserts the expected finding matrix.

Invariants:

- Rules never run git; they only see the epoch reader and loaded corpus.
- Every rule ID in SPEC §4 has a planted fixture case (gate A3) — a rule that stops firing
  breaks the gate instead of passing silently.
- The adapter's contract table is the single source of truth for fingerprint anchors.
