"""Archive rejection controls, executed in hosted CI/EC only."""
import gzip
import hashlib
import io
import stat
import tarfile
import zipfile

import pytest

from workloads.source_release_verify import common


def archive(kind, entries):
    output = io.BytesIO()
    if kind == "zip":
        with zipfile.ZipFile(output, "w") as z:
            for path, data in entries:
                # Preserve adversarial raw names on Windows too; ZipInfo's
                # constructor normally rewrites backslashes before writing.
                entry = zipfile.ZipInfo("placeholder")
                entry.filename = entry.orig_filename = path
                z.writestr(entry, data)
    else:
        with tarfile.open(fileobj=output, mode="w:gz") as t:
            for path, data in entries:
                item = tarfile.TarInfo(path)
                item.size = len(data)
                t.addfile(item, io.BytesIO(data))
    return output.getvalue()


@pytest.mark.parametrize("kind", ["zip", "tar.gz"])
def test_original_bytes_match_git_but_newline_rewrite_fails(kind):
    raw = b"original\r\n"
    blob = hashlib.sha1(b"blob 10\0" + raw).hexdigest()
    files = common.read_archive(archive(kind, [("root/file", raw)]), kind, "root")
    assert common.compare_git(files, {"file": ("100644", blob)})["file"]["size"] == 10
    with pytest.raises(ValueError, match="blob mismatch"):
        common.compare_git({"file": b"original\n"}, {"file": ("100644", blob)})
    with pytest.raises(ValueError, match="path set"):
        common.compare_git(files, {})


@pytest.mark.parametrize("kind", ["zip", "tar.gz"])
@pytest.mark.parametrize("name", ["root/../escape", "/root/file", "root\\file", "root/C:escape", "root/CON", "other/file"])
def test_unsafe_or_wrong_root_is_refused(kind, name):
    with pytest.raises(ValueError):
        common.read_archive(archive(kind, [(name, b"x")]), kind, "root")


@pytest.mark.parametrize("kind", ["zip", "tar.gz"])
def test_case_collision_and_file_directory_collision_refused(kind):
    for entries in ([('root/A', b'a'), ('root/a', b'b')],
                    [('root/a', b'a'), ('root/a/b', b'b')],
                    [('root/A', b'a'), ('root/a/b', b'b')]):
        with pytest.raises(ValueError):
            common.read_archive(archive(kind, entries), kind, "root")


def test_links_are_never_extracted():
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as z:
        entry = zipfile.ZipInfo("root/link")
        entry.create_system = 3
        entry.external_attr = (stat.S_IFLNK | 0o777) << 16
        z.writestr(entry, "target")
    with pytest.raises(ValueError, match="special"):
        common.read_archive(output.getvalue(), "zip", "root")
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as t:
        entry = tarfile.TarInfo("root/link")
        entry.type = tarfile.SYMTYPE
        entry.linkname = "target"
        t.addfile(entry)
    with pytest.raises(ValueError, match="special"):
        common.read_archive(output.getvalue(), "tar.gz", "root")


def test_zip_nul_name_is_not_accepted_as_a_safe_alias():
    with pytest.raises(ValueError, match="normalized unsafe path"):
        common.read_archive(archive("zip", [("root/file\0hidden", b"x")]), "zip", "root")


def test_tar_metadata_decompression_is_bounded(monkeypatch):
    monkeypatch.setattr(common, "MAX_TOTAL", 1024)
    with pytest.raises(ValueError, match="expanded TAR"):
        common.read_archive(gzip.compress(b"\0" * 2048), "tar.gz", "root")


@pytest.mark.parametrize("kind", ["zip", "tar.gz"])
def test_member_size_is_bounded(kind, monkeypatch):
    monkeypatch.setattr(common, "MAX_FILE", 2)
    with pytest.raises(ValueError, match="file size"):
        common.read_archive(archive(kind, [("root/file", b"abc")]), kind, "root")


def test_metadata_rejects_base_dependencies_disguised_as_extras():
    from workloads.source_release_verify.run import metadata
    header = (b'Name: ledgerwash\nVersion: 0.5.0\nRequires-Python: >=3.11\n'
              b'License-Expression: Apache-2.0\nLicense-File: LICENSE\n'
              b'Description-Content-Type: text/markdown\nProvides-Extra: dev\n')
    assert metadata(header + b'Requires-Dist: pytest>=8; extra == "dev"\n\nreadme')["Version"] == "0.5.0"
    with pytest.raises(ValueError, match="dependency"):
        metadata(header + b'Requires-Dist: evil; extra == "dev" or python_version >= "3"\n\nreadme')
