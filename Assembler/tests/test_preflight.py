"""Preflight behaviour, driven through the CLI against fabricated checkouts.

Every fixture repository is built fresh in a temp directory — hermetic, and
proof that preflight measures rather than assumes.
"""

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SHIM = REPO_ROOT / "Assembler" / "holobike-assemble"


def run_preflight(*arguments):
    return subprocess.run(
        [sys.executable, str(SHIM), "preflight", *arguments],
        capture_output=True,
        text=True,
        check=False,
    )


def make_git_checkout(path):
    path.mkdir(parents=True)
    for command in (
        ["git", "init", "--quiet", "--initial-branch=main"],
        ["git", "config", "user.email", "preflight@test.invalid"],
        ["git", "config", "user.name", "Preflight Test"],
        ["git", "commit", "--quiet", "--allow-empty",
         "--message", "fixture"],
    ):
        subprocess.run(command, cwd=path, check=True, capture_output=True)
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=path, check=True,
        capture_output=True, text=True).stdout.strip()
    return revision


ROSTER = (
    "uroborOS", "HexAtlas", "Assetscape", "HolobikeCore", "AthleteIdentity",
    "drAIs", "HolobikeExperience", "HolobikeDevice", "HolobikeRider",
    "HolobikeWorlds",
    "HoloviewDisplay",
    "OrielUI",
)


def minimal_leaf(name, repository=None):
    return {
        "schema_version": 1,
        "integration": name,
        "kit": "geo_kit",
        "repository": repository or name,
    }


class PreflightBehaviour(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.scratch.name)
        self.addCleanup(self.scratch.cleanup)

    def write_environment(self, checkouts):
        document = {"schema_version": 1, "checkouts": checkouts}
        path = self.root / "environment.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        return path

    def write_stack(self, leaves):
        """Fabricate a Stack tree: {directory name: document or raw text}."""
        stack = self.root / "Stack"
        for name, document in leaves.items():
            leaf = stack / name
            leaf.mkdir(parents=True, exist_ok=True)
            text = document if isinstance(document, str) \
                else json.dumps(document)
            (leaf / "integration.json").write_text(text, encoding="utf-8")
        stack.mkdir(exist_ok=True)
        return stack

    def full_stack(self, overrides=None):
        leaves = {name: minimal_leaf(name) for name in ROSTER}
        leaves.update(overrides or {})
        return self.write_stack(leaves)

    def report_for(self, environment_path, stack=None):
        result = run_preflight(
            "--json", "--environment", str(environment_path),
            "--stack", str(stack if stack is not None else self.full_stack()))
        report = json.loads(result.stdout)
        return result, report

    def test_a_clean_checkout_reports_its_revision(self):
        checkout = self.root / "HexAtlas"
        revision = make_git_checkout(checkout)
        environment = self.write_environment({"HexAtlas": str(checkout)})

        result, report = self.report_for(environment)
        self.assertEqual(result.returncode, 0, result.stderr)
        facts = report["integrations"]["HexAtlas"]
        self.assertEqual(facts["status"], "clean")
        self.assertEqual(facts["revision"], revision)
        self.assertEqual(facts["branch"], "main")
        self.assertFalse(facts["dirty"])
        # Undeclared integrations are reported as such, never invented.
        self.assertEqual(
            report["integrations"]["uroborOS"]["status"], "undeclared")

    def test_a_dirty_checkout_is_a_fact_not_a_failure(self):
        checkout = self.root / "HexAtlas"
        make_git_checkout(checkout)
        (checkout / "uncommitted.txt").write_text("wip", encoding="utf-8")
        environment = self.write_environment({"HexAtlas": str(checkout)})

        result, report = self.report_for(environment)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(report["integrations"]["HexAtlas"]["dirty"])
        self.assertEqual(
            report["integrations"]["HexAtlas"]["status"], "dirty")

    def test_a_missing_checkout_is_a_problem(self):
        environment = self.write_environment(
            {"HexAtlas": str(self.root / "nowhere")})
        result, report = self.report_for(environment)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(
            report["integrations"]["HexAtlas"]["status"], "missing")

    def test_a_repository_git_refuses_is_unreadable_not_absent(self):
        checkout = self.root / "HexAtlas"
        checkout.mkdir()
        # A gitfile pointing nowhere: git metadata exists, git refuses it —
        # the class of fact a root-owned checkout produces.
        (checkout / ".git").write_text(
            "gitdir: /nonexistent\n", encoding="utf-8")
        environment = self.write_environment({"HexAtlas": str(checkout)})
        result, report = self.report_for(environment)
        self.assertEqual(result.returncode, 1)
        facts = report["integrations"]["HexAtlas"]
        self.assertEqual(facts["status"], "unreadable_repository")
        self.assertTrue(facts["detail"])

    def test_a_plain_directory_is_not_a_checkout(self):
        checkout = self.root / "HexAtlas"
        checkout.mkdir()
        environment = self.write_environment({"HexAtlas": str(checkout)})
        result, report = self.report_for(environment)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(
            report["integrations"]["HexAtlas"]["status"],
            "not_a_git_repository")

    def test_a_refused_document_reports_why_and_touches_nothing(self):
        path = self.root / "environment.json"
        path.write_text(
            json.dumps({"schema_version": 1, "checkouts": {},
                        "surprise": True}),
            encoding="utf-8")
        result = run_preflight("--environment", str(path))
        self.assertEqual(result.returncode, 2)
        self.assertIn("surprise", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_the_human_table_names_every_integration(self):
        checkout = self.root / "HexAtlas"
        make_git_checkout(checkout)
        environment = self.write_environment({"HexAtlas": str(checkout)})
        result = run_preflight(
            "--environment", str(environment),
            "--stack", str(self.full_stack()))
        self.assertEqual(result.returncode, 0)
        for name in ("INTEGRATION", "LEAF", "HexAtlas", "uroborOS",
                     "undeclared"):
            self.assertIn(name, result.stdout)

    def test_a_missing_leaf_is_a_problem(self):
        environment = self.write_environment({})
        leaves = {name: minimal_leaf(name) for name in ROSTER
                  if name != "HexAtlas"}
        result, report = self.report_for(
            environment, self.write_stack(leaves))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(report["stack"]["HexAtlas"]["status"],
                         "leaf_missing")

    def test_an_invalid_leaf_carries_its_errors(self):
        environment = self.write_environment({})
        stack = self.full_stack(
            {"HexAtlas": '{"schema_version": 1, "surprise": true}'})
        result, report = self.report_for(environment, stack)
        self.assertEqual(result.returncode, 1)
        facts = report["stack"]["HexAtlas"]
        self.assertEqual(facts["status"], "invalid")
        self.assertTrue(facts["errors"])

    def test_a_leaf_disagreeing_with_its_directory_is_a_mismatch(self):
        environment = self.write_environment({})
        stack = self.full_stack(
            {"HexAtlas": minimal_leaf("Assetscape")})
        result, report = self.report_for(environment, stack)
        self.assertEqual(result.returncode, 1)
        # The document filed itself under Assetscape, so Assetscape sees a
        # duplicate and HexAtlas sees nothing — both truthfully reported.
        self.assertEqual(report["stack"]["HexAtlas"]["status"],
                         "leaf_missing")
        self.assertEqual(report["stack"]["Assetscape"]["status"],
                         "duplicate")

    def test_a_leaf_that_contradicts_the_checkout_name_is_a_problem(self):
        checkout = self.root / "HexAtlas"
        make_git_checkout(checkout)
        environment = self.write_environment({"HexAtlas": str(checkout)})
        stack = self.full_stack(
            {"HexAtlas": minimal_leaf("HexAtlas",
                                      repository="HexAtlas_uplugin")})
        result, report = self.report_for(environment, stack)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(report["stack"]["HexAtlas"]["status"],
                         "checkout_repository_mismatch")

    def test_a_stray_leaf_outside_the_roster_is_a_problem(self):
        environment = self.write_environment({})
        stack = self.full_stack(
            {"Mystery": '{"schema_version": 1}'})
        result, report = self.report_for(environment, stack)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(report["stack_strays"])


if __name__ == "__main__":
    unittest.main()
