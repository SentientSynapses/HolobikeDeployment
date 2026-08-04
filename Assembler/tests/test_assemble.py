"""Assemble behaviour, driven through the CLI against fabricated leaves.

The bundle is the deliverable: staged bytes, digests that match them, and
a record naming the resolution it was built from.
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


def sha256_of(path):
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AssembleBehaviour(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.scratch.name)
        self.addCleanup(self.scratch.cleanup)
        self.artifacts = self.root / "Artifacts"
        self.checkout = self.root / "checkouts" / "HexAtlas"
        self.checkout.mkdir(parents=True)

    def write_inputs(self, build_steps, artifacts):
        environment = self.root / "environment.json"
        environment.write_text(json.dumps({
            "schema_version": 1,
            "checkouts": {"HexAtlas": str(self.checkout)},
        }), encoding="utf-8")

        leaf = self.root / "Stack" / "HexAtlas"
        leaf.mkdir(parents=True, exist_ok=True)
        document = {
            "schema_version": 1,
            "integration": "HexAtlas",
            "kit": "geo_kit",
            "repository": "HexAtlas",
        }
        if build_steps is not None:
            document["entry_points"] = {
                "build": {"steps": [{"argv": step} for step in build_steps]}}
        if artifacts is not None:
            document["artifacts"] = artifacts
        (leaf / "integration.json").write_text(
            json.dumps(document), encoding="utf-8")

        profile = self.root / "bundle.json"
        profile.write_text(json.dumps({
            "schema_version": 1,
            "profile": "bundle",
            "integrations": ["HexAtlas"],
        }), encoding="utf-8")

        record = self.root / "resolve-dev-fixture.json"
        record.write_text(json.dumps({
            "schema_version": 1,
            "kind": "resolution",
            "run": {"verb": "resolve",
                    "started_at_utc": "2026-08-04T12:00:00Z",
                    "finished_at_utc": "2026-08-04T12:00:01Z"},
            "deployment": {
                "revision": "0" * 40, "dirty": False},
            "line": "dev",
            "resolved": {"HexAtlas": {
                "selected": {"branch": "main"}, "status": "resolved",
                "revision": "1" * 40, "branch": "main", "dirty": False}},
            "gates": {},
            "problems": [],
        }), encoding="utf-8")
        return profile, record, environment, self.root / "Stack"

    def assemble(self, profile, record, environment, stack):
        return run_cli(
            "assemble",
            "--profile-path", str(profile),
            "--record", str(record),
            "--environment", str(environment),
            "--stack", str(stack),
            "--artifacts", str(self.artifacts))

    def outputs_of(self, result):
        record_line = next(
            line for line in result.stdout.splitlines()
            if line.startswith("record: "))
        bundle_line = next(
            line for line in result.stdout.splitlines()
            if line.startswith("bundle: "))
        record_path = pathlib.Path(record_line[len("record: "):])
        bundle_path = pathlib.Path(bundle_line[len("bundle: "):])
        judged = run_cli("resolve", "--validate-record", str(record_path))
        self.assertEqual(judged.returncode, 0, judged.stderr)
        return json.loads(record_path.read_text(encoding="utf-8")), \
            bundle_path

    def test_a_build_stages_its_artifact_with_a_matching_digest(self):
        step = [sys.executable, "-c",
                "open('out.bin','w').write('artifact-bytes')"]
        result = self.assemble(*self.write_inputs([step], ["out.bin"]))
        self.assertEqual(result.returncode, 0, result.stderr)

        record, bundle = self.outputs_of(result)
        staged = bundle / "HexAtlas" / "out.bin"
        self.assertTrue(staged.is_file())
        entry = record["artifacts"]["HexAtlas"][0]
        self.assertEqual(entry["sha256"], sha256_of(staged))
        self.assertEqual(entry["bytes"], staged.stat().st_size)
        self.assertEqual(record["builds"]["HexAtlas"]["status"], "built")
        self.assertEqual(record["resolution"]["record"],
                         "resolve-dev-fixture.json")
        # The bundle is self-describing.
        self.assertTrue((bundle / "assembly.json").is_file())

    def test_a_failing_step_is_recorded_with_its_log_and_stops(self):
        steps = [
            [sys.executable, "-c", "print('about to fail'); "
             "raise SystemExit(3)"],
            [sys.executable, "-c", "open('never.bin','w').write('x')"],
        ]
        result = self.assemble(*self.write_inputs(steps, ["never.bin"]))
        self.assertEqual(result.returncode, 1)

        record, bundle = self.outputs_of(result)
        build = record["builds"]["HexAtlas"]
        self.assertEqual(build["status"], "failed")
        self.assertEqual(len(build["steps"]), 1)
        self.assertEqual(build["steps"][0]["exit"], 3)
        log = bundle / build["steps"][0]["log"]
        self.assertIn("about to fail", log.read_text(encoding="utf-8"))
        self.assertNotIn("HexAtlas", record["artifacts"])
        self.assertTrue(record["problems"])

    def test_a_missing_declared_artifact_is_a_problem(self):
        step = [sys.executable, "-c", "pass"]
        result = self.assemble(
            *self.write_inputs([step], ["nowhere.bin"]))
        self.assertEqual(result.returncode, 1)
        record, _ = self.outputs_of(result)
        self.assertTrue(
            any("nowhere.bin" in problem for problem in record["problems"]))

    def test_a_member_without_a_build_entry_is_skipped_loudly(self):
        result = self.assemble(*self.write_inputs(None, None))
        self.assertEqual(result.returncode, 1)
        record, _ = self.outputs_of(result)
        self.assertEqual(record["builds"]["HexAtlas"]["status"], "skipped")
        self.assertTrue(record["problems"])

    def test_assemble_refuses_a_record_that_is_not_a_resolution(self):
        profile, record, environment, stack = self.write_inputs(
            [[sys.executable, "-c", "pass"]], ["out.bin"])
        record.write_text(json.dumps({
            "schema_version": 1,
            "kind": "bootstrap",
            "run": {"verb": "bootstrap",
                    "started_at_utc": "2026-08-04T12:00:00Z",
                    "finished_at_utc": "2026-08-04T12:00:01Z"},
            "deployment": {"revision": "0" * 40, "dirty": False},
            "line": "dev",
            "actions": {"HexAtlas": {"status": "up_to_date"}},
            "problems": [],
        }), encoding="utf-8")
        result = self.assemble(profile, record, environment, stack)
        self.assertEqual(result.returncode, 2)
        self.assertIn("resolution", result.stderr)


if __name__ == "__main__":
    unittest.main()
