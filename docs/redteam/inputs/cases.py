"""ledgerwash red-team cases."""

from __future__ import annotations

import json

from harness import (SRC_BYTES, SRC_REL, commit, fp_entry, receipt, sha_of,
                     task, w)


def register(case, std_base):
    # ---------------------------------------------------------- controls
    def ctl_nohistory(repo):
        w(repo, ".gitattributes", b"* -text\n")
        w(repo, SRC_REL, SRC_BYTES)
        commit(repo, "sources")
        # one unrelated receipt establishes the era...
        w(repo, "evidence/task-operations/era.json", receipt("T-099"))
        # ...and a DONE task with zero receipts closed after it
        w(repo, "governance/tasks/T-099.json", task("T-099"))
        w(repo, "governance/tasks/T-800.json", task("T-800"))
        commit(repo, "ledger")

    case("CTL-NOHISTORY", "control", ctl_nohistory,
         "BLOCK", "DONE + zero receipts in-era must fire NO_OPERATION_HISTORY")

    def ctl_hash(repo):
        w(repo, ".gitattributes", b"* -text\n")
        w(repo, SRC_REL, SRC_BYTES)
        commit(repo, "sources")
        bad = fp_entry(digest="e" * 64)
        w(repo, "governance/tasks/T-100.json", task("T-100"))
        w(repo, "evidence/task-operations/r1.json", receipt("T-100", fps=[bad]))
        commit(repo, "ledger")

    case("CTL-HASHMISMATCH", "control", ctl_hash,
         "BLOCK", "wrong sha256 must fire FP_HASH_MISMATCH")

    # ------------------------------------------------- receipt destruction
    def a1_delete_all_receipts(repo):
        std_base()(repo)
        import shutil
        for f in (repo / "evidence/task-operations").glob("*.json"):
            f.unlink()
        commit(repo, "cleanup: drop receipts")

    case("A1-DELETE-RECEIPTS", "attack", a1_delete_all_receipts,
         "BYPASS?", "delete every receipt -> era invisible, NO_OPERATION_HISTORY inert, exit 0?")

    # ------------------------------------------- era gate on attacker time
    def a2_backdate_time(repo):
        w(repo, ".gitattributes", b"* -text\n")
        w(repo, SRC_REL, SRC_BYTES)
        commit(repo, "sources")
        w(repo, "evidence/task-operations/era.json", receipt("T-099"))
        w(repo, "governance/tasks/T-099.json", task("T-099"))
        # zero-receipt DONE task claiming a PRE-system close time
        w(repo, "governance/tasks/T-800.json", task("T-800", time="2020-01-01T00:00:00Z"))
        commit(repo, "ledger")

    case("A2-BACKDATE-TIME", "attack", a2_backdate_time,
         "BYPASS?", "zero-receipt DONE task with time before earliest receipt stays silent")

    def a3_malform_time(repo):
        a2_backdate_time(repo)
        w(repo, "governance/tasks/T-800.json", task("T-800", time="yesterday-ish"))
        commit(repo, "typo")

    case("A3-MALFORM-TIME", "attack", a3_malform_time,
         "BYPASS?", "unparseable time -> TIMESTAMP_MALFORMED warn only, era rule silent")

    # ------------------------------------------------- adapter invisibility
    def a4_subdir_receipt(repo):
        std_base()(repo)
        target = repo / "evidence/task-operations/sub"
        target.mkdir()
        for f in (repo / "evidence/task-operations").glob("*.json"):
            f.rename(target / f.name)
        commit(repo, "tidy: group receipts")

    case("A4-SUBDIR-RECEIPT", "attack", a4_subdir_receipt,
         "BYPASS?", "receipts moved one directory deeper: non-recursive list_dir, no residual")

    def a5_rename_task(repo):
        w(repo, ".gitattributes", b"* -text\n")
        w(repo, SRC_REL, SRC_BYTES)
        commit(repo, "sources")
        w(repo, "evidence/task-operations/era.json", receipt("T-099"))
        w(repo, "governance/tasks/T-099.json", task("T-099"))
        # DONE task whose filename escapes the T-*.json glob
        w(repo, "governance/tasks/DONE-800.json", task("DONE-800"))
        commit(repo, "ledger")

    case("A5-RENAME-TASK", "attack", a5_rename_task,
         "BYPASS?", "task file outside T-*.json glob: silently invisible, no residual")

    # -------------------------------------------- fingerprint verification
    def a6_strip_fps(repo):
        std_base()(repo)
        path = repo / "evidence/task-operations/r1.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        del data["source_fingerprints"]
        path.write_text(json.dumps(data, indent=2), encoding="utf-8", newline="\n")
        commit(repo, "slim receipt")

    case("A6-STRIP-FPS", "attack", a6_strip_fps,
         "BYPASS?", "source_fingerprints absent -> rule skips entry, zero findings")

    def a7_undoc_origin(repo):
        std_base()(repo)
        path = repo / "evidence/task-operations/r1.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["source_fingerprints"][0]["origin"] = "worktree-file-at-write-time"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8", newline="\n")
        commit(repo, "origin wording")

    case("A7-UNDOC-ORIGIN", "attack", a7_undoc_origin,
         "BYPASS?", "undocumented (hash_format, origin) -> warn only, digest never verified")

    def a8_ghost_anchor(repo):
        w(repo, ".gitattributes", b"* -text\n")
        w(repo, SRC_REL, SRC_BYTES)
        commit(repo, "sources")
        digest = sha_of(SRC_BYTES)
        entry = fp_entry(digest=digest, origin="expected-head-blob")
        rec = receipt("T-100", fps=[entry], expected_head="9" * 40)
        w(repo, "governance/tasks/T-100.json", task("T-100"))
        w(repo, "evidence/task-operations/r1.json", rec)
        commit(repo, "ledger")

    case("A8-GHOST-ANCHOR", "attack", a8_ghost_anchor,
         "BYPASS?", "expected_head not an object -> PIN_LOCAL_MISSING warn + unverified residual, pass")

    # ------------------------------------------------------- chain liveness
    def a9_strip_chain(repo):
        std_base()(repo)
        r1 = repo / "evidence/task-operations/r1.json"
        data1 = json.loads(r1.read_text(encoding="utf-8"))
        data1["after_record_sha256"] = "a" * 64
        r1.write_text(json.dumps(data1, indent=2), encoding="utf-8", newline="\n")
        # second receipt whose before sha DISAGREES -- but the field is omitted
        rec2 = receipt("T-100", recorded_at="2026-09-28T11:00:00Z")
        rec2.pop("before_record_sha256")
        rec2["after_record_sha256"] = "b" * 64
        w(repo, "evidence/task-operations/r2.json", rec2)
        commit(repo, "second op")

    case("A9-STRIP-CHAIN", "attack", a9_strip_chain,
         "BYPASS?", "before_record_sha256 omitted -> CHAIN_BREAK requires both sides, silent")

    # -------------------------------------------------------- drift liveness
    def a10_anchor_swamp(repo):
        std_base()(repo)
        # post-hoc weaken the task record (the thing POST_HOC_DRIFT exists for)
        w(repo, "governance/tasks/T-100.json", task("T-100", state="DONE", status="DONE", owner="agent-7", title="task T-100", evidence="see src/proof.py"))
        from harness import sha_of as _sh
        prev_after = _sh(__import__("json").dumps({"task_id": "T-100", "v": 1}))
        swamp = receipt("T-100", recorded_at="2027-01-01T00:00:00Z", before=prev_after)
        swamp["after_record"] = task("T-100", state="DONE", status="DONE", owner="agent-7", title="task T-100", evidence="see src/proof.py")
        w(repo, "evidence/task-operations/zzz-confirm.json", swamp)
        commit(repo, "confirm")

    case("A10-ANCHOR-SWAMP", "attack", a10_anchor_swamp,
         "BYPASS?", "a later vacuous receipt whose after_record matches the tampered record defuses drift")

    def a11_strip_after(repo):
        std_base()(repo)
        path = repo / "evidence/task-operations/r1.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data.pop("after_record", None)  # not present in std_base anyway
        path.write_text(json.dumps(data, indent=2), encoding="utf-8", newline="\n")
        # and tamper the record freely
        w(repo, "governance/tasks/T-100.json", task("T-100", state="DONE", status="DONE", owner="mystery", title="retitled"))
        commit(repo, "retitle")

    case("A11-NO-AFTER-RECORD", "attack", a11_strip_after,
         "BYPASS?", "anchor receipt without after_record -> POST_HOC_DRIFT silently inert")

    # ------------------------------------------------------------ vacuous
    def a12_vacuous_ledger(repo):
        w(repo, ".gitattributes", b"* -text\n")
        w(repo, SRC_REL, SRC_BYTES)
        commit(repo, "sources")
        w(repo, "governance/tasks/T-100.json", task("T-100"))
        w(repo, "governance/tasks/T-101.json", task("T-101"))
        # receipts carrying no evidence payload at all
        w(repo, "evidence/task-operations/r1.json",
          {"task_id": "T-100", "recorded_at": "2026-09-28T10:00:00Z"})
        w(repo, "evidence/task-operations/r2.json",
          {"task_id": "T-101", "recorded_at": "2026-09-28T10:30:00Z"})
        commit(repo, "ledger")

    case("A12-VACUOUS-LEDGER", "attack", a12_vacuous_ledger,
         "BYPASS?", "two-field receipts satisfy operation history; zero findings expected")

    # -------------------------------------------------- status unicode skip
    def a13_status_unicode(repo):
        std_base()(repo)
        w(repo, "governance/tasks/T-100.json",
          task("T-100", state="TODO", status="✅已完成（验收通过）"))
        commit(repo, "status wording")

    case("A13-STATUS-UNICODE", "attack", a13_status_unicode,
         "BYPASS?", "status with no ASCII head is skipped -> state TODO vs done-claim invisible")

    # ------------------------------------------------- reference grammar
    def a14_ref_grammar(repo):
        std_base()(repo)
        w(repo, "governance/tasks/T-100.json",
          task("T-100", evidence="src/proofs/t-100.csv (see also build/out.log)"))
        commit(repo, "evidence pointer")

    case("A14-REF-GRAMMAR", "attack", a14_ref_grammar,
         "BYPASS?", "references outside the 4 grammar roots are never checked for existence")


def register_more(case, std_base):
    def ctl_drift(repo):
        w(repo, ".gitattributes", b"* -text\n")
        w(repo, SRC_REL, SRC_BYTES)
        commit(repo, "sources")
        rec = receipt("T-100")
        rec["after_record"] = task("T-100")  # honest snapshot
        w(repo, "governance/tasks/T-100.json",
          task("T-100", title="RETITLED POST HOC", state="DONE"))
        w(repo, "evidence/task-operations/r1.json", rec)
        commit(repo, "ledger")

    case("CTL-DRIFT", "control", ctl_drift,
         "BLOCK", "after_record != current record must fire POST_HOC_DRIFT")

    def a15_drift_swamp_on_real_anchor(repo):
        ctl_drift(repo)
        swamp = receipt("T-100", recorded_at="2027-01-01T00:00:00Z", before="1" * 64)
        swamp["after_record"] = task("T-100", title="RETITLED POST HOC", state="DONE")
        w(repo, "evidence/task-operations/zzz.json", swamp)
        commit(repo, "confirm")

    case("A15-DRIFT-SWAMP", "attack", a15_drift_swamp_on_real_anchor,
         "BYPASS?", "same as A10 but against the working drift control")


def register_last(case, std_base):
    def a16_dangling_in_grammar(repo):
        std_base()(repo)
        w(repo, "governance/tasks/T-100.json",
          task("T-100", evidence="evidence/results/ghost-missing.csv"))
        commit(repo, "pointer")

    case("A16-DANGLING-WARN-ONLY", "attack", a16_dangling_in_grammar,
         "BYPASS?", "even an in-grammar dangling ref is warn-only under default fail_on=high")


def register_final(case, std_base):
    def a4b_partial_subdir(repo):
        w(repo, ".gitattributes", b"* -text\n")
        w(repo, SRC_REL, SRC_BYTES)
        commit(repo, "sources")
        digest = sha_of(SRC_BYTES)
        # an innocent era receipt stays at top level
        w(repo, "evidence/task-operations/era.json", receipt("T-099"))
        w(repo, "governance/tasks/T-099.json", task("T-099"))
        # the fingerprinted receipt moves one level down -> invisible, no residual
        rec = receipt("T-100", fps=[fp_entry(digest=digest)])
        w(repo, "evidence/task-operations/r1.json", rec)
        w(repo, "governance/tasks/T-100.json", task("T-100"))
        commit(repo, "ledger")
        target = repo / "evidence/task-operations/sub"
        target.mkdir()
        (repo / "evidence/task-operations/r1.json").rename(target / "r1.json")
        commit(repo, "tidy")

    case("A4B-PARTIAL-SUBDIR", "attack", a4b_partial_subdir,
         "BYPASS?", "hide one receipt in a subdir with another left visible: no residual at all")


def register_a4c(case, std_base):
    def a4c_open_task_hidden_receipts(repo):
        w(repo, ".gitattributes", b"* -text\n")
        w(repo, SRC_REL, SRC_BYTES)
        commit(repo, "sources")
        w(repo, "evidence/task-operations/era.json", receipt("T-099"))
        w(repo, "governance/tasks/T-099.json", task("T-099"))
        # an OPEN task with an honest receipt (fingerprinted, after_record honest)
        honest = receipt("T-100", fps=[fp_entry(digest=sha_of(SRC_BYTES))])
        honest["after_record"] = task("T-100", state="OPEN", title="original title")
        w(repo, "evidence/task-operations/r1.json", honest)
        w(repo, "governance/tasks/T-100.json",
          task("T-100", state="OPEN", title="original title"))
        commit(repo, "ledger")
        # hide the receipt one level down, then rewrite the record post-hoc
        target = repo / "evidence/task-operations/sub"
        target.mkdir()
        (repo / "evidence/task-operations/r1.json").rename(target / "r1.json")
        w(repo, "governance/tasks/T-100.json",
          task("T-100", state="OPEN", title="REWRITTEN scope: everything approved"))
        commit(repo, "tidy + clarify")

    case("A4C-OPEN-TASK-HIDDEN", "attack", a4c_open_task_hidden_receipts,
         "BYPASS?", "hide receipts of a non-DONE task and rewrite its record: drift has no anchor")
