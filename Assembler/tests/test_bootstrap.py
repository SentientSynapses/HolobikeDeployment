"""Bootstrap behaviour, driven through the CLI against local-path origins.

The mutation boundary is the whole test: clone missing, fast-forward
clean-on-branch, and prove that dirty trees, wrong branches, and diverged
histories are reported untouched.
"""

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SHIM = REPO_ROOT / "Assembler" / "holobike-assemble"


def run_cli(*arguments):
    return subprocess.run(
        [sys.executable, str(SHIM), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )


def git(cwd, *arguments):
    return subprocess.run(
        ["git", "-C", str(cwd), *arguments],
        capture_output=True, text=True, check=True).stdout.strip()


def make_origin(path):
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "--quiet", "--initial-branch=main"],
                   cwd=path, check=True, capture_output=True)
    for key, value in (("user.email", "bootstrap@test.invalid"),
                       ("user.name", "Bootstrap Test")):
        subprocess.run(["git", "config", key, value],
                       cwd=path, check=True, capture_output=True)
    (path / "file.txt").write_text("one\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=path, check=True,
                   capture_output=True)
    subprocess.run(["git", "commit", "--quiet", "-m", "one"],
                   cwd=path, check=True, capture_output=True)
    return path


def advance_origin(path):
    (path / "file.txt").write_text("two\n", encoding="utf-8")
    subprocess.run(["git", "commit", "--quiet", "-am", "two"],
                   cwd=path, check=True, capture_output=True)
    return git(path, "rev-parse", "HEAD")


class BootstrapBehaviour(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.scratch.name)
        self.addCleanup(self.scratch.cleanup)
        self.artifacts = self.root / "Artifacts"
        self.origin = make_origin(self.root / "origins" / "HexAtlas")

    def write_stack(self, origin=None):
        leaf = self.root / "Stack" / "HexAtlas"
        leaf.mkdir(parents=True, exist_ok=True)
        document = {
            "schema_version": 1,
            "integration": "HexAtlas",
            "domain": "geo",
            "repository": "HexAtlas",
        }
        if origin is not None:
            document["origin"] = origin
        (leaf / "integration.json").write_text(
            json.dumps(document), encoding="utf-8")
        return self.root / "Stack"

    def write_inputs(self, checkout, origin=None):
        environment = self.root / "environment.json"
        environment.write_text(json.dumps({
            "schema_version": 1,
            "checkouts": {"HexAtlas": str(checkout)},
        }), encoding="utf-8")
        revisions = self.root / "dev.json"
        revisions.write_text(json.dumps({
            "schema_version": 1,
            "line": "dev",
            "selections": {"HexAtlas": {"branch": "main"}},
        }), encoding="utf-8")
        stack = self.write_stack(origin)
        return environment, revisions, stack

    def bootstrap(self, environment, revisions, stack):
        return run_cli(
            "bootstrap",
            "--revisions", str(revisions),
            "--environment", str(environment),
            "--stack", str(stack),
            "--artifacts", str(self.artifacts))

    def action_of(self, result):
        prefix = "record: "
        line = next(line for line in result.stdout.splitlines()
                    if line.startswith(prefix))
        record_path = pathlib.Path(line[len(prefix):])
        judged = run_cli("resolve", "--validate-record", str(record_path))
        self.assertEqual(judged.returncode, 0, judged.stderr)
        record = json.loads(record_path.read_text(encoding="utf-8"))
        return record["actions"]["HexAtlas"], record

    def test_a_missing_checkout_is_cloned_from_its_declared_origin(self):
        checkout = self.root / "checkouts" / "HexAtlas"
        result = self.bootstrap(
            *self.write_inputs(checkout, origin=str(self.origin)))
        self.assertEqual(result.returncode, 0, result.stderr)
        action, _ = self.action_of(result)
        self.assertEqual(action["status"], "cloned")
        self.assertTrue((checkout / "file.txt").is_file())
        self.assertEqual(git(checkout, "rev-parse", "--abbrev-ref", "HEAD"),
                         "main")

    def test_a_missing_checkout_without_origin_is_unclonable(self):
        checkout = self.root / "checkouts" / "HexAtlas"
        result = self.bootstrap(*self.write_inputs(checkout, origin=None))
        self.assertEqual(result.returncode, 1)
        action, record = self.action_of(result)
        self.assertEqual(action["status"], "unclonable")
        self.assertTrue(record["problems"])
        self.assertFalse(checkout.exists())

    def test_a_clean_on_branch_checkout_fast_forwards(self):
        checkout = self.root / "checkouts" / "HexAtlas"
        self.bootstrap(*self.write_inputs(checkout, origin=str(self.origin)))
        new_head = advance_origin(self.origin)

        result = self.bootstrap(
            *self.write_inputs(checkout, origin=str(self.origin)))
        self.assertEqual(result.returncode, 0, result.stderr)
        action, _ = self.action_of(result)
        self.assertEqual(action["status"], "updated")
        self.assertEqual(action["revision_after"], new_head)
        self.assertEqual(git(checkout, "rev-parse", "HEAD"), new_head)

    def test_an_up_to_date_checkout_is_left_exactly_alone(self):
        checkout = self.root / "checkouts" / "HexAtlas"
        inputs = self.write_inputs(checkout, origin=str(self.origin))
        self.bootstrap(*inputs)
        before = git(checkout, "rev-parse", "HEAD")

        result = self.bootstrap(*inputs)
        self.assertEqual(result.returncode, 0)
        action, _ = self.action_of(result)
        self.assertEqual(action["status"], "up_to_date")
        self.assertEqual(git(checkout, "rev-parse", "HEAD"), before)

    def test_a_dirty_tree_is_reported_and_never_touched(self):
        checkout = self.root / "checkouts" / "HexAtlas"
        inputs = self.write_inputs(checkout, origin=str(self.origin))
        self.bootstrap(*inputs)
        (checkout / "file.txt").write_text("uncommitted\n", encoding="utf-8")
        advance_origin(self.origin)

        result = self.bootstrap(*inputs)
        self.assertEqual(result.returncode, 1)
        action, record = self.action_of(result)
        self.assertEqual(action["status"], "dirty_skipped")
        self.assertEqual((checkout / "file.txt").read_text(encoding="utf-8"),
                         "uncommitted\n")
        self.assertTrue(record["problems"])

    def test_a_wrong_branch_is_reported_and_never_switched(self):
        checkout = self.root / "checkouts" / "HexAtlas"
        inputs = self.write_inputs(checkout, origin=str(self.origin))
        self.bootstrap(*inputs)
        subprocess.run(["git", "checkout", "-b", "feature", "--quiet"],
                       cwd=checkout, check=True, capture_output=True)

        result = self.bootstrap(*inputs)
        self.assertEqual(result.returncode, 1)
        action, _ = self.action_of(result)
        self.assertEqual(action["status"], "selection_mismatch")
        self.assertEqual(git(checkout, "rev-parse", "--abbrev-ref", "HEAD"),
                         "feature")

    def test_a_diverged_history_is_reported_and_never_reset(self):
        checkout = self.root / "checkouts" / "HexAtlas"
        inputs = self.write_inputs(checkout, origin=str(self.origin))
        self.bootstrap(*inputs)
        # Local commit the origin never saw, plus origin movement: ff is
        # impossible and bootstrap must leave the local commit standing.
        (checkout / "local.txt").write_text("local\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=checkout, check=True,
                       capture_output=True)
        subprocess.run(["git", "commit", "--quiet", "-m", "local"],
                       cwd=checkout, check=True, capture_output=True)
        local_head = git(checkout, "rev-parse", "HEAD")
        advance_origin(self.origin)

        result = self.bootstrap(*inputs)
        self.assertEqual(result.returncode, 1)
        action, _ = self.action_of(result)
        self.assertEqual(action["status"], "diverged")
        self.assertEqual(git(checkout, "rev-parse", "HEAD"), local_head)


if __name__ == "__main__":
    unittest.main()
