"""The environment schema's conformance suite.

Drives the CLI — the tool's testable surface — over every fixture
under `tests/fixtures/environment` and `tests/fixtures/integration`, and holds the
committed Stack leaves to the same judge as the corpus.
"""

import json
import pathlib
import subprocess
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SHIM = REPO_ROOT / "Tool" / "holobike"
FIXTURES = REPO_ROOT / "Tool" / "tests" / "fixtures" / "environment"
INTEGRATION_FIXTURES = REPO_ROOT / "Tool" / "tests" / "fixtures" / "integration"
SCHEMAS = REPO_ROOT / "Tool" / "src" / "holobike" / "schemas"
FIXTURES_ROOT = REPO_ROOT / "Tool" / "tests" / "fixtures"
SCHEMA = SCHEMAS / "environment.schema.json"
INTEGRATION_SCHEMA = REPO_ROOT / "Tool" / "src" / "holobike" / "schemas" / "integration.schema.json"


def stack_leaves():
    """Every committed integration contract: <domain>/<Integration>.json."""
    return sorted(
        path for path in (REPO_ROOT / "Stack").rglob("*.json")
        if path.name != "nonmembers.json")


def validate_only(document_path):
    return subprocess.run(
        [sys.executable, str(SHIM), "check",
         "--validate-only", "--environment", str(document_path)],
        capture_output=True,
        text=True,
        check=False,
    )


def validate_integration(document_path):
    return subprocess.run(
        [sys.executable, str(SHIM), "check",
         "--validate-integration", str(document_path)],
        capture_output=True,
        text=True,
        check=False,
    )


def validate_nonmembers(document_path):
    return subprocess.run(
        [sys.executable, str(SHIM), "check",
         "--validate-nonmembers", str(document_path)],
        capture_output=True,
        text=True,
        check=False,
    )


def validate_revisions(document_path):
    return subprocess.run(
        [sys.executable, str(SHIM), "check",
         "--validate-revisions", str(document_path)],
        capture_output=True,
        text=True,
        check=False,
    )


def validate_record(document_path):
    return subprocess.run(
        [sys.executable, str(SHIM), "check",
         "--validate-record", str(document_path)],
        capture_output=True,
        text=True,
        check=False,
    )


def validate_policy(document_path):
    return subprocess.run(
        [sys.executable, str(SHIM), "check",
         "--validate-policy", str(document_path)],
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


class IntegrationConformance(unittest.TestCase):
    def test_every_fixture_is_classified_and_holds(self):
        run_fixture_corpus(self, INTEGRATION_FIXTURES, validate_integration)

    def test_every_leaf_has_a_README(self):
        # OrielUI was a member in every mechanism — selected, in twelve roster
        # enums, carrying a passing gate — and the only leaf without one.
        for leaf in stack_leaves():
            with self.subTest(leaf=leaf.stem):
                self.assertTrue(leaf.with_suffix(".md").is_file())

    def test_every_leaf_is_named_in_the_roster_tables(self):
        # The stray scan catches a repository nobody declared. This catches
        # the opposite: a member declared everywhere except where a person
        # reads the roster.
        tables = "\n".join(
            (REPO_ROOT / name).read_text(encoding="utf-8")
            for name in ("README.md", "Stack/README.md"))
        for leaf in stack_leaves():
            name = json.loads(leaf.read_text(encoding="utf-8"))["integration"]
            with self.subTest(integration=name):
                self.assertEqual(
                    tables.count(f"[`{name}`]"), 2,
                    f"{name} must appear in both roster tables")

    def test_every_stack_leaf_is_an_accepted_fixture(self):
        # The committed leaves are held to the same judge as the corpus: a
        # leaf that drifts from the contract fails the suite, not just the
        # next live preflight. The expected set is read off the schema's
        # roster rather than counted, so enrolling an integration cannot
        # leave this assertion behind, and a duplicate or misnamed leaf is
        # caught as precisely as a missing one.
        schema = json.loads(INTEGRATION_SCHEMA.read_text(encoding="utf-8"))
        roster = schema["properties"]["integration"]["enum"]
        leaves = stack_leaves()
        declared = [json.loads(leaf.read_text(encoding="utf-8"))["integration"]
                    for leaf in leaves]
        self.assertEqual(sorted(declared), sorted(roster), leaves)
        for leaf in leaves:
            with self.subTest(leaf=str(leaf.relative_to(REPO_ROOT))):
                result = validate_integration(leaf)
                self.assertEqual(result.returncode, 0, result.stderr)


class NonMembersConformance(unittest.TestCase):
    """The declaration that closes the roster into a loop.

    A repository in neither the roster nor this file is a named problem
    rather than a discovery — which only holds while the file itself is held
    to a contract.
    """

    def test_every_fixture_is_classified_and_holds(self):
        run_fixture_corpus(
            self, REPO_ROOT / "Tool" / "tests" / "fixtures" / "nonmembers", validate_nonmembers)

    def test_the_declaration_validates(self):
        result = validate_nonmembers(REPO_ROOT / "Stack" / "nonmembers.json")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_no_declared_nonmember_is_also_a_member(self):
        # Both at once would make the roster ambiguous rather than closed.
        sys.path.insert(0, str(REPO_ROOT / "Tool" / "src"))
        from holobike import nonmembers, stack

        declared, errors = nonmembers.load_nonmembers(
            REPO_ROOT / "Stack" / "nonmembers.json")
        self.assertEqual(errors, [])
        documents, errors = stack.load_stack(REPO_ROOT / "Stack")
        self.assertEqual(errors, [])
        members = {d.repository for d in documents.values()}
        self.assertEqual(members & set(declared), set())


class RevisionsConformance(unittest.TestCase):
    def test_every_fixture_is_classified_and_holds(self):
        run_fixture_corpus(
            self, FIXTURES_ROOT / "revisions", validate_revisions)

    def test_every_committed_line_is_an_accepted_fixture(self):
        lines = sorted((REPO_ROOT / "Revisions").glob("*.json"))
        self.assertTrue(lines, "Revisions/ must declare at least one line")
        for line in lines:
            with self.subTest(line=line.name):
                result = validate_revisions(line)
                self.assertEqual(result.returncode, 0, result.stderr)
                # The line's name is its file name; a manifest that
                # disagrees with its own file is filed wrong.
                document = json.loads(line.read_text(encoding="utf-8"))
                self.assertEqual(document["line"], line.stem)

    def test_the_binding_matches_the_schema(self):
        sys.path.insert(0, str(REPO_ROOT / "Tool" / "src"))
        from holobike import environment, revisions

        schema = json.loads(
            (SCHEMAS / "revisions.schema.json")
            .read_text(encoding="utf-8"))
        self.assertEqual(
            set(schema["properties"]["selections"]["properties"]),
            set(environment.INTEGRATIONS))
        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            revisions.SCHEMA_VERSION)


class PolicyConformance(unittest.TestCase):
    def test_every_fixture_is_classified_and_holds(self):
        run_fixture_corpus(
            self, FIXTURES_ROOT / "policy", validate_policy)

    def test_every_committed_policy_is_an_accepted_fixture(self):
        policies = sorted((REPO_ROOT / "Policy").glob("*.json"))
        self.assertTrue(policies, "Policy/ must declare at least one policy")
        for path in policies:
            with self.subTest(policy=path.name):
                result = validate_policy(path)
                self.assertEqual(result.returncode, 0, result.stderr)
                document = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(document["policy"], path.stem)

    def test_the_binding_matches_the_schema(self):
        sys.path.insert(0, str(REPO_ROOT / "Tool" / "src"))
        from holobike import environment, policy

        schema = json.loads(
            (SCHEMAS / "policy.schema.json")
            .read_text(encoding="utf-8"))
        self.assertEqual(
            set(schema["$defs"]["site"]["properties"]["integration"]["enum"]),
            set(environment.INTEGRATIONS))
        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            policy.SCHEMA_VERSION)


def validate_profile(document_path):
    return subprocess.run(
        [sys.executable, str(SHIM), "check",
         "--validate-profile", str(document_path)],
        capture_output=True,
        text=True,
        check=False,
    )


class ProfilesConformance(unittest.TestCase):
    def test_every_fixture_is_classified_and_holds(self):
        run_fixture_corpus(
            self, FIXTURES_ROOT / "profiles", validate_profile)

    def test_every_committed_profile_is_an_accepted_fixture(self):
        committed = sorted((REPO_ROOT / "Profiles").glob("*.json"))
        self.assertTrue(committed,
                        "Profiles/ must declare at least one profile")
        for path in committed:
            with self.subTest(profile=path.name):
                result = validate_profile(path)
                self.assertEqual(result.returncode, 0, result.stderr)
                document = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(document["profile"], path.stem)



class RecordConformance(unittest.TestCase):
    def test_every_fixture_is_classified_and_holds(self):
        run_fixture_corpus(
            self, FIXTURES_ROOT / "record", validate_record)

    def test_the_binding_matches_the_schema(self):
        sys.path.insert(0, str(REPO_ROOT / "Tool" / "src"))
        from holobike import environment, record

        schema = json.loads(
            (SCHEMAS / "record.schema.json")
            .read_text(encoding="utf-8"))
        self.assertEqual(
            set(schema["properties"]["resolved"]["properties"]),
            set(environment.INTEGRATIONS))
        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            record.SCHEMA_VERSION)


if __name__ == "__main__":
    unittest.main()
