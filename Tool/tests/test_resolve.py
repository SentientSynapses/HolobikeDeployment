"""Resolve behaviour, driven through the CLI against fabricated checkouts.

Every record a test provokes is re-judged through the record contract via
the CLI — the writer and the judge must agree or nothing here counts.
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
        capture_output=True,
        text=True,
        check=False,
    )


def make_git_checkout(path, branch="main"):
    path.mkdir(parents=True)
    for command in (
        ["git", "init", "--quiet", f"--initial-branch={branch}"],
        ["git", "config", "user.email", "resolve@test.invalid"],
        ["git", "config", "user.name", "Resolve Test"],
        ["git", "commit", "--quiet", "--allow-empty",
         "--message", "fixture"],
    ):
        subprocess.run(command, cwd=path, check=True, capture_output=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=path, check=True,
        capture_output=True, text=True).stdout.strip()


class ResolveBehaviour(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.scratch.name)
        self.addCleanup(self.scratch.cleanup)
        self.artifacts = self.root / "Artifacts"

    def write_environment(self, checkouts):
        path = self.root / "environment.json"
        path.write_text(
            json.dumps({"schema_version": 2, "host": "workstation", "os": "linux", "checkouts": checkouts}),
            encoding="utf-8")
        return path

    def write_revisions(self, selections, line="dev"):
        path = self.root / f"{line}.json"
        path.write_text(
            json.dumps({
                "schema_version": 1,
                "line": line,
                "selections": selections,
            }),
            encoding="utf-8")
        return path

    def resolve(self, revisions_path, environment_path):
        # No gate kinds exist since D-08 retired parity — these tests exercise
        # resolution alone; gate behaviour has its own suite.
        result = run_cli(
            "build", "--only", "resolve",
            "--revisions", str(revisions_path),
            "--environment", str(environment_path),
            "--artifacts", str(self.artifacts),
            )
        return result

    def written_record(self, result):
        prefix = "record: "
        lines = [line for line in result.stdout.splitlines()
                 if line.startswith(prefix)]
        self.assertEqual(len(lines), 1, result.stdout)
        record_path = pathlib.Path(lines[0][len(prefix):])
        self.assertTrue(record_path.is_file())
        judged = run_cli("check", "--validate-record", str(record_path))
        self.assertEqual(judged.returncode, 0, judged.stderr)
        return json.loads(record_path.read_text(encoding="utf-8"))

    def test_a_matching_branch_selection_resolves_and_pins(self):
        checkout = self.root / "HexAtlas"
        revision = make_git_checkout(checkout)
        environment = self.write_environment({"HexAtlas": str(checkout)})
        revisions = self.write_revisions({"HexAtlas": {"branch": "main"}})

        result = self.resolve(revisions, environment)
        self.assertEqual(result.returncode, 0, result.stderr)
        record = self.written_record(result)
        facts = record["resolved"]["HexAtlas"]
        self.assertEqual(facts["status"], "resolved")
        self.assertEqual(facts["revision"], revision)
        self.assertEqual(record["problems"], [])
        # Self-identity: the deployment repository pins itself.
        self.assertEqual(len(record["deployment"]["revision"]), 40)

    def test_a_branch_mismatch_is_recorded_not_refused(self):
        checkout = self.root / "HexAtlas"
        make_git_checkout(checkout, branch="feature")
        environment = self.write_environment({"HexAtlas": str(checkout)})
        revisions = self.write_revisions({"HexAtlas": {"branch": "main"}})

        result = self.resolve(revisions, environment)
        self.assertEqual(result.returncode, 1)
        record = self.written_record(result)
        facts = record["resolved"]["HexAtlas"]
        self.assertEqual(facts["status"], "selection_mismatch")
        self.assertIn("feature", facts["detail"])
        self.assertTrue(record["problems"])

    def test_a_commit_selection_demands_exactly_that_commit(self):
        checkout = self.root / "HexAtlas"
        revision = make_git_checkout(checkout)
        environment = self.write_environment({"HexAtlas": str(checkout)})

        exact = self.write_revisions(
            {"HexAtlas": {"commit": revision}}, line="pinned")
        result = self.resolve(exact, environment)
        self.assertEqual(result.returncode, 0, result.stderr)

        other = self.write_revisions(
            {"HexAtlas": {"commit": "0" * 40}}, line="stale")
        result = self.resolve(other, environment)
        self.assertEqual(result.returncode, 1)
        record = self.written_record(result)
        self.assertEqual(
            record["resolved"]["HexAtlas"]["status"], "selection_mismatch")

    def test_dirty_state_rides_the_record(self):
        checkout = self.root / "HexAtlas"
        make_git_checkout(checkout)
        (checkout / "wip.txt").write_text("wip", encoding="utf-8")
        environment = self.write_environment({"HexAtlas": str(checkout)})
        revisions = self.write_revisions({"HexAtlas": {"branch": "main"}})

        result = self.resolve(revisions, environment)
        self.assertEqual(result.returncode, 0)
        record = self.written_record(result)
        self.assertTrue(record["resolved"]["HexAtlas"]["dirty"])

    def test_an_undeclared_checkout_is_unresolvable(self):
        environment = self.write_environment({})
        revisions = self.write_revisions({"HexAtlas": {"branch": "main"}})
        result = self.resolve(revisions, environment)
        self.assertEqual(result.returncode, 1)
        record = self.written_record(result)
        self.assertEqual(
            record["resolved"]["HexAtlas"]["status"], "unresolvable")

    def test_two_runs_never_share_a_record(self):
        checkout = self.root / "HexAtlas"
        make_git_checkout(checkout)
        environment = self.write_environment({"HexAtlas": str(checkout)})
        revisions = self.write_revisions({"HexAtlas": {"branch": "main"}})

        self.resolve(revisions, environment)
        self.resolve(revisions, environment)
        records = list((self.artifacts / "records").glob("*.json"))
        self.assertEqual(len(records), 2, records)

    def test_a_refused_manifest_writes_no_record(self):
        environment = self.write_environment({})
        bad = self.root / "bad.json"
        bad.write_text('{"schema_version": 1}', encoding="utf-8")
        result = self.resolve(bad, environment)
        self.assertEqual(result.returncode, 2)
        self.assertNotEqual(result.stderr, "")
        self.assertFalse(self.artifacts.exists())


if __name__ == "__main__":
    unittest.main()
