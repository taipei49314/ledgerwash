# Independent runner evidence — design only

This is LW-002's final design deliverable. It does not add network calls to
ledgerwash, provision credentials, run a model, deploy, sign or publish a release.
Mechanical completeness cannot establish that a claimed verification happened.

## Initial source and trust boundary

Start with one existing source: GitHub's run/job/check APIs for an EC pool run,
collected independently of the scanned ledger and its artifacts. A separate
collector runs with narrowly scoped read access. ledgerwash receives only a pinned
offline evidence bundle; it never performs the collection or executes the target.

The collector must bind repository identity, full product SHA, run id/attempt,
workflow identity and EC source SHA, job/runner identity, completed conclusion,
workload declaration digest, check App id/head SHA/details URL, and artifact
digests. Keep original API responses, retrieval source, collector revision and
response hashes. Requested and actual source identity must agree. A same-name
check from another App, wrong attempt or source SHA is not interchangeable.

GitHub's service authenticates its records; EC/private receipt content still needs
to be tied to the observed job publication. A self-written log, locally coherent
hashes, or an unsigned bundle supplied by the ledger author does not become an
independent witness merely because it names a run. For offline authenticity, the
consumer must either independently fetch the records or verify an independently
trusted collector attestation whose trust root is configured outside the ledger.
Key management and attestation infrastructure require a separate scoped design.

## Consumer result and missing evidence

Keep structural findings/coverage and execution evidence separate. Suggested
states: independently_correlated, contradiction, unverified. Missing records,
expired access, reruns, unavailable artifacts, unknown App identity or collector
trust never become pass. Claims must say which exact verification step was
observed; a successful workflow conclusion alone cannot prove that a particular
procedure ran, or that the runner/collector itself was uncompromised.

## Future acceptance, not performed here

Use a real independently collected positive run and negatives with substituted
source SHA, attempt, App id, artifact digest and collector signature. Preserve an
internally consistent forged ledger that still passes the structural reader but
lacks independent correlation. The collector's output is read-only evidence,
not permission to merge, release, change task ownership or interpret authority.

Proceed only after the smaller verification-coverage contract and real EC corpus
regression are understood. This document defines an option, not a claim that
execution authenticity is implemented or validated in spec 4.
