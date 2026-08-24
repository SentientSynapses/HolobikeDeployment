"""The development-environment mapping's binding.

Canonical contract: `schemas/environment.schema.json`, enforced by
`schema.py` and held by the fixtures under `tests/fixtures/environment`.

Validation is fail-closed — unknown keys are rejections, not tolerances, so a
misspelled integration name fails rather than silently deselecting an
integration. The schema says so with `additionalProperties: false`; this
module no longer restates it.

A host document is machine truth: where things are on *this* workstation, and
which machine it is. Product truth — what the stack composes on each OS —
lives in `Profiles/` and the Stack leaves. Conflating them would start as
platform truth and accrete machine paths until it was really a per-host file
with merge pain.

The roster is *derived* from the schema rather than declared here. It used to
be a tuple kept in agreement with the schema by a parity test; a value read
from the canonical document cannot drift from it, so the agreement is
structural instead of tested.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import document, schema

SCHEMA_VERSION = 3


def _declared_names(holder):
    return tuple(
        schema.contract("environment").document["properties"][holder]
        ["properties"])


INTEGRATIONS = _declared_names("checkouts")
TOOLCHAINS = _declared_names("toolchains")


@dataclass(frozen=True)
class EnvironmentDocument:
    """One workstation: who it is, what it runs, and what it carries."""

    host: str = ""
    os: str = ""
    checkouts: dict = field(default_factory=dict)
    toolchains: dict = field(default_factory=dict)


def _bind(root):
    return EnvironmentDocument(
        host=root["host"],
        os=root["os"],
        checkouts=dict(root.get("checkouts") or {}),
        toolchains=dict(root.get("toolchains") or {})), []


def validate_environment_text(text):
    """Validate one document; returns (EnvironmentDocument or None, errors).

    The document is returned only when the error list is empty.
    """
    root, errors = document.parse(text, schema.contract("environment"))
    if errors:
        return None, errors
    return _bind(root)


def load_environment(path):
    """Read and validate the document at path; returns (doc or None, errors)."""
    root, errors = document.read(path, schema.contract("environment"))
    if errors:
        return None, errors
    return _bind(root)


def producer(document):
    """The `run` block's identity half: which machine wrote this record.

    Every verb stamps this. A record that does not name its producer cannot
    be told apart from one made elsewhere, and the panel host exists precisely
    to produce the records only it can.
    """
    return {"host": document.host, "os": document.os}
