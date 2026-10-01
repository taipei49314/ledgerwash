# ledgerwash ARCHITECTURE (v0.4)

Layers — [SPEC.md](SPEC.md) wins on conflict:

- `epoch.py` — read-only git snapshot reader pinned to a ref. The only module that runs git.
- `models.py` — Finding, severity ladder, type-strict equality, fingerprint canonicalization.
- `adapters/ec_ledger.py` — layout constants, the closed fingerprint contract table, and the
  corpus loader. Owns ALL layout knowledge; rules never parse paths themselves.
- `rules/` — functions `(corpus) -> list[Finding]`, one module per rule family.
- `coverage.py` — supported EC record, history, identity and source verification checks;
  runs after findings rules so their residuals also make coverage incomplete. Does not
  authenticate execution, decisions or trusted time (SPEC §3.1).
- `engine.py` — orchestration: load corpus, run rules in fixed order, sort, fingerprint,
  build the envelope, retain the finding verdict and apply the optional completeness gate.
  Never interprets rule semantics.
- `cli.py` — `scan` / `qualify` subcommands and exit codes.
- `qualify_corpus.py` — deterministic synthetic ledger builder (the red-by-design fixture).
  `ledgerwash qualify` scans a freshly built corpus and asserts the expected finding matrix.

Invariants:

- Rules never run git; they see the epoch reader and the loaded corpus. Rules may append
  verification residuals (e.g. an unresolvable fingerprint anchor); adapter-shape residuals
  are the adapter's.
- Every rule ID in SPEC §4 has a planted fixture case (gate A3) — a rule that stops firing
  breaks the gate instead of passing silently.
- The adapter's contract table is the single source of truth for fingerprint anchors.
