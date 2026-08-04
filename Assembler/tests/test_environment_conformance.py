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
INTEGRATION_FIXTURES = REPO_ROOT / "Conformance" / "integration"
SCHEMA = REPO_ROOT / "Schemas" / "environment.schema.json"
INTEGRATION_SCHEMA = REPO_ROOT / "Schemas" / "integration.schema.json"
EXAMPLE = REPO_ROOT / "Schemas" / "environment.example.json"


def validate_only(document_path):
    return subprocess.run(
        [sys.executable, str(SHIM), "preflight",
         "--validate-only", "--environment", str(document_path)],
        capture_output=True,
        text=True,
        check=False,
    )


def validate_integration(document_path):
    return subprocess.run(
        [sys.executable, str(SHIM), "preflight",
         "--validate-integration", str(document_path)],
        capture_output=True,
        text=True,
        check=False,
    )


def run_fixture_corpus(test, fixtures_dir, judge):
    fixtures = sorted(fixtures_dir.iterdir())
    test.assertTrue(fixtures, "the conformance corpus must not be empty")
    for fixture in fixtures:
        with test.subTest(fixture=fixture.name):
            if fixture.name.startswith("accepted."):
                result = judge(fixture)
                test.assertEqual(
                    result.returncode, 0,
                    f"accepted fixture refused: {result.stderr}")
                test.assertEqual(result.stderr, "")
            elif fixture.name.startswith("rejected."):
                result = judge(fixture)
                test.assertEqual(
                    result.returncode, 2, "rejected fixture accepted")
                test.assertNotEqual(
                    result.stderr, "", "a refusal must say why")
            else:
                test.fail(
                    f"unclassifiable fixture: {fixture.name} — a fixture "
                    "nobody runs is a contract nobody keeps")


class EnvironmentConformance(unittest.TestCase):
    def test_every_fixture_is_classified_and_holds(self):
        run_fixture_corpus(self, FIXTURES, validate_only)

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


class IntegrationConformance(unittest.TestCase):
    def test_every_fixture_is_classified_and_holds(self):
        run_fixture_corpus(self, INTEGRATION_FIXTURES, validate_integration)

    def test_the_binding_matches_the_schema(self):
        sys.path.insert(0, str(REPO_ROOT / "Assembler" / "src"))
        from holobike_assemble import environment, integration

        schema = json.loads(INTEGRATION_SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(
            set(schema["properties"]["integration"]["enum"]),
            set(environment.INTEGRATIONS))
        self.assertEqual(
            set(schema["properties"]["kit"]["enum"]),
            set(integration.KITS))
        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            integration.SCHEMA_VERSION)

    def test_every_stack_leaf_is_an_accepted_fixture(self):
        # The ten committed leaves are held to the same judge as the corpus:
        # a leaf that drifts from the contract fails the suite, not just the
        # next live preflight.
        leaves = sorted((REPO_ROOT / "Stack").glob("**/integration.json"))
        self.assertEqual(len(leaves), 10, leaves)
        for leaf in leaves:
            with self.subTest(leaf=str(leaf.relative_to(REPO_ROOT))):
                result = validate_integration(leaf)
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
