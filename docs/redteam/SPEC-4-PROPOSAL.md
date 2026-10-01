# Spec 4 proposal — explicit verification coverage

Status: proposed, not the active contract. Activate in a separate spec/version
commit only after the pinned PR2 pool red-team replay. Scope is completeness of
mechanical verification inputs, not execution authenticity.

## Verdicts and compatibility

Retain all fourteen rule IDs, severities and default fail_on behavior. Add an
envelope coverage report and finding_verdict. Default verdict equals the finding
verdict. With --require-complete, verdict additionally blocks incomplete coverage.
Exit 1 means that selected gate blocked; parsing/runtime failures remain exit 2.
Coverage issues are not accusations and do not silently become high findings.
The new fields and gate require spec 4 / engine 0.4.0 / envelope version 2.

Each coverage check has path, locator, check, status (verified, unverified or
mismatch) and a stable reason. Complete means at least one task and receipt,
every loaded task can be bound to its supported operation history, all modeled
receipt and source checks verified, and no residual or unexpected adapter entry.
It does not mean artifacts are authentic, timestamps trustworthy, authority
valid, or all possible evidence paths were checked. Existing scope exclusions
remain explicit.

## Supported strict receipt profile

Ordinary ec-task-operation and ec-task-repair receipts use EC canonical record
digests: SHA256 over UTF-8 json.dumps(ensure_ascii=False, sort_keys=True,
separators=(",", ":"), allow_nan=False), with no trailing newline.

- String task_id must name a loaded task. recorded_at and request.at parse.
- expected_head and receipt birth resolve to commits.
- Nonempty unique request.sources must correspond one-to-one to nonempty
  source_fingerprints. Each contract/anchor/blob/digest is verified. Unknown
  contracts remain unverified even if best-effort bytes happen to match.
- before_record is an explicit object or null, with its matching digest or
  explicit null. after_record is an object with a matching digest and task id.
- after_record.history equals before_record.history plus this receipt's event;
  new claims start from an empty history. Sources are unique, published receipt
  paths. Ordinary operation identity, repair exception and record linkage are
  checked rather than requiring every historical snapshot to equal the present.
- Current history orders its receipts. Consecutive embedded before/after records
  match strictly; the last after_record matches the current task.

Legacy pre-store receipts and ec-task-migration are outside the initial strict
binding profile and receive explicit unverified coverage. They are not silently
exempted by self-declared schema or task time. Default findings remain compatible;
strict does not declare historical records fraudulent. Supporting archived legacy
row and migration identities can be a later independently specified extension.

## Adapter visibility

Continue loading only direct T-*.json tasks and direct *.json receipts. Record
unexpected direct files/directories as residuals instead of changing recursive
scope. Also reject duplicate JSON keys and non-finite JSON constants. Unloaded
entries are visible as unverified coverage, not treated as legitimate tasks.

## Required controls and acceptance

Preserve the 21 original cases and their frozen PR2 results. Add paired controls
for removing an originally present after_record and hiding an originally clean
OPEN task receipt. Include a complete valid claim→progress lifecycle, a true
post-receipt drift, a new unmatched anchor, Unicode canonical digests, record
digest mismatch, duplicate/missing source contracts, missing timestamps, and
unexpected filenames/subdirectories. Full consistent fabricated execution may
still pass: preserve the S4 authenticity limit.

Remote validation requires no engine errors or skips, existing frozen gates,
all positive/negative controls and deterministic raw replay. Historical epoch
b8761e95bbd92c4cd1d1917cbf70ff84e74c97f8 and current epoch
1b92c81036db6196af558b33cb455e2fdad42dce are read from EC's own private full-history
checkout, never shipped in this public product repository. Raw scans remain in
EC private receipt refs. Compare default finding identities and strict coverage
reasons and explain every change; neither real corpus is required to pass strict.
