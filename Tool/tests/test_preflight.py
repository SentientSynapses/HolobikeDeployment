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
SHIM = REPO_ROOT / "Tool" / "holobike"


def run_preflight(*arguments):
    return subprocess.run(
        [sys.executable, str(SHIM), "check", *arguments],
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
    "AthleteInsights",
    "drAIs", "HolobikeExperience", "HolobikeDevice", "HolobikeRider",
    "HolobikeWorlds",
    "HoloviewDisplay",
    "OrielUI",
)


def minimal_leaf(name, repository=None):
    return {
        "schema_version": 2,
        "integration": name,
        "domain": "geo",
        "repository": repository or name,
        "deployables": {"AtlasClient": {"destination": "device"}},
    }


class PreflightFixtures(unittest.TestCase):
    """Scaffolding only. Carries no tests of its own, so the suites that
    build on it do not re-run each other's."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.scratch.name)
        self.addCleanup(self.scratch.cleanup)

    def write_environment(self, checkouts, toolchains=None):
        document = {"schema_version": 3, "host": "workstation", "os": "linux", "checkouts": checkouts}
        if toolchains is not None:
            document["toolchains"] = toolchains
        path = self.root / "environment.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        return path

    def make_engine(self, name, major, minor, patch=0):
        """A directory an engine's version can actually be read out of."""
        engine = self.root / name
        build = engine / "Engine" / "Build"
        build.mkdir(parents=True)
        (build / "Build.version").write_text(
            json.dumps({"MajorVersion": major, "MinorVersion": minor,
                        "PatchVersion": patch}),
            encoding="utf-8")
        return engine

    def make_unreal_project(self, checkout, relative, association):
        project = checkout / relative
        project.parent.mkdir(parents=True, exist_ok=True)
        project.write_text(
            json.dumps({"FileVersion": 3,
                        "EngineAssociation": association}),
            encoding="utf-8")
        return relative

    def write_stack(self, leaves):
        """Fabricate a Stack tree: {leaf name: document or raw text}."""
        stack = self.root / "Stack"
        stack.mkdir(parents=True, exist_ok=True)
        for name, document in leaves.items():
            text = document if isinstance(document, str) \
                else json.dumps(document)
            (stack / f"{name}.json").write_text(text, encoding="utf-8")
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

class PreflightBehaviour(PreflightFixtures):
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
            json.dumps({"schema_version": 3, "host": "workstation", "os": "linux", "checkouts": {},
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


class EngineAssociation(PreflightFixtures):
    """The project and the declared engine must be talking about one engine.

    This existed as two unrelated facts for a while: the environment named an
    engine directory and preflight asked only whether it was there, while the
    project's own EngineAssociation went unread. A workstation carrying two
    engines answers "present" to either of them, so a mapping that named the
    wrong one looked healthy — which is precisely how it drifted.
    """

    PROJECT = "HolobikeExperience/HolobikeExperience.uproject"

    def experience(self, association, engine_minor):
        checkout = self.root / "HolobikeExperience_uproject"
        make_git_checkout(checkout)
        self.make_unreal_project(checkout, self.PROJECT, association)
        engine = self.make_engine(f"UE-5.{engine_minor}", 5, engine_minor)
        environment = self.write_environment(
            {"HolobikeExperience": str(checkout)},
            {"unreal_engine": {"5.3": str(engine)}})
        leaf = minimal_leaf("HolobikeExperience", repository="HolobikeExperience_uproject")
        leaf["unreal_project"] = self.PROJECT
        return self.report_for(
            environment, self.full_stack({"HolobikeExperience": leaf}))

    def test_a_project_and_its_engine_may_agree(self):
        result, report = self.experience("5.3", 3)
        facts = report["engine_associations"]["HolobikeExperience"]
        self.assertEqual(facts["status"], "agrees")
        self.assertEqual(facts["engine_association"], "5.3")
        self.assertEqual(facts["engine_version"], "5.3")
        self.assertEqual(result.returncode, 0)

    def test_an_engine_entry_that_lies_about_its_version_is_caught(self):
        # The map is keyed by version, so a 5.3 entry pointing at a 5.7 tree
        # is a misdeclaration — and saying WHICH declaration is wrong beats
        # the old "project wants 5.3, toolchain is 5.7", which left the reader
        # to guess whether the project or the mapping needed changing.
        result, report = self.experience("5.3", 7)
        facts = report["engine_associations"]["HolobikeExperience"]
        self.assertEqual(facts["status"], "engine_misdeclared")
        engine = report["toolchains"]["unreal_engine"]
        self.assertEqual(engine["status"], "misdeclared")
        self.assertEqual(engine["engines"]["5.3"]["found"], "5.7")
        self.assertEqual(result.returncode, 1)

    def test_an_engine_the_host_does_not_declare_is_named(self):
        # A workstation may carry several engines and none of the demanded
        # one. Presence of *an* engine was never the question.
        result, report = self.experience("5.9", 3)
        facts = report["engine_associations"]["HolobikeExperience"]
        self.assertEqual(facts["status"], "engine_undeclared")
        self.assertIn("5.9", facts["detail"])
        self.assertIn("5.3", facts["detail"])
        self.assertEqual(result.returncode, 1)

    def test_an_undeclared_project_is_not_judged(self):
        checkout = self.root / "HexAtlas"
        make_git_checkout(checkout)
        engine = self.make_engine("UE-5.3", 5, 3)
        environment = self.write_environment(
            {"HexAtlas": str(checkout)}, {"unreal_engine": {"5.3": str(engine)}})
        result, report = self.report_for(environment)
        # No leaf declares a project, so there is nothing to hold to anything.
        self.assertEqual(report["engine_associations"], {})
        self.assertEqual(result.returncode, 0)

    def test_a_declared_project_that_is_not_there_is_a_problem(self):
        checkout = self.root / "HolobikeExperience"
        make_git_checkout(checkout)
        engine = self.make_engine("UE-5.3", 5, 3)
        environment = self.write_environment(
            {"HolobikeExperience": str(checkout)},
            {"unreal_engine": {"5.3": str(engine)}})
        leaf = minimal_leaf("HolobikeExperience", repository="HolobikeExperience_uproject")
        leaf["unreal_project"] = self.PROJECT
        result, report = self.report_for(
            environment, self.full_stack({"HolobikeExperience": leaf}))
        self.assertEqual(
            report["engine_associations"]["HolobikeExperience"]["status"],
            "project_unreadable")
        self.assertEqual(result.returncode, 1)

    def test_an_engine_without_a_version_is_said_so_not_assumed(self):
        checkout = self.root / "HolobikeExperience_uproject"
        make_git_checkout(checkout)
        self.make_unreal_project(checkout, self.PROJECT, "5.3")
        engine = self.root / "UE-unlabelled"
        engine.mkdir()
        environment = self.write_environment(
            {"HolobikeExperience": str(checkout)},
            {"unreal_engine": {"5.3": str(engine)}})
        leaf = minimal_leaf("HolobikeExperience", repository="HolobikeExperience_uproject")
        leaf["unreal_project"] = self.PROJECT
        result, report = self.report_for(
            environment, self.full_stack({"HolobikeExperience": leaf}))
        self.assertEqual(
            report["engine_associations"]["HolobikeExperience"]["status"],
            "engine_unversioned")
        self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()
