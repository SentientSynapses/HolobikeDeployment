"""Filesystem primitives shared by deployment lifecycle verbs.

This module owns path containment, artifact digests, and immutable file
publication. Domain modules decide what a file means; they do not each invent
their own interpretation of a relative path or durable write.
"""

from __future__ import annotations

import fcntl
import hashlib
import os
import secrets
import stat
from pathlib import Path, PurePosixPath


class FilesystemContractError(ValueError):
    """A path or file violates a deployment filesystem contract."""


_STABLE_FILE_FIELDS = (
    "st_dev", "st_ino", "st_mode", "st_nlink", "st_size", "st_mtime_ns",
    "st_ctime_ns",
)


def _open_regular(path, *, require_single_link):
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise FilesystemContractError(
            f"cannot open regular file safely: {path}: {error}") from error
    try:
        info = os.fstat(descriptor)
    except Exception:
        os.close(descriptor)
        raise
    if not stat.S_ISREG(info.st_mode) \
            or (require_single_link and info.st_nlink != 1):
        os.close(descriptor)
        qualifier = "single-link " if require_single_link else ""
        raise FilesystemContractError(
            f"not a {qualifier}regular file: {path}")
    return descriptor, info


def _require_stable_file(path, before, after, bytes_read):
    if bytes_read != after.st_size or any(
            getattr(before, field) != getattr(after, field)
            for field in _STABLE_FILE_FIELDS):
        raise FilesystemContractError(f"file changed while being read: {path}")


def relative_parts(value):
    """Return canonical POSIX path components or raise.

    Records are portable data, so their relative paths use POSIX spelling even
    when the Assembler runs on another host platform.
    """
    if not isinstance(value, str) or not value or "\0" in value:
        raise FilesystemContractError("must be a non-empty relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value \
            or any(part in ("", ".", "..") for part in path.parts):
        raise FilesystemContractError(
            "must be a canonical relative path without traversal")
    return path.parts


def require_filename(value):
    """Return one safe file name or raise."""
    parts = relative_parts(value)
    if len(parts) != 1:
        raise FilesystemContractError("must be a file name, not a path")
    return parts[0]


def resolve_beneath(root, relative, *, kind=None):
    """Resolve an existing relative path without permitting root escape.

    ``kind`` may be ``file`` or ``directory``. Symlinks at the final path are
    refused so a record cannot redirect an artifact or parent record after it
    has been reviewed.
    """
    parts = relative_parts(relative)
    root_path = Path(root).resolve(strict=True)
    candidate = root_path.joinpath(*parts)
    if candidate.is_symlink():
        raise FilesystemContractError(f"symlink is not allowed: {relative}")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise FilesystemContractError(
            f"path is unavailable: {relative}: {error}") from error
    if not resolved.is_relative_to(root_path):
        raise FilesystemContractError(f"path escapes its root: {relative}")
    info = resolved.stat()
    if kind == "file" and not stat.S_ISREG(info.st_mode):
        raise FilesystemContractError(f"not a regular file: {relative}")
    if kind == "directory" and not stat.S_ISDIR(info.st_mode):
        raise FilesystemContractError(f"not a directory: {relative}")
    return resolved


def resolve_direct_child(root, path, *, kind="file"):
    """Resolve ``path`` and require it to be a direct child of ``root``."""
    supplied = Path(path)
    name = require_filename(supplied.name)
    resolved = resolve_beneath(root, name, kind=kind)
    try:
        supplied_resolved = supplied.resolve(strict=True)
    except OSError as error:
        raise FilesystemContractError(f"path is unavailable: {error}") from error
    if supplied_resolved != resolved:
        raise FilesystemContractError(
            f"path must be a direct child of {Path(root)}")
    return resolved


def sha256_file(path):
    """Return a stable SHA-256 digest of one regular file."""
    descriptor, before = _open_regular(path, require_single_link=False)
    digest = hashlib.sha256()
    count = 0
    try:
        while True:
            chunk = os.read(descriptor, 1 << 16)
            if not chunk:
                break
            digest.update(chunk)
            count += len(chunk)
        after = os.fstat(descriptor)
        _require_stable_file(path, before, after, count)
    finally:
        os.close(descriptor)
    return digest.hexdigest()


def read_file_snapshot(path, *, max_bytes):
    """Return one bounded, stable, single-link regular-file snapshot."""
    descriptor, before = _open_regular(path, require_single_link=True)
    try:
        if before.st_size > max_bytes:
            raise FilesystemContractError(
                f"file exceeds {max_bytes} bytes: {path}")
        chunks = []
        remaining = max_bytes + 1
        while remaining:
            chunk = os.read(descriptor, min(1 << 16, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        if remaining == 0:
            raise FilesystemContractError(
                f"file exceeds {max_bytes} bytes: {path}")
        content = b"".join(chunks)
        after = os.fstat(descriptor)
        _require_stable_file(path, before, after, len(content))
        return content
    finally:
        os.close(descriptor)


def copy_file_snapshot(source, destination):
    """Stably copy one regular file; return its SHA-256 and byte count."""
    source_descriptor, before = _open_regular(
        source, require_single_link=False)
    destination = Path(destination)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    destination_descriptor = None
    digest = hashlib.sha256()
    count = 0
    try:
        destination_descriptor = os.open(
            destination, flags, stat.S_IMODE(before.st_mode))
        while True:
            chunk = os.read(source_descriptor, 1 << 16)
            if not chunk:
                break
            digest.update(chunk)
            count += len(chunk)
            offset = 0
            while offset < len(chunk):
                written = os.write(destination_descriptor, chunk[offset:])
                if written <= 0:
                    raise OSError("artifact copy made no progress")
                offset += written
        after = os.fstat(source_descriptor)
        _require_stable_file(source, before, after, count)
        os.fchmod(destination_descriptor, stat.S_IMODE(before.st_mode))
        os.fsync(destination_descriptor)
        os.close(destination_descriptor)
        destination_descriptor = None
        directory = os.open(
            destination.parent,
            os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
        )
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        return digest.hexdigest(), count
    except Exception:
        if destination_descriptor is not None:
            os.close(destination_descriptor)
        try:
            destination.unlink()
        except FileNotFoundError:
            pass
        raise
    finally:
        os.close(source_descriptor)


def open_private_output(path):
    """Create one new user-private binary output stream."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        return os.fdopen(descriptor, "wb")
    except Exception:
        os.close(descriptor)
        raise


def copy_file_snapshot(source, destination):
    """Stably copy one regular file; return its SHA-256 and byte count."""
    source_descriptor, before = _open_regular(
        source, require_single_link=False)
    destination = Path(destination)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    destination_descriptor = None
    digest = hashlib.sha256()
    count = 0
    try:
        destination_descriptor = os.open(
            destination, flags, stat.S_IMODE(before.st_mode))
        while True:
            chunk = os.read(source_descriptor, 1 << 16)
            if not chunk:
                break
            digest.update(chunk)
            count += len(chunk)
            offset = 0
            while offset < len(chunk):
                written = os.write(destination_descriptor, chunk[offset:])
                if written <= 0:
                    raise OSError("artifact copy made no progress")
                offset += written
        after = os.fstat(source_descriptor)
        _require_stable_file(source, before, after, count)
        os.fchmod(destination_descriptor, stat.S_IMODE(before.st_mode))
        os.fsync(destination_descriptor)
        os.close(destination_descriptor)
        destination_descriptor = None
        directory = os.open(
            destination.parent,
            os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
        )
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        return digest.hexdigest(), count
    except Exception:
        if destination_descriptor is not None:
            os.close(destination_descriptor)
        try:
            destination.unlink()
        except FileNotFoundError:
            pass
        raise
    finally:
        os.close(source_descriptor)


def publish_text(path, text):
    """Durably publish a UTF-8 file without replacing an existing record."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    directory = os.open(
        path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    temporary = f".{path.name}.{os.getpid()}.{secrets.token_hex(8)}.tmp"
    descriptor = None
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(temporary, flags, 0o644, dir_fd=directory)
        content = text.encode("utf-8")
        offset = 0
        while offset < len(content):
            written = os.write(descriptor, content[offset:])
            if written <= 0:
                raise OSError("record write made no progress")
            offset += written
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None

        # linkat is the portable no-replace publication primitive available
        # through Python: an existing immutable record makes this fail.
        os.link(
            temporary,
            path.name,
            src_dir_fd=directory,
            dst_dir_fd=directory,
            follow_symlinks=False,
        )
        os.unlink(temporary, dir_fd=directory)
        os.fsync(directory)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            os.unlink(temporary, dir_fd=directory)
        except FileNotFoundError:
            pass
        os.close(directory)


def publish_directory(staging, destination):
    """Atomically publish one prepared directory under a serialized parent."""
    staging = Path(staging)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    parent = destination.parent.resolve(strict=True)
    if staging.parent.resolve(strict=True) != parent:
        raise FilesystemContractError(
            "staging and destination directories must share a parent")
    directory = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        fcntl.flock(directory, fcntl.LOCK_EX)
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(destination)
        os.rename(
            staging.name,
            destination.name,
            src_dir_fd=directory,
            dst_dir_fd=directory,
        )
        os.fsync(directory)
    finally:
        os.close(directory)
