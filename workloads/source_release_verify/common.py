"""Bounded archive parsing and exact Git-blob checks; no extraction side effects."""
from __future__ import annotations

import hashlib
import gzip
import io
from pathlib import PurePosixPath
import stat
import tarfile
import zipfile

MAX_ARCHIVE = 32 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024
MAX_FILE = 8 * 1024 * 1024
MAX_ENTRIES = 2000


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe_name(name):
    require(isinstance(name, str) and name and len(name) <= 500, "archive name bound")
    require(not any(ord(c) < 32 for c in name) and "\\" not in name
            and ":" not in name and not name.startswith("/"), "unsafe archive path")
    parts = name.rstrip("/").split("/")
    require(all(p and p not in (".", "..") and not p.endswith((".", " ")) for p in parts),
            "unsafe archive component")
    require(all(p.split(".")[0].upper() not in
                {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(1, 10)],
                 *[f"LPT{i}" for i in range(1, 10)]} for p in parts), "reserved path")
    return "/".join(parts)


def read_archive(raw, kind, root=None):
    """Return file bytes only, rejecting ambiguity before anything is written."""
    require(len(raw) <= MAX_ARCHIVE, "compressed archive bound")
    files, seen, directories, total = {}, set(), set(), 0

    def add(name, directory, size, reader):
        nonlocal total
        path = safe_name(name)
        key = path.casefold()
        require(key not in seen, "duplicate/case-colliding archive path")
        seen.add(key)
        require(len(seen) <= MAX_ENTRIES, "archive entry bound")
        if root:
            require(path == root or path.startswith(root + "/"), "unexpected archive root")
            path = path[len(root):].lstrip("/")
        if directory:
            require(size == 0, "directory contains data")
            if path:
                directories.add(path)
            return
        require(path and 0 <= size <= MAX_FILE, "file size bound")
        total += size
        require(total <= MAX_TOTAL, "expanded archive bound")
        data = reader(size + 1)
        require(len(data) == size, "archive length mismatch")
        files[path] = data

    if kind == "zip":
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            require(len(archive.infolist()) <= MAX_ENTRIES, "archive entry bound")
            for entry in archive.infolist():
                # ZipInfo normalizes backslashes on Windows and truncates NULs.
                # Reject the original name before accepting its normalized alias.
                require(entry.orig_filename == entry.filename, "ZIP normalized unsafe path")
                mode = entry.external_attr >> 16
                require(stat.S_IFMT(mode) in (0, stat.S_IFDIR, stat.S_IFREG), "ZIP special file")
                require(not entry.flag_bits & 1, "encrypted ZIP")
                with archive.open(entry) as handle:
                    add(entry.filename, entry.is_dir(), entry.file_size, handle.read)
    elif kind == "tar.gz":
        # Bound decompression including PAX metadata and padding before tar parsing.
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as compressed:
            expanded = compressed.read(MAX_TOTAL + 1)
        require(len(expanded) <= MAX_TOTAL, "expanded TAR bound")
        with tarfile.open(fileobj=io.BytesIO(expanded), mode="r:") as archive:
            for entry in archive:
                require(entry.isdir() or entry.isfile(), "TAR special file/link")
                handle = archive.extractfile(entry) if entry.isfile() else None
                add(entry.name, entry.isdir(), entry.size, handle.read if handle else None)
    else:
        raise ValueError("unsupported archive format")
    require(files, "empty archive")
    require(all(any(p.startswith(d + "/") for p in files) for d in directories),
            "unreferenced archive directory")
    folded_files = {p.casefold() for p in files}
    for path in files:
        require(not any(str(parent).casefold() in folded_files for parent in PurePosixPath(path).parents
                        if str(parent) != "."), "file/directory collision")
    return files


def compare_git(files, expected):
    require(files.keys() == expected.keys(), "archive tracked path set mismatch")
    manifest = {}
    for path, data in files.items():
        mode, blob = expected[path]
        require(mode == "100644", "fixed workload supports only regular non-executable files")
        actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        require(actual == blob, "Git blob mismatch: " + path)
        manifest[path] = {"git_blob": blob, "size": len(data), "sha256": sha(data)}
    return manifest
