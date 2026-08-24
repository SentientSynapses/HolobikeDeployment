"""Gate behaviour, driven through the CLI against fabricated dual copies.

The proof discipline is the house's: build parity, watch the gate pass;
break parity by one byte, watch it fail and say where; break it somewhere
excluded, watch it stay silent.
"""

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SHIM = REPO_ROOT / "Assembler" / "holobike"


def run_cli(*arguments):
    return subprocess.run(
        [sys.executable, str(SHIM), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )


def make_git_checkout(path):
    path.mkdir(parents=True)
    for command in (
        ["git", "init", "--quiet", "--initial-branch=main"],
        ["git", "config", "user.email", "gates@test.invalid"],
        ["git", "config", "user.name", "Gates Test"],
        ["git", "commit", "--quiet", "--allow-empty",
         "--message", "fixture"],
    ):
        subprocess.run(command, cwd=path, check=True, capture_output=True)


class GateBehaviour(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.scratch.name)
        self.addCleanup(self.scratch.cleanup)
        self.artifacts = self.root / "Artifacts"

        # Two checkouts, each carrying a copy of the same plugin tree.
        self.left = self.root / "HolobikeRider"
        self.right = self.root / "HolobikeExperience"
        make_git_checkout(self.left)
        make_git_checkout(self.right)
        for base, plugin_root in (
                (self.left, "Plugin"),
                (self.right, "Mounted/Plugin")):
            source = base / plugin_root / "Source"
            source.mkdir(parents=True)
            (source / "Module.cpp").write_text(
                "int main() { return 0; }\n", encoding="utf-8")
            (source / "Module.h").write_text(
                "#pragma once\n", encoding="utf-8")
            binaries = base / plugin_root / "Binaries"
            binaries.mkdir()
            (binaries / "junk.so").write_text(base.name, encoding="utf-8")

    def write_inputs(self):
        environment = self.root / "environment.json"
        environment.write_text(json.dumps({
            "schema_version": 1,
            "checkouts": {
                "HolobikeRider": str(self.left),
                "HolobikeExperience": str(self.right),
            },
        }), encoding="utf-8")
        revisions = self.root / "dev.json"
        revisions.write_text(json.dumps({
            "schema_version": 1,
            "line": "dev",
            "selections": {"HolobikeRider": {"branch": "main"}},
        }), encoding="utf-8")
        policy_dir = self.root / "Policy"
        policy_dir.mkdir(exist_ok=True)
        (policy_dir / "parity.json").write_text(json.dumps({
            "schema_version": 1,
            "policy": "parity",
            "gates": [{
                "name": "rider-dual-copy",
                "kind": "tree_parity",
                "left": {"integration": "HolobikeRider", "path": "Plugin"},
                "right": {"integration": "HolobikeExperience",
                          "path": "Mounted/Plugin"},
                "exclude": ["Binaries"],
            }],
        }), encoding="utf-8")
        return environment, revisions, policy_dir

    def resolve(self, environment, revisions, policy_dir):
        return run_cli(
            "build", "--only", "resolve",
            "--revisions", str(revisions),
            "--environment", str(environment),
            "--artifacts", str(self.artifacts),
            "--policy", str(policy_dir))

    def record_of(self, result):
        prefix = "record: "
        line = next(line for line in result.stdout.splitlines()
                    if line.startswith(prefix))
        record_path = pathlib.Path(line[len(prefix):])
        judged = run_cli("check", "--validate-record", str(record_path))
        self.assertEqual(judged.returncode, 0, judged.stderr)
        return json.loads(record_path.read_text(encoding="utf-8"))

    def test_matching_copies_pass_and_the_verdict_rides_the_record(self):
        result = self.resolve(*self.write_inputs())
        self.assertEqual(result.returncode, 0, result.stderr)
        record = self.record_of(result)
        verdict = record["gates"]["rider-dual-copy"]
        self.assertEqual(verdict["status"], "pass")
        self.assertEqual(verdict["counts"]["differing"], 0)
        self.assertEqual(record["problems"], [])

    def test_one_mutated_byte_fails_the_gate_and_names_the_file(self):
        inputs = self.write_inputs()
        mounted = self.right / "Mounted/Plugin/Source/Module.cpp"
        mounted.write_text(
            "int main() { return 1; }\n", encoding="utf-8")

        result = self.resolve(*inputs)
        self.assertEqual(result.returncode, 1)
        record = self.record_of(result)
        verdict = record["gates"]["rider-dual-copy"]
        self.assertEqual(verdict["status"], "fail")
        self.assertIn("differs: Source/Module.cpp", verdict["mismatches"])
        self.assertTrue(
            any("rider-dual-copy" in problem
                for problem in record["problems"]))

    def test_a_file_present_on_one_side_only_is_named(self):
        inputs = self.write_inputs()
        extra = self.right / "Mounted/Plugin/Source/Extra.cpp"
        extra.write_text("// mounted only\n", encoding="utf-8")

        result = self.resolve(*inputs)
        self.assertEqual(result.returncode, 1)
        verdict = self.record_of(result)["gates"]["rider-dual-copy"]
        self.assertEqual(verdict["counts"]["only_right"], 1)
        self.assertIn("only right: Source/Extra.cpp", verdict["mismatches"])

    def test_excluded_components_never_fail_a_gate(self):
        inputs = self.write_inputs()
        junk = self.right / "Mounted/Plugin/Binaries/junk.so"
        junk.write_text("rebuilt, deliberately different", encoding="utf-8")

        result = self.resolve(*inputs)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_a_linked_mount_is_parity_by_construction(self):
        inputs = self.write_inputs()
        mounted = self.right / "Mounted/Plugin"
        shutil.rmtree(mounted)
        mounted.symlink_to(self.left / "Plugin", target_is_directory=True)

        result = self.resolve(*inputs)
        self.assertEqual(result.returncode, 0, result.stderr)
        record = self.record_of(result)
        verdict = record["gates"]["rider-dual-copy"]
        self.assertEqual(verdict["status"], "linked")
        self.assertEqual(
            verdict["target"], str((self.left / "Plugin").resolve()))
        self.assertEqual(record["problems"], [])

    def test_a_link_to_somewhere_else_is_still_compared(self):
        # "It's a link" is not the fact; "both sites are the same tree"
        # is. A mount linked to the wrong place must be compared like any
        # copy, not waved through.
        inputs = self.write_inputs()
        elsewhere = self.root / "Elsewhere/Plugin"
        (elsewhere / "Source").mkdir(parents=True)
        (elsewhere / "Source/Module.cpp").write_text(
            "int main() { return 2; }\n", encoding="utf-8")
        mounted = self.right / "Mounted/Plugin"
        shutil.rmtree(mounted)
        mounted.symlink_to(elsewhere, target_is_directory=True)

        result = self.resolve(*inputs)
        self.assertEqual(result.returncode, 1)
        verdict = self.record_of(result)["gates"]["rider-dual-copy"]
        self.assertEqual(verdict["status"], "fail")
        self.assertIn("differs: Source/Module.cpp", verdict["mismatches"])
        self.assertEqual(verdict["counts"]["only_left"], 1)

    def test_an_unevaluable_gate_is_skipped_and_that_is_a_problem(self):
        environment, revisions, policy_dir = self.write_inputs()
        environment.write_text(json.dumps({
            "schema_version": 1,
            "checkouts": {"HolobikeRider": str(self.left)},
        }), encoding="utf-8")

        result = self.resolve(environment, revisions, policy_dir)
        self.assertEqual(result.returncode, 1)
        record = self.record_of(result)
        verdict = record["gates"]["rider-dual-copy"]
        self.assertEqual(verdict["status"], "skipped")
        self.assertTrue(
            any("skipped" in problem for problem in record["problems"]))


if __name__ == "__main__":
    unittest.main()
