"""The vendored validator's own conformance.

Three things are proven here. That every declared schema compiles — which,
because the validator refuses unimplemented keywords, is the check that stops
a contract widening into territory nothing enforces. That the validator
agrees with `jsonschema` over the entire fixture corpus, so vendoring costs
no correctness; that test runs wherever the library happens to be installed
and skips where it is not, which is the whole point of not depending on it.
And that the refusals which keep it honest actually fire.
"""

import json
import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "Tool" / "src"))

from holobike import schema as vendored  # noqa: E402

CONTRACTS = ("environment", "integration", "profiles", "record",
             "revisions")


def stack_leaves():
    """Every committed integration contract: <domain>/<Integration>.json."""
    return sorted(
        path for path in (REPO_ROOT / "Stack").rglob("*.json")
        if path.name != "nonmembers.json")


def _schema_path(name):
    return REPO_ROOT / "Tool" / "src" / "holobike" / "schemas" / f"{name}.schema.json"


def _fixtures(name):
    return sorted((REPO_ROOT / "Tool" / "tests" / "fixtures" / name).iterdir())


class SchemasCompile(unittest.TestCase):
    def test_every_declared_schema_compiles(self):
        for name in CONTRACTS:
            with self.subTest(contract=name):
                vendored.load(_schema_path(name))

    def test_every_schema_has_a_corpus(self):
        for name in CONTRACTS:
            with self.subTest(contract=name):
                self.assertTrue(
                    _fixtures(name),
                    "a schema without fixtures is a contract nobody keeps")


class RefusalsFire(unittest.TestCase):
    def test_an_unimplemented_keyword_is_refused(self):
        with self.assertRaises(vendored.SchemaError) as caught:
            vendored.Schema({"type": "object", "dependentRequired": {}})
        self.assertIn("dependentRequired", str(caught.exception))

    def test_an_unimplemented_keyword_nested_in_properties_is_refused(self):
        with self.assertRaises(vendored.SchemaError):
            vendored.Schema(
                {"properties": {"x": {"unevaluatedProperties": False}}})

    def test_a_remote_reference_is_refused(self):
        with self.assertRaises(vendored.SchemaError):
            vendored.Schema({"$ref": "https://example.invalid/schema.json"})

    def test_a_reference_to_nothing_is_refused(self):
        with self.assertRaises(vendored.SchemaError):
            vendored.Schema({"$ref": "#/$defs/absent"})

    def test_an_unsupported_draft_is_refused(self):
        with self.assertRaises(vendored.SchemaError):
            vendored.Schema({"$schema": "http://json-schema.org/draft-07/schema#"})


class LiveDeclarationsValidate(unittest.TestCase):
    """The documents this repository actually carries must pass their own
    contract. A schema no live document satisfies is decoration."""

    def test_every_stack_leaf_validates(self):
        leaves = stack_leaves()
        self.assertTrue(leaves)
        contract = vendored.load(_schema_path("integration"))
        for leaf in leaves:
            with self.subTest(leaf=leaf.name):
                document = json.loads(leaf.read_text(encoding="utf-8"))
                self.assertEqual(contract.validate(document), [])

    def test_the_declared_compositions_validate(self):
        for name, relative in (
                ("revisions", "Revisions/dev.json"),
                ("profiles", "Profiles/device.json")):
            with self.subTest(document=relative):
                contract = vendored.load(_schema_path(name))
                document = json.loads(
                    (REPO_ROOT / relative).read_text(encoding="utf-8"))
                self.assertEqual(contract.validate(document), [])


class VersionConstantsAgree(unittest.TestCase):
    """Each binding still declares SCHEMA_VERSION by hand.

    The roster and the kit set are read out of the schema now, so they cannot
    drift. The version constant is the one value still stated twice, and D-03
    is the reason it matters: six schemas hold six independent constants, and
    each spends its own once. A binding a version behind its contract would
    otherwise refuse every document the schema accepts.
    """

    def test_every_binding_matches_its_schema(self):
        sys.path.insert(0, str(REPO_ROOT / "Tool" / "src"))
        from holobike import (environment, integration, profiles,
                                       record, revisions)
        bindings = {"environment": environment, "integration": integration,
                    "profiles": profiles, "record": record,
                    "revisions": revisions}
        for name, binding in bindings.items():
            with self.subTest(contract=name):
                document = json.loads(_schema_path(name).read_text("utf-8"))
                self.assertEqual(
                    document["properties"]["schema_version"]["const"],
                    binding.SCHEMA_VERSION)


class TheRosterAgreesWithItself(unittest.TestCase):
    """The roster is spelled out at seven sites across five schemas.

    Adding a member means editing all seven; a member enrolled in six is
    live in some mechanisms and invisible to others, which is a failure that
    passes every other test in this suite. This makes it fail here instead.
    """

    #: destination admits these alongside the roster; they end a chain
    #: rather than naming a member (D-19).
    RESERVED = frozenset({"device", "server"})

    def _roster(self):
        document = json.loads(_schema_path("environment").read_text("utf-8"))
        return frozenset(document["properties"]["checkouts"]["properties"])

    def _sites(self, node, roster, where="#", found=None):
        found = [] if found is None else found
        if isinstance(node, dict):
            for key, value in node.items():
                names = None
                if key == "enum" and isinstance(value, list):
                    names = frozenset(
                        v for v in value if isinstance(v, str))
                elif key == "properties" and isinstance(value, dict):
                    names = frozenset(value)
                if names is not None and roster & names:
                    found.append((f"{where}/{key}", names))
                    if key == "properties":
                        for name, sub in value.items():
                            self._sites(sub, roster,
                                        f"{where}/properties/{name}", found)
                        continue
                self._sites(value, roster, f"{where}/{key}", found)
        elif isinstance(node, list):
            for index, value in enumerate(node):
                self._sites(value, roster, f"{where}/{index}", found)
        return found

    def test_every_roster_site_names_every_member(self):
        roster = self._roster()
        self.assertEqual(len(roster), 13)
        sites = 0
        for name in CONTRACTS:
            document = json.loads(_schema_path(name).read_text("utf-8"))
            for where, names in self._sites(document, roster):
                sites += 1
                declared = names - self.RESERVED
                with self.subTest(site=f"{name}{where}"):
                    self.assertEqual(
                        declared, roster,
                        f"missing {sorted(roster - declared)}, "
                        f"unexpected {sorted(declared - roster)}")
        self.assertEqual(sites, 7, "a roster site appeared or vanished")


class NamedPathsExist(unittest.TestCase):
    """Nothing tracked may name a repository path that is not there.

    Moving files broke three things silently in this refactor: thirteen
    markdown links, the daily cadence's systemd unit, and thirteen stale
    citations across .gitignore, a schema $id, a non-member's reason and two
    READMEs. Each was a string naming a location, and no test looked at
    strings. This one does.

    PLAN.md and DECISIONS.md are exempt: a record of finished work cites the
    paths that existed when the work was done, and correcting them would make
    the record false. .gitignore is held to a weaker rule — an ignore pattern
    is a prediction about output that may not exist yet, so only the tier it
    names has to be real. That still catches the actual failure, which was a
    pattern left pointing at a directory the refactor deleted.
    """

    TIERS = ("Tool", "Stack", "Profiles", "Revisions", "Releases", "Artifacts",
             "Schemas", "Conformance", "Assembler", "Policy", "Provisioning")
    HISTORICAL = {"PLAN.md", "DECISIONS.md"}

    def test_no_tracked_file_names_a_path_that_is_gone(self):
        import re
        import subprocess
        pattern = re.compile(
            r"\b((?:" + "|".join(self.TIERS) + r")/[A-Za-z0-9_./@-]+)")
        tracked = subprocess.run(
            ["git", "ls-files"], cwd=REPO_ROOT, capture_output=True,
            text=True, check=True).stdout.split()
        missing = []
        for name in tracked:
            if name in self.HISTORICAL:
                continue
            try:
                body = (REPO_ROOT / name).read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for hit in set(pattern.findall(body)):
                target = hit.rstrip(".,;:)")
                if "*" in target or "<" in target:
                    continue
                probe = (target.split("/", 1)[0] if name == ".gitignore"
                         else target)
                if not (REPO_ROOT / probe).exists():
                    missing.append(f"{name} names {target}")
        self.assertEqual(sorted(missing), [])


class DeclaredUnitsPointAtRealThings(unittest.TestCase):
    """The cadence runs from a tracked template, installed per host.

    Renaming the launcher broke it silently: the unit kept pointing at a path
    that no longer existed, the timer fired, and the only evidence was a failed
    service nobody was watching. A declared unit that names a file which is not
    there is a broken cadence waiting for its next tick.
    """

    def test_every_unit_execstart_exists(self):
        units = sorted((REPO_ROOT / "Tool" / "timers").glob("*.service"))
        self.assertTrue(units, "the cadence must declare its units")
        for unit in units:
            for line in unit.read_text(encoding="utf-8").splitlines():
                if not line.startswith("ExecStart="):
                    continue
                with self.subTest(unit=unit.name):
                    # ExecStart=<interpreter> <script> <args...>
                    parts = line[len("ExecStart="):].split()
                    named = [p for p in parts if "/" in p and not p.startswith("-")]
                    self.assertTrue(named, f"no path in {line}")
                    for path in named:
                        self.assertTrue(
                            pathlib.Path(path).exists(),
                            f"{unit.name} names {path}, which is not there")


class AgreesWithJsonschema(unittest.TestCase):
    """Vendoring is only defensible while it costs no correctness."""

    def setUp(self):
        try:
            import jsonschema  # noqa: F401
        except ImportError:
            self.skipTest("jsonschema is not installed; nothing to compare")

    def test_the_whole_corpus_gets_the_same_verdict(self):
        import jsonschema
        compared = 0
        for name in CONTRACTS:
            document = json.loads(_schema_path(name).read_text("utf-8"))
            mine = vendored.Schema(document)
            theirs = jsonschema.Draft202012Validator(document)
            for fixture in _fixtures(name):
                try:
                    instance = json.loads(fixture.read_text("utf-8"))
                except json.JSONDecodeError:
                    continue  # strict decoding's business, not the schema's
                with self.subTest(fixture=f"{name}/{fixture.name}"):
                    self.assertEqual(
                        not mine.validate(instance),
                        theirs.is_valid(instance),
                        "the vendored validator and jsonschema disagree")
                compared += 1
        self.assertGreater(compared, 100, "the comparison must be broad")


if __name__ == "__main__":
    unittest.main()
