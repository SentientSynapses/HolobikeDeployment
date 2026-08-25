"""The `build` verb as a pipeline, driven through the CLI.

The resolution is line-wide; a build composes one profile (D-23). These
tests fix the consequence: drift in a member the profile does not select is
carried as a recorded fact, drift in a member it does select stops the run,
and `--only resolve` keeps the line-wide verdict the daily cadence relies on.
"""

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SHIM = REPO_ROOT / "Tool" / "holobike"


def run_cli(*arguments):
    return subprocess.run(
        [sys.executable, str(SHIM), *arguments],
        capture_output=True, text=True, check=False)


def make_git_checkout(path, branch="main"):
    path.mkdir(parents=True)
    (path / ".gitignore").write_text("Builds/\n", encoding="utf-8")
    for command in (
        ["git", "init", "--quiet", f"--initial-branch={branch}"],
        ["git", "config", "user.email", "build@test.invalid"],
        ["git", "config", "user.name", "Build Test"],
        ["git", "add", ".gitignore"],
        ["git", "commit", "--quiet", "--message", "fixture"],
    ):
        subprocess.run(command, cwd=path, check=True, capture_output=True)


class BuildPipelineBehaviour(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.root = pathlib.Path(self.scratch.name)
        self.artifacts = self.root / "Artifacts"
        self.stack = self.root / "Stack"
        (self.stack / "geo").mkdir(parents=True)
        (self.stack / "os").mkdir()
        (self.stack / "geo" / "HexAtlas.json").write_text(json.dumps({
            "schema_version": 2, "integration": "HexAtlas", "domain": "geo",
            "repository": "HexAtlas",
            "deployables": {"AtlasServer": {
                "destination": "server",
                "build": {"steps": [{"argv": [
                    "sh", "-c",
                    "mkdir -p Builds && printf server > Builds/HexAtlasServer"]}]},
                "artifacts": ["Builds/HexAtlasServer"]}}}), encoding="utf-8")
        (self.stack / "os" / "uroborOS.json").write_text(json.dumps({
            "schema_version": 2, "integration": "uroborOS", "domain": "os",
            "repository": "uroborOS",
            "deployables": {"uroborOS": {"destination": "device"}}}),
            encoding="utf-8")
        self.profile = self.root / "atlas.json"
        self.profile.write_text(json.dumps({
            "schema_version": 2, "profile": "atlas", "destination": "server",
            "deployables": [
                {"integration": "HexAtlas", "deployable": "AtlasServer"}]}),
            encoding="utf-8")

    def line(self, atlas_branch, os_branch):
        atlas = self.root / "checkouts" / "HexAtlas"
        os_checkout = self.root / "checkouts" / "uroborOS"
        make_git_checkout(atlas, atlas_branch)
        make_git_checkout(os_checkout, os_branch)
        environment = self.root / "environment.json"
        environment.write_text(json.dumps({
            "schema_version": 3, "host": "workstation", "os": "linux",
            "checkouts": {"HexAtlas": str(atlas),
                          "uroborOS": str(os_checkout)}}), encoding="utf-8")
        revisions = self.root / "dev.json"
        revisions.write_text(json.dumps({
            "schema_version": 1, "line": "dev",
            "selections": {"HexAtlas": {"branch": "main"},
                           "uroborOS": {"branch": "main"}}}),
            encoding="utf-8")
        return environment, revisions

    def build(self, environment, revisions, *extra):
        return run_cli(
            "build", "atlas", *extra,
            "--profile-path", str(self.profile),
            "--revisions", str(revisions),
            "--environment", str(environment),
            "--artifacts", str(self.artifacts),
            "--stack", str(self.stack))

    def assemblies(self):
        return sorted((self.artifacts / "records").glob("assemble-atlas-*"))

    def test_drift_outside_the_profile_is_carried_not_fatal(self):
        environment, revisions = self.line("main", "elsewhere")
        result = self.build(environment, revisions)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("uroborOS: selection_mismatch", result.stdout)
        self.assertIn("lie outside profile atlas", result.stdout)
        self.assertIn("built: assemble-atlas-", result.stdout)
        self.assertEqual(len(self.assemblies()), 1)
        # Nothing in the profile declares a service, so emulation has
        # nothing honest to say and is skipped as a stated fact.
        self.assertIn("emulate: skipped — nothing in profile atlas",
                      result.stdout)
        self.assertEqual(
            sorted((self.artifacts / "records").glob("emulate-*")), [])
        # The fact travels: the resolution the assembly binds still says it.
        assembly = json.loads(self.assemblies()[0].read_text("utf-8"))
        resolution = json.loads(
            (self.artifacts / "records" / assembly["resolution"]["record"])
            .read_text("utf-8"))
        self.assertEqual(
            resolution["resolved"]["uroborOS"]["status"], "selection_mismatch")

    def test_drift_inside_the_profile_stops_the_build(self):
        environment, revisions = self.line("elsewhere", "main")
        result = self.build(environment, revisions)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("unresolved in profile atlas: HexAtlas", result.stderr)
        self.assertEqual(self.assemblies(), [])

    def test_only_resolve_keeps_the_line_wide_verdict(self):
        environment, revisions = self.line("main", "elsewhere")
        result = self.build(environment, revisions, "--only", "resolve")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertNotIn("continuing", result.stdout)


if __name__ == "__main__":
    unittest.main()
