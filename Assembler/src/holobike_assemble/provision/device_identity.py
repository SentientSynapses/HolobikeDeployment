"""Bounded offline provisioning for public HoloBike device identity."""

from __future__ import annotations

import argparse
import datetime
import errno
import fcntl
import json
import os
import re
import secrets
import stat
import sys
from pathlib import Path


SCHEMA_VERSION = 1
MAX_DOCUMENT_BYTES = 64 * 1024
MAX_PROVISIONING_REVISION = (1 << 63) - 1
TARGET_DIRECTORY = ("etc", "holobike")
TARGET_NAME = "device-identity.json"
FIELDS = (
    "schema_version",
    "device_id",
    "product_model",
    "provisioning_revision",
    "provisioned_at_utc",
    "provenance",
)
TOKEN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
UTC_TIMESTAMP = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")


class IdentityProvisioningError(ValueError):
    """A refused identity input or filesystem target."""


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise IdentityProvisioningError(
                f"duplicate identity field: {key!r}")
        result[key] = value
    return result


def _is_utc_timestamp(value):
    if not isinstance(value, str) or not UTC_TIMESTAMP.fullmatch(value):
        return False
    try:
        parsed = datetime.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return (
        parsed.tzinfo is not None
        and parsed.utcoffset() == datetime.timedelta(0)
    )


def validate_identity(document):
    """Return a canonical field-ordered identity or raise."""
    if not isinstance(document, dict):
        raise IdentityProvisioningError("device identity must be a JSON object")
    actual = set(document)
    expected = set(FIELDS)
    if actual != expected:
        missing = sorted(expected.difference(actual))
        unknown = sorted(actual.difference(expected))
        detail = []
        if missing:
            detail.append("missing: " + ", ".join(missing))
        if unknown:
            detail.append("unknown: " + ", ".join(unknown))
        raise IdentityProvisioningError(
            "device identity fields are invalid (" + "; ".join(detail) + ")")
    if (
        isinstance(document["schema_version"], bool)
        or document["schema_version"] != SCHEMA_VERSION
    ):
        raise IdentityProvisioningError(
            f"schema_version must be the integer {SCHEMA_VERSION}")
    for field in ("device_id", "product_model", "provenance"):
        value = document[field]
        if not isinstance(value, str) or not TOKEN.fullmatch(value):
            raise IdentityProvisioningError(
                f"{field} must match {TOKEN.pattern}")
    revision = document["provisioning_revision"]
    if (
        isinstance(revision, bool)
        or not isinstance(revision, int)
        or revision < 1
        or revision > MAX_PROVISIONING_REVISION
    ):
        raise IdentityProvisioningError(
            "provisioning_revision must be an integer in the signed 64-bit range")
    if not _is_utc_timestamp(document["provisioned_at_utc"]):
        raise IdentityProvisioningError(
            "provisioned_at_utc must be an ISO-8601 UTC timestamp ending in Z")
    return {field: document[field] for field in FIELDS}


def load_identity(path):
    path = Path(path)
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = None
    try:
        descriptor = os.open(path, flags)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise IdentityProvisioningError(
                "identity input must be a single-link regular file")
        if before.st_size > MAX_DOCUMENT_BYTES:
            raise IdentityProvisioningError(
                f"identity input exceeds {MAX_DOCUMENT_BYTES} bytes")
        chunks = []
        remaining = MAX_DOCUMENT_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(4096, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        if remaining == 0:
            raise IdentityProvisioningError(
                f"identity input exceeds {MAX_DOCUMENT_BYTES} bytes")
        after = os.fstat(descriptor)
        stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns",
                         "st_ctime_ns", "st_nlink")
        if any(getattr(before, field) != getattr(after, field)
               for field in stable_fields) \
                or len(b"".join(chunks)) != after.st_size:
            raise IdentityProvisioningError(
                "identity input changed while being read")
        document = json.loads(
            b"".join(chunks).decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys)
    except IdentityProvisioningError:
        raise
    except (OSError, UnicodeError, ValueError) as error:
        raise IdentityProvisioningError(
            f"unable to load identity input: {error}") from error
    finally:
        if descriptor is not None:
            os.close(descriptor)
    return validate_identity(document)


def _canonical_bytes(document):
    return (
        json.dumps(validate_identity(document), indent=2, ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def _open_offline_root(root):
    root = Path(root)
    if not root.is_absolute():
        raise IdentityProvisioningError("provisioning root must be absolute")
    parts = root.parts
    if root == Path("/") or any(part in {"", ".", ".."} for part in parts[1:]):
        raise IdentityProvisioningError(
            "the live root and non-normalized roots are not provisioning targets")

    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open("/", flags)
    live_root = os.fstat(descriptor)
    try:
        for component in parts[1:]:
            next_descriptor = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        target_root = os.fstat(descriptor)
        if (target_root.st_dev, target_root.st_ino) == \
                (live_root.st_dev, live_root.st_ino):
            raise IdentityProvisioningError(
                "the live root is not a provisioning target")
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


def _open_target_component(parent_descriptor, name, create_missing):
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    created = False
    try:
        try:
            descriptor = os.open(name, flags, dir_fd=parent_descriptor)
        except FileNotFoundError:
            if not create_missing:
                raise IdentityProvisioningError(
                    f"identity target directory {name!r} is absent")
            try:
                os.mkdir(name, 0o755, dir_fd=parent_descriptor)
                created = True
            except FileExistsError:
                pass
            descriptor = os.open(name, flags, dir_fd=parent_descriptor)
            if created and os.geteuid() == 0:
                os.fchown(descriptor, 0, 0)
            if created:
                os.fsync(parent_descriptor)
    except OSError as error:
        if error.errno in (errno.ELOOP, errno.ENOTDIR):
            raise IdentityProvisioningError(
                f"identity target directory {name!r} is not a trusted directory"
            ) from error
        raise
    try:
        info = os.fstat(descriptor)
        if info.st_mode & 0o022:
            raise IdentityProvisioningError(
                f"identity target directory {name!r} is group/other writable")
        if os.geteuid() == 0 and (info.st_uid != 0 or info.st_gid != 0):
            raise IdentityProvisioningError(
                f"identity target directory {name!r} is not root-owned")
    except Exception:
        os.close(descriptor)
        raise
    return descriptor


def _read_target(directory_descriptor):
    try:
        info = os.stat(
            TARGET_NAME,
            dir_fd=directory_descriptor,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return None, None
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise IdentityProvisioningError(
            "existing device identity must be a single-link regular file")
    if info.st_size > MAX_DOCUMENT_BYTES:
        raise IdentityProvisioningError("existing device identity is oversized")
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(TARGET_NAME, flags, dir_fd=directory_descriptor)
    except OSError as error:
        raise IdentityProvisioningError(
            "existing device identity cannot be opened safely") from error
    try:
        opened_info = os.fstat(descriptor)
        if (
            opened_info.st_dev != info.st_dev
            or opened_info.st_ino != info.st_ino
            or not stat.S_ISREG(opened_info.st_mode)
            or opened_info.st_nlink != 1
        ):
            raise IdentityProvisioningError(
                "existing device identity changed while being opened")
        chunks = []
        remaining = MAX_DOCUMENT_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(4096, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        if remaining == 0:
            raise IdentityProvisioningError(
                "existing device identity exceeds its size limit")
        content = b"".join(chunks)
        final_info = os.fstat(descriptor)
        stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns",
                         "st_ctime_ns", "st_nlink", "st_mode", "st_uid",
                         "st_gid")
        if any(getattr(opened_info, field) != getattr(final_info, field)
               for field in stable_fields) or len(content) != final_info.st_size:
            raise IdentityProvisioningError(
                "existing device identity changed while being read")
        document = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except IdentityProvisioningError:
        raise
    except (UnicodeError, ValueError) as error:
        raise IdentityProvisioningError(
            "existing device identity is malformed") from error
    finally:
        os.close(descriptor)
    return validate_identity(document), final_info


def _open_target_directory(root, create_missing):
    descriptor = _open_offline_root(root)
    try:
        for component in TARGET_DIRECTORY:
            next_descriptor = _open_target_component(
                descriptor, component, create_missing)
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


def install_identity(root, document):
    """Atomically install one validated identity beneath an offline root."""
    document = validate_identity(document)
    directory_descriptor = _open_target_directory(root, create_missing=True)
    temporary_name = (
        f".{TARGET_NAME}.{os.getpid()}.{secrets.token_hex(8)}.tmp")
    try:
        fcntl.flock(directory_descriptor, fcntl.LOCK_EX)
        current, _ = _read_target(directory_descriptor)
        if (
            current is not None
            and document["provisioning_revision"]
            <= current["provisioning_revision"]
        ):
            raise IdentityProvisioningError(
                "provisioning_revision must increase when replacing identity")

        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(
            temporary_name, flags, 0o644, dir_fd=directory_descriptor)
        try:
            content = _canonical_bytes(document)
            offset = 0
            while offset < len(content):
                written = os.write(descriptor, content[offset:])
                if written <= 0:
                    raise OSError("device identity write made no progress")
                offset += written
            os.fchmod(descriptor, 0o644)
            if os.geteuid() == 0:
                os.fchown(descriptor, 0, 0)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

        os.replace(
            temporary_name,
            TARGET_NAME,
            src_dir_fd=directory_descriptor,
            dst_dir_fd=directory_descriptor,
        )
        os.fsync(directory_descriptor)
        installed, info = _read_target(directory_descriptor)
        if installed != document or stat.S_IMODE(info.st_mode) != 0o644:
            raise IdentityProvisioningError(
                "installed device identity failed post-write verification")
        if os.geteuid() == 0 and (info.st_uid != 0 or info.st_gid != 0):
            raise IdentityProvisioningError(
                "installed device identity is not root-owned")
        return installed
    finally:
        try:
            os.unlink(temporary_name, dir_fd=directory_descriptor)
        except FileNotFoundError:
            pass
        os.close(directory_descriptor)


def verify_identity(root):
    """Validate the fixed identity target beneath an offline root."""
    directory_descriptor = _open_target_directory(root, create_missing=False)
    try:
        fcntl.flock(directory_descriptor, fcntl.LOCK_SH)
        document, info = _read_target(directory_descriptor)
        if document is None:
            raise IdentityProvisioningError("device identity is absent")
        if stat.S_IMODE(info.st_mode) != 0o644:
            raise IdentityProvisioningError(
                "device identity mode must be 0644")
        if os.geteuid() == 0 and (info.st_uid != 0 or info.st_gid != 0):
            raise IdentityProvisioningError(
                "device identity must be root-owned")
        return document
    finally:
        os.close(directory_descriptor)


def _parser():
    parser = argparse.ArgumentParser(
        description="Provision public HoloBike identity into an offline root.")
    commands = parser.add_subparsers(dest="command", required=True)
    install = commands.add_parser("install")
    install.add_argument("--root", type=Path, required=True)
    install.add_argument("--input", type=Path, required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("--root", type=Path, required=True)
    return parser


def main(argv=None):
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "install":
            document = install_identity(
                arguments.root, load_identity(arguments.input))
            print(
                "installed HoloBike device identity revision "
                f"{document['provisioning_revision']}")
        else:
            document = verify_identity(arguments.root)
            print(
                "verified HoloBike device identity revision "
                f"{document['provisioning_revision']}")
        return 0
    except (IdentityProvisioningError, OSError) as error:
        print(f"device identity refused: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
