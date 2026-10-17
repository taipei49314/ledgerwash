# ledgerwash SPEC (spec 4)

The contract for ledgerwash v0.4. [ARCHITECTURE.md](ARCHITECTURE.md) describes layers; on
conflict this file wins. Frozen means: changes here require a spec bump, an independent
commit, and fixture/gate re-runs.

## 0. What it is / is not

ledgerwash reads a git-based agent work ledger (task records, operation receipts, handoff
summaries) at a pinned revision and flags mechanically-checkable patterns of weakened
evidence. It is an audit reader, not an enforcer: it writes nothing, enforces nothing, and
does not execute the subject repo's code.

- Local-first. Deterministic. No LLM. No network. Does not execute the subject.
- `exit 0` is not proof the ledger is honest. It means no in-scope finding was at or above
  `fail_on`. The rule set (§4) is closed; what it does not check is in §9 and is surfaced as
  residuals/observations where possible.
- A finding is a pattern match, not an accusation. Messages describe what is and is not
  verifiable; they never assert fraud.

## 1. Trust model

The scanned repo is untrusted input. The tool trusts: git content addressing, its own epoch
reader (§2), and the adapter contract table (§3). Everything else — task records, receipts,
timestamps, fingerprints, referenced paths — is a claim, verified only where a rule says so.
"Not flagged" is not "verified": each rule covers exactly its own pattern.

## 2. Analysis unit: the epoch

An epoch is (target repo, resolved ref). `scan --at <ref>` resolves the ref to a full commit
sha (the epoch pin) and reads EVERYTHING through `git cat-file` at that ref — task records,
receipts, referenced paths, fingerprint anchors. No worktree reads; the checkout state of the
target is irrelevant. Default ref is `HEAD` (then recording the epoch pin is the caller's
duty).

The epoch reader provides: file bytes at ref, directory listings at ref, batched object
existence, a per-file birth-commit map (the commit that added each receipt file — every file
in a multi-file commit is mapped), and blob-at-commit.

## 3. Ledger adapters (closed set)

v0.4 ships exactly one adapter: `ec-ledger`.

Layout (repo-relative):

- `governance/tasks/T-*.json` — task records (id = filename stem)
- `evidence/task-operations/*.json` — operation receipts
- `governance/github-snapshot.json` — observation only
- `CURRENT.md` — observation only

Reference grammar for task-record strings:
`(?:evidence|docs|governance|tools)/[A-Za-z0-9._/\-]+`.

Fingerprint contract table (closed; a `source_fingerprints` entry whose
`(hash_format, origin)` is not listed triggers `CONTRACT_UNDOCUMENTED`):

| hash_format | origin | verification anchor |
|---|---|---|
| `raw-git-blob-bytes` | `new-utf8-blob-in-containing-commit` | the receipt file's birth commit |
| `raw-git-blob-bytes` | `expected-head-blob` | the receipt's `expected_head` commit |

Semantics: `new-utf8-blob-in-containing-commit` claims the blob was created by the commit
containing the receipt (post-image). `expected-head-blob` claims the bytes are as of
`expected_head`, the head the receipt was written against — which may be the birth commit's
parent when one commit both changed the file and added the receipt (the pre-image case). An
anchor that does not resolve in the target repo is itself a pin finding (§4); the
fingerprint is then unverified, not failed.

`git-commit-bound` entries (task history) carry no digest; they are bound by publication
(the containing commit) and are out of fingerprint scope.

Records that do not fit the adapter shape (missing `task_id`, non-string `status`/`state`,
`schema_version` other than 1) are surfaced in `residuals` — they never silently vanish. An
absent or empty `governance/tasks/` or `evidence/task-operations/` is itself a residual: a
repo with no ledger must not read as a clean ledger.


## 3.1. Mechanical verification coverage (spec 4)

Coverage is separate from the fourteen findings. Each check has `path`, `locator`,
`check`, `status` (`verified`, `unverified`, `mismatch`) and a stable `reason`.
Checks sort by (path, locator, check, reason); counts cover all three statuses.
`coverage.complete` requires nonempty loaded tasks and receipts, every check
verified, and no adapter/rule residual or unparsed record. It proves only the
following supported inputs were mechanically verified, never execution honesty.

Supported task-store records have the exact keys `schema_version,id,description,
status,state,owner,time,evidence,handoff,history`. Schema is integer 1 (not bool),
id matches the filename's EC `T-\d+(?:[a-z]|-[a-z]+)?` grammar; description/status
are nonempty strings, owner/time/evidence strings, none with NUL. State is one of
TODO, CLAIMED, BLOCKED, DONE, SUPERSEDED, CANCELLED, and matches the leading status
state after removing `**`. Owner is trimmed with no newline, pipe or backtick.
Handoff is null or the exact nonempty string keys checked_at/progress/next_step/
source, with a UTC-Z time and safe relative path. History is nonempty, unique
direct receipt paths and exact operation events `{kind: operation, hash_format:
git-commit-bound, source: <path>}`. Migration/legacy shape is explicitly unverified.

Supported receipts are integer schema 2, kind ec-task-operation or ec-task-repair:

- task_id names a loaded task; recorded_at and request.at parse. Times remain
  self-declared claims. No Git commit clock or authority is trusted.
- Receipt birth and expected_head resolve to commits, request.expected.head
  equals expected_head, and receipt bytes at epoch equal bytes at birth.
- operation_id is a canonical UUID matching the filename. Ordinary request UUIDs
  match root operation_id/request_id; request_id is unique across loaded ordinary
  receipts. Intent digest matches the request with operation_id/at removed and
  expected.head/summary.checked_at removed (EC transport convention).
- request.operation is claim, progress, finish, handoff, resume, retire or repair.
  before_record must be an explicit supported object or null only for a new claim;
  its digest key must match the object or explicit null. after_record is a supported
  object with a matching digest. Digests are lowercase SHA256 of UTF-8 canonical
  JSON: ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
  no trailing newline. Nested equality is type-strict.
- after_record.history appends exactly this receipt event to before_record.history.
  Current task history orders operations; each receipt's after history equals the
  corresponding prefix, adjacent before/after records match and the last after
  equals the current task. Binding is bidirectional: every loaded receipt must be
  attached to its own task history. Never compare all historical records to current.
- Repair omits ordinary request UUID/intent requirements, must say operation=repair
  with a non-null before, and preserves id/owner/description/state/status.
- Nonempty unique safe request.sources correspond one-to-one with nonempty unique
  source_fingerprints. Every entry has a supported §3 contract and lowercase64hex
  digest matching actual blob bytes at the documented anchor. Missing/unknown
  inputs remain unverified, even when best-effort findings checks happen to pass.

Only direct T-*.json tasks and direct *.json receipts are loaded. Unexpected
direct files and subdirectories become residuals; the adapter does not recurse.
Duplicate JSON keys, non-finite values and invalid Unicode scalar strings are rejected as RECORD_UNPARSEABLE and
unverified coverage, not engine crashes. Coverage is built after the existing
rules, including residuals they add. No legacy or migration exemption can be
claimed merely by declaring an old schema or an early task time.

This profile does not reimplement EC's guard: decision authority, request guards,
policy, operation authorization/state-transition semantics, task-store index and
generated view consistency, legacy row/migration binding, execution authenticity,
trustworthy time and evidence outside the declared source set remain unverified.
Complete self-consistent fabricated execution can still pass (S4 limit).

`finding_verdict` is the unchanged fail_on threshold result. Default `verdict`
equals it. `--require-complete` additionally blocks when coverage.complete=false;
thus strict exit1 can mean incomplete inputs without a high finding. Envelope
version2 adds finding_verdict, coverage and run.require_complete. It does not
rename rules, change their severities or reinterpret default exit0 as complete.

## 4. Rule IDs (frozen)

Severity ladder: `info < warn < high < critical`. One ID = one mechanically distinct pattern.

| rule | severity | fires when |
|---|---|---|
| `DANGLING_REF` | warn | a path matching the reference grammar does not exist in the epoch tree; deduped per referenced path (locator names the referencing task ids) |
| `FP_SOURCE_MISSING` | high | a `source_fingerprints` entry's `source` does not exist at its documented anchor |
| `FP_HASH_MISMATCH` | high | sha256 of the source bytes at the documented anchor != the claimed digest; when the claimed digest matches an EOL-converted variant of the anchor bytes the message says so (deterministic diagnostic hint, severity unchanged) |
| `NO_OPERATION_HISTORY` | high | a task whose `state` is `DONE` has zero operation receipts, and its `time` parses to a moment on/after the earliest receipt `recorded_at` in the ledger (era-aware: the receipt system must demonstrably exist at close time; pre-system tasks and tasks with unparseable `time` stay silent) |
| `CONTRACT_UNDOCUMENTED` | warn | a fingerprint entry's `(hash_format, origin)` is not in the adapter table, or required fields are missing; best-effort anchors (birth, then birth^) are tried and the outcome is recorded in `message` |
| `PIN_UNROUTABLE` | warn | a 40-hex sha referenced in a task record is not an object of the target repo and is not a routable pin; unverified, not failed |
| `PIN_LOCAL_MISSING` | warn | a receipt's `expected_head` (a pin on the target repo itself) is not an object of the target repo; wording says "unverified locally", never "failed" |
| `TIMELINE_INVERSION` | high | a receipt's `recorded_at` is earlier than its `request.at` |
| `CHAIN_BREAK` | high | consecutive operations of one task disagree: previous `after_record_sha256` vs next `before_record_sha256`, both present and unequal; ops ordered by `(recorded_at, filename)` |
| `POST_HOC_DRIFT` | high | the anchor operation (max `(recorded_at, filename)`) embeds an `after_record` that is not type-strict-equal to the current task record (bool != int; coerced fields show up) |
| `TIMESTAMP_MALFORMED` | warn | a timestamp the rules depend on (`recorded_at`, `request.at`, task `time`) does not parse as ISO-8601 and carries no redaction shape; the dependent ordering/verification is skipped and this finding records the raw value |
| `TIMESTAMP_REDACTED` | info | an unparseable timestamp carrying the redaction shape — an ISO-8601 prefix with digit masking (`15:2xZ`) or an `A → B` range; unorderable by convention (the EC legacy redaction style), recorded, not treated as weakening |
| `RECORD_UNPARSEABLE` | high | a task or receipt file fails JSON parsing; that record is excluded from other rules |
| `STATUS_STATE_MISMATCH` | warn | normalized `status` head (strip `*`, whitespace-split, keep the leading ASCII `[A-Za-z0-9_-]+` run) != `state`; a status with no ASCII head is skipped |

Dedup: `PIN_*` per sha, `DANGLING_REF` per path, everything else per (file, locator).

## 5. Findings envelope

stdout (or `--out` file), UTF-8 JSON, sorted keys, `ensure_ascii=False`, one trailing
newline:

```json
{
  "ledgerwash_findings_version": 2,
  "run": {"adapter": "ec-ledger", "epoch": "<40hex>", "ledgerwash_version": "0.4.0", "ref": "<as given>", "spec_version": 4, "target": "<path>", "require_complete": false},
  "verdict": "pass | block",
  "finding_verdict": "pass | block",
  "coverage": {"version": 1, "complete": false, "counts": {}, "checks": [], "scope": "...", "limitations": []},
  "findings": [],
  "observations": [],
  "residuals": [],
  "summary": {"critical": 0, "high": 0, "info": 0, "warn": 0}
}
```

Each finding: `rule`, `severity`, `message` (stable English, no timestamps), `path`
(repo-relative, forward slashes), `locator` (task id / receipt filename / field),
optional `before` / `after` (short evidence strings), and `fingerprint`
(`rule/<path>/v1:<64hex>` — sha256 of the canonical JSON of rule, path, locator, before,
after).

Observations are structural stats that carry no verdict: self-signing counts (receipt
`request.actor` vs task `owner`, same / differ), snapshot `expires_at` as recorded (no
freshness judgment — there is no clock in this tool), cross-repo qualified pins seen,
`schema_version` distribution. Residuals are `{path, reason}` adapter-shape violations and
scope notes. Neither changes default `verdict`; both incomplete inputs and residuals block with `--require-complete`.

## 6. Exit codes

| exit | meaning |
|---|---|
| 0 | finding_verdict pass; with --require-complete, coverage.complete also true |
| 1 | selected verdict block: finding threshold or optional incomplete-coverage gate |
| 2 | engine error: git unreadable, ref unresolvable, adapter invariant broken |

A crash must not exit 1.

## 7. Determinism

- No network. No clock in the envelope. No random. No floats.
- Bytes are hashed exactly as stored in git objects; no EOL or whitespace normalization.
- Findings sorted by (rule, path, locator); envelope JSON bytes are identical across
  platforms for the same epoch (Python 3.11–3.13).

## 8. Claims policy

A pass/block statement that cannot name the judge is not reproducible. Record: ledgerwash
version (or git revision), `spec_version`, epoch pin (sha), adapter, and the exit code.
Example: `pass @ ledgerwash 0.4.0, spec 4, epoch <pinned-sha>, adapter ec-ledger, exit 0`.

## 9. Non-goals (spec 4)

- No network verification of pins (no remote fallback as of spec 4); PIN findings
  therefore never claim a pin is dead — only that it is unroutable or unverified locally.
- No freshness verdicts (needs a clock and a freshness policy).
- No self-signing verdicts (structural observation only; round 0 found design risk, not
  confirmed forgery).
- No equivalence-weakening checks (taxonomy 3) and no scope-drift checks (taxonomy 7) —
  round 0 produced no confirmed instance; still out of scope in spec 4.
- Source files are hash-verified only through `source_fingerprints`; spec 4 also verifies canonical record/intent digests and history binding (§3.1). `request.expected.sources`,
  `request.guards.policy_sources`, `LEDGER.md`, and session transcripts are out of scope
  for spec 4.

## 10. Spec changelog

- spec 1 (v0.1.0): initial contract. Twelve frozen rule IDs; `ec-ledger` adapter; epoch
  reader; fingerprint contract table with two documented combos.
- spec 2 (v0.2.0): `TIMESTAMP_REDACTED` (info) split from `TIMESTAMP_MALFORMED` — digit-masked
  and range timestamps are a redaction convention, not weakening (rule count 12 → 13).
  Timeline findings carry the task id in locator and message. Fingerprint anchors must
  resolve to commit objects; a non-commit or unresolvable anchor is a residual, never an
  FP finding. Empty tasks/receipts directories are residuals (no-ledger ≠ clean-ledger).
- spec 3 (v0.3.0): `NO_OPERATION_HISTORY` (high) added — a `DONE` task with zero operation
  receipts whose `time` is on/after the ledger's earliest receipt `recorded_at` (era-aware;
  closes the S4 receipt-less record-rewrite escape, docs/s4/REPORT.md) (rule count 13 → 14).
  `FP_HASH_MISMATCH` messages carry a deterministic diagnostic hint when the claimed digest
  matches an EOL-converted variant of the anchor bytes (severity unchanged).

- spec 4 (v0.4.0): explicit mechanical verification coverage (§3.1), optional
  --require-complete gate and envelope version2; fourteen finding IDs/default
  threshold semantics retained. Adapter visibility and strict JSON parsing expanded.
