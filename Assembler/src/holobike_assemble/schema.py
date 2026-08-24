"""JSON Schema validation, in the subset the declared contracts use.

The documents under `Schemas/` are the canonical contract (D-15). This module
is what makes that true: it loads them and enforces them, so a document shape
is defined in one place instead of being restated in Python.

Vendored rather than depended on (D-18). The surface is small and was
measured, not guessed: draft 2020-12, local `$ref` only, and the twenty
keywords below. The rule that keeps a vendored validator honest is that it
**refuses a schema using a keyword it does not implement** — silent
under-enforcement would let a contract widen without anyone deciding to widen
it. That refusal is safe because this repository owns the closed set of
schemas it validates.

Errors read `path: what is wrong`, matching the style the hand-written
validators established.
"""

from __future__ import annotations

import json
import pathlib
import re

# Keywords that constrain an instance. Anything outside this set and the
# annotations below is refused at compile time, by design.
_APPLICATORS = frozenset({
    "type", "$ref", "properties", "additionalProperties", "required",
    "minLength", "pattern", "enum", "const", "items", "minItems",
    "propertyNames", "minProperties", "maxProperties", "minimum",
    "uniqueItems", "allOf", "oneOf", "if", "then",
})

# Carry no assertion: skipped rather than refused.
_ANNOTATIONS = frozenset({
    "$schema", "$id", "$comment", "title", "description", "examples",
    "default", "deprecated", "$defs",
})

_SUPPORTED_DRAFT = "https://json-schema.org/draft/2020-12/schema"


class SchemaError(Exception):
    """The schema itself is malformed, or uses an unimplemented keyword."""


def _is_integer(value):
    # bool is a subclass of int in Python; JSON Schema does not agree.
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


_TYPE_CHECKS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": _is_integer,
    "number": _is_number,
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def _canonical(value):
    """A comparable form for uniqueItems; JSON values are not hashable."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class Schema:
    """A compiled schema. Reusable and stateless once built."""

    def __init__(self, root):
        if not isinstance(root, dict):
            raise SchemaError("a schema must be a JSON object")
        declared = root.get("$schema")
        if declared is not None and declared != _SUPPORTED_DRAFT:
            raise SchemaError(
                f"unsupported draft {declared!r}: this validator implements "
                f"{_SUPPORTED_DRAFT}")
        self._root = root
        self._audit(root, "#")

    @property
    def document(self):
        """The schema document itself, for callers that read it as data.

        The roster lives in these files; deriving it here is what keeps the
        Python side from restating it and drifting.
        """
        return self._root

    # -- compile-time refusal -------------------------------------------

    def _audit(self, node, where):
        """Walk the schema and refuse anything unimplemented."""
        if isinstance(node, bool):
            return
        if not isinstance(node, dict):
            raise SchemaError(f"{where}: a subschema must be an object")
        for keyword, value in node.items():
            if keyword in _ANNOTATIONS:
                continue
            if keyword not in _APPLICATORS:
                raise SchemaError(
                    f"{where}: unimplemented keyword {keyword!r} — implement "
                    "it or narrow the schema; it must not pass unchecked")
            if keyword == "$ref":
                self._dereference(value, where)
        for holder in ("properties", "$defs"):
            for name, sub in (node.get(holder) or {}).items():
                self._audit(sub, f"{where}/{holder}/{name}")
        for keyword in ("items", "propertyNames", "additionalProperties",
                        "if", "then"):
            sub = node.get(keyword)
            if isinstance(sub, (dict, bool)):
                self._audit(sub, f"{where}/{keyword}")
        for keyword in ("allOf", "oneOf"):
            for index, sub in enumerate(node.get(keyword) or []):
                self._audit(sub, f"{where}/{keyword}/{index}")

    def _dereference(self, pointer, where):
        if not isinstance(pointer, str) or not pointer.startswith("#/"):
            raise SchemaError(
                f"{where}: only local references are supported, got "
                f"{pointer!r}")
        target = self._root
        for token in pointer[2:].split("/"):
            token = token.replace("~1", "/").replace("~0", "~")
            if not isinstance(target, dict) or token not in target:
                raise SchemaError(f"{where}: {pointer} resolves to nothing")
            target = target[token]
        return target

    # -- validation -----------------------------------------------------

    def validate(self, instance):
        """Return a list of human-readable errors; empty means valid."""
        errors = []
        self._check(instance, self._root, [], errors)
        return errors

    def _check(self, value, node, path, errors):
        if node is True or node == {}:
            return
        if node is False:
            errors.append(f"{_where(path)}: not permitted here")
            return

        if "$ref" in node:
            self._check(value, self._dereference(node["$ref"], "#"), path,
                        errors)

        expected = node.get("type")
        if expected is not None:
            names = expected if isinstance(expected, list) else [expected]
            if not any(_TYPE_CHECKS[n](value) for n in names):
                errors.append(
                    f"{_where(path)}: must be {_article(names)}")
                return  # every further check would only restate this

        if "const" in node and value != node["const"]:
            errors.append(
                f"{_where(path)}: must be {json.dumps(node['const'])}")
        if "enum" in node and value not in node["enum"]:
            allowed = ", ".join(json.dumps(v) for v in node["enum"])
            errors.append(f"{_where(path)}: must be one of {allowed}")

        if isinstance(value, str):
            self._check_string(value, node, path, errors)
        if _is_number(value):
            minimum = node.get("minimum")
            if minimum is not None and value < minimum:
                errors.append(f"{_where(path)}: must be at least {minimum}")
        if isinstance(value, list):
            self._check_array(value, node, path, errors)
        if isinstance(value, dict):
            self._check_object(value, node, path, errors)

        for sub in node.get("allOf") or []:
            self._check(value, sub, path, errors)
        if "oneOf" in node:
            matched = sum(
                1 for sub in node["oneOf"] if not _errors_of(self, value, sub))
            if matched != 1:
                errors.append(
                    f"{_where(path)}: must match exactly one permitted shape, "
                    f"matched {matched}")
        if "if" in node and "then" in node:
            if not _errors_of(self, value, node["if"]):
                self._check(value, node["then"], path, errors)

    def _check_string(self, value, node, path, errors):
        minimum = node.get("minLength")
        if minimum is not None and len(value) < minimum:
            errors.append(
                f"{_where(path)}: must be at least {minimum} character"
                f"{'s' if minimum != 1 else ''} long")
        pattern = node.get("pattern")
        if pattern is not None and not re.search(pattern, value):
            errors.append(f"{_where(path)}: must match {pattern}")

    def _check_array(self, value, node, path, errors):
        minimum = node.get("minItems")
        if minimum is not None and len(value) < minimum:
            errors.append(
                f"{_where(path)}: must have at least {minimum} item"
                f"{'s' if minimum != 1 else ''}")
        if node.get("uniqueItems") and len(
                {_canonical(v) for v in value}) != len(value):
            errors.append(f"{_where(path)}: items must be unique")
        items = node.get("items")
        if items is not None:
            for index, item in enumerate(value):
                self._check(item, items, path + [index], errors)

    def _check_object(self, value, node, path, errors):
        for name in node.get("required") or []:
            if name not in value:
                errors.append(f"{_where(path + [name])}: is required")
        minimum = node.get("minProperties")
        if minimum is not None and len(value) < minimum:
            errors.append(
                f"{_where(path)}: must have at least {minimum} propert"
                f"{'ies' if minimum != 1 else 'y'}")
        maximum = node.get("maxProperties")
        if maximum is not None and len(value) > maximum:
            errors.append(
                f"{_where(path)}: must have at most {maximum} propert"
                f"{'ies' if maximum != 1 else 'y'}")

        names = node.get("propertyNames")
        if names is not None:
            for name in value:
                for error in _errors_of(self, name, names):
                    errors.append(f"{_where(path + [name])}: name {error}")

        declared = node.get("properties") or {}
        for name, sub in declared.items():
            if name in value:
                self._check(value[name], sub, path + [name], errors)

        extra = node.get("additionalProperties")
        if extra is not None and extra is not True:
            for name in value:
                if name in declared:
                    continue
                if extra is False:
                    errors.append(f"{_where(path + [name])}: is not permitted")
                else:
                    self._check(value[name], extra, path + [name], errors)


def _errors_of(schema, value, node):
    """Errors from applying one subschema, without recording a path."""
    collected = []
    schema._check(value, node, [], collected)
    return collected


def _where(path):
    if not path:
        return "the document"
    rendered = ""
    for step in path:
        if isinstance(step, int):
            rendered += f"[{step}]"
        elif rendered:
            rendered += f".{step}"
        else:
            rendered = str(step)
    return rendered


def _article(names):
    spelled = {"object": "an object", "array": "an array",
               "string": "a string", "integer": "an integer",
               "number": "a number", "boolean": "a boolean",
               "null": "null"}
    return " or ".join(spelled[n] for n in names)


def load(path):
    """Compile the schema document at `path`."""
    with open(path, "r", encoding="utf-8") as handle:
        return Schema(json.load(handle))


_SCHEMA_DIR = pathlib.Path(__file__).resolve().parents[3] / "Schemas"
_COMPILED = {}


def contract(name):
    """The compiled schema for a declared contract, by name.

    Compiled once per process: the schemas are immutable inputs, and every
    verb that touches a document type pays the parse otherwise.
    """
    if name not in _COMPILED:
        _COMPILED[name] = load(_SCHEMA_DIR / f"{name}.schema.json")
    return _COMPILED[name]
