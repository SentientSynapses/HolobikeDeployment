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
sys.path.insert(0, str(REPO_ROOT / "Assembler" / "src"))

from holobike_assemble import schema as vendored  # noqa: E402

CONTRACTS = ("environment", "integration", "policy", "profiles", "record",
             "revisions")


def _schema_path(name):
    return REPO_ROOT / "Schemas" / f"{name}.schema.json"


def _fixtures(name):
    return sorted((REPO_ROOT / "Conformance" / name).iterdir())


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
        leaves = sorted((REPO_ROOT / "Stack").rglob("integration.json"))
        self.assertTrue(leaves)
        contract = vendored.load(_schema_path("integration"))
        for leaf in leaves:
            with self.subTest(leaf=leaf.name):
                document = json.loads(leaf.read_text(encoding="utf-8"))
                self.assertEqual(contract.validate(document), [])

    def test_the_declared_compositions_validate(self):
        for name, relative in (
                ("revisions", "Revisions/dev.json"),
                ("profiles", "Profiles/services.json"),
                ("policy", "Policy/parity.json")):
            with self.subTest(document=relative):
                contract = vendored.load(_schema_path(name))
                document = json.loads(
                    (REPO_ROOT / relative).read_text(encoding="utf-8"))
                self.assertEqual(contract.validate(document), [])


class TheRosterAgreesWithItself(unittest.TestCase):
    """The roster is spelled out at twelve sites across six schemas.

    Adding a member means editing all twelve; a member enrolled in eleven is
    live in some mechanisms and invisible to others, which is a failure that
    passes every other test in this suite. This makes it fail here instead.
    """

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
                with self.subTest(site=f"{name}{where}"):
                    self.assertEqual(
                        names, roster,
                        f"missing {sorted(roster - names)}, "
                        f"unexpected {sorted(names - roster)}")
        self.assertEqual(sites, 12, "a roster site appeared or vanished")


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
