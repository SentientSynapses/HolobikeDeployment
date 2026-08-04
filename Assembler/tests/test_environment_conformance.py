"""The environment schema's conformance suite.

Drives the CLI — the Assembler's testable surface — over every fixture
under Conformance/environment, plus the schema's own example document, and
holds the Python binding's roster to the canonical schema.
"""

import json
import pathlib
import subprocess
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SHIM = REPO_ROOT / "Assembler" / "holobike-assemble"
FIXTURES = REPO_ROOT / "Conformance" / "environment"
SCHEMA = REPO_ROOT / "Schemas" / "environment.schema.json"
EXAMPLE = REPO_ROOT / "Schemas" / "environment.example.json"


def validate_only(document_path):
    return subprocess.run(
        [sys.executable, str(SHIM), "preflight",
         "--validate-only", "--environment", str(document_path)],
        capture_output=True,
        text=True,
        check=False,
    )


class EnvironmentConformance(unittest.TestCase):
    def test_every_fixture_is_classified_and_holds(self):
        fixtures = sorted(FIXTURES.iterdir())
        self.assertTrue(fixtures, "the conformance corpus must not be empty")
        for fixture in fixtures:
            with self.subTest(fixture=fixture.name):
                if fixture.name.startswith("accepted."):
                    result = validate_only(fixture)
                    self.assertEqual(
                        result.returncode, 0,
                        f"accepted fixture refused: {result.stderr}")
                    self.assertEqual(result.stderr, "")
                elif fixture.name.startswith("rejected."):
                    result = validate_only(fixture)
                    self.assertEqual(
                        result.returncode, 2,
                        "rejected fixture accepted")
                    self.assertNotEqual(
                        result.stderr, "",
                        "a refusal must say why")
                else:
                    self.fail(
                        f"unclassifiable fixture: {fixture.name} — a fixture "
                        "nobody runs is a contract nobody keeps")

    def test_the_example_document_is_an_accepted_fixture(self):
        result = validate_only(EXAMPLE)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_the_binding_roster_matches_the_schema(self):
        sys.path.insert(0, str(REPO_ROOT / "Assembler" / "src"))
        from holobike_assemble import environment

        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        schema_integrations = set(
            schema["properties"]["checkouts"]["properties"])
        schema_toolchains = set(
            schema["properties"]["toolchains"]["properties"])
        self.assertEqual(schema_integrations, set(environment.INTEGRATIONS))
        self.assertEqual(schema_toolchains, set(environment.TOOLCHAINS))
        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            environment.SCHEMA_VERSION)


if __name__ == "__main__":
    unittest.main()
