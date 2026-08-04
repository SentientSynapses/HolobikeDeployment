"""Admission behaviour, driven through the CLI against fabricated chains.

Admission is the one writer of Releases/; these tests build clean and
dirty chains in a temp Artifacts/ and prove that only a clean one is
promoted, that a release is self-contained, and that a version is
immutable.
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
        capture_output=True, text=True, check=False)


def _resolution(name, *, gate_status="pass", selection_status="resolved"):
    return {
        "schema_version": 1, "kind": "resolution",
        "run": {"verb": "resolve",
                "started_at_utc": "2026-08-04T12:00:00Z",
                "finished_at_utc": "2026-08-04T12:00:01Z"},
        "deployment": {"revision": "0" * 40, "dirty": False},
        "line": "dev",
        "resolved": {"AthleteIdentity": {
            "selected": {"branch": "main"}, "status": selection_status,
            "revision": "1" * 40, "branch": "main", "dirty": False}},
        "gates": {"rider-dual-copy": {
            "kind": "tree_parity", "status": gate_status,
            "counts": {"compared": 1, "only_left": 0, "only_right": 0,
                       "differing": 0},
            "mismatches": [], "truncated": 0}},
        "problems": [],
    }


def _assembly(resolution_name, *, build_status="built", with_artifact=True):
    return {
        "schema_version": 1, "kind": "assembly",
        "run": {"verb": "assemble",
                "started_at_utc": "2026-08-04T12:01:00Z",
                "finished_at_utc": "2026-08-04T12:01:01Z"},
        "deployment": {"revision": "0" * 40, "dirty": False},
        "line": "dev", "profile": "services",
        "resolution": {"record": resolution_name, "line": "dev"},
        "builds": {"AthleteIdentity": {"status": build_status, "steps": []}},
        "artifacts": {"AthleteIdentity": (
            [{"path": "AthleteIdentity/svc", "sha256": "a" * 64,
              "bytes": 10}] if with_artifact else [])},
        "bundle": "bundles/services-fixture",
        "problems": [],
    }


class AdmitBehaviour(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._temp.name)
        self.addCleanup(self._temp.cleanup)
        self.artifacts = self.root / "Artifacts"
        self.records = self.artifacts / "records"
        self.records.mkdir(parents=True)
        self.releases = self.root / "Releases"

    def _write(self, name, document):
        path = self.records / name
        path.write_text(json.dumps(document), encoding="utf-8")
        return path

    def _chain(self, **resolution_kwargs):
        resolution_name = "resolve-dev-fixture.json"
        self._write(resolution_name, _resolution(
            resolution_name, **resolution_kwargs))
        assembly_name = "assemble-services-fixture.json"
        assembly_path = self._write(
            assembly_name, _assembly(resolution_name))
        return assembly_path

    def admit(self, version, assembly_path, *extra):
        return run_cli(
            "admit", "--version", version,
            "--record", str(assembly_path),
            "--artifacts", str(self.artifacts),
            "--releases", str(self.releases), *extra)

    def test_a_clean_chain_is_admitted_and_self_contained(self):
        result = self.admit("0.1.0", self._chain())
        self.assertEqual(result.returncode, 0, result.stderr)
        release_dir = self.releases / "0.1.0"
        self.assertTrue((release_dir / "release.json").is_file())
        self.assertTrue((release_dir / "resolution.json").is_file())
        self.assertTrue((release_dir / "assembly.json").is_file())
        release = json.loads(
            (release_dir / "release.json").read_text(encoding="utf-8"))
        self.assertEqual(release["attestation"]["emulation"], "absent")
        self.assertIsNone(release["chain"]["emulation"])
        # The release record validates as a release.
        judged = run_cli(
            "resolve", "--validate-record", str(release_dir / "release.json"))
        self.assertEqual(judged.returncode, 0, judged.stderr)

    def test_a_failing_gate_refuses_admission(self):
        result = self.admit("0.1.0", self._chain(gate_status="fail"))
        self.assertEqual(result.returncode, 1)
        self.assertFalse((self.releases / "0.1.0").exists())
        self.assertTrue(any("gate" in line
                            for line in result.stdout.splitlines()))
        # The refusal is still recorded as a decision.
        decisions = list(self.records.glob("admit-0.1.0-*.json"))
        self.assertEqual(len(decisions), 1)
        decision = json.loads(decisions[0].read_text(encoding="utf-8"))
        self.assertFalse(decision["admitted"])

    def test_an_unresolved_selection_refuses(self):
        result = self.admit(
            "0.1.0", self._chain(selection_status="selection_mismatch"))
        self.assertEqual(result.returncode, 1)
        self.assertFalse((self.releases / "0.1.0").exists())

    def test_a_version_is_immutable(self):
        self.admit("0.1.0", self._chain())
        result = self.admit("0.1.0", self._chain())
        self.assertEqual(result.returncode, 2)
        self.assertIn("immutable", result.stderr)

    def test_a_bad_version_is_refused_before_any_work(self):
        result = self.admit("0.1.0/../etc", self._chain())
        self.assertEqual(result.returncode, 2)

    def test_a_non_assembly_record_is_refused(self):
        resolution_name = "resolve-dev-fixture.json"
        path = self._write(resolution_name, _resolution(resolution_name))
        result = self.admit("0.1.0", path)
        self.assertEqual(result.returncode, 2)
        self.assertIn("assembly record", result.stderr)

    def test_a_healthy_emulation_gates_and_is_carried(self):
        assembly_path = self._chain()
        emulation = {
            "schema_version": 1, "kind": "emulation",
            "run": {"verb": "emulate",
                    "started_at_utc": "2026-08-04T12:02:00Z",
                    "finished_at_utc": "2026-08-04T12:02:01Z"},
            "deployment": {"revision": "0" * 40, "dirty": False},
            "line": "dev", "profile": "services",
            "assembly": {"record": "assemble-services-fixture.json",
                         "bundle": "bundles/services-fixture"},
            "members": {"AthleteIdentity": {
                "status": "healthy", "run": "host"}},
            "problems": [],
        }
        emulation_path = self._write("emulate-services-fixture.json",
                                     emulation)
        result = self.admit("0.2.0", assembly_path,
                            "--emulation", str(emulation_path))
        self.assertEqual(result.returncode, 0, result.stderr)
        release = json.loads(
            (self.releases / "0.2.0" / "release.json")
            .read_text(encoding="utf-8"))
        self.assertEqual(release["attestation"]["emulation"], "healthy")
        self.assertTrue(
            (self.releases / "0.2.0" / "emulation.json").is_file())

    def test_an_emulation_of_a_different_bundle_is_refused(self):
        assembly_path = self._chain()
        emulation = {
            "schema_version": 1, "kind": "emulation",
            "run": {"verb": "emulate",
                    "started_at_utc": "2026-08-04T12:02:00Z",
                    "finished_at_utc": "2026-08-04T12:02:01Z"},
            "deployment": {"revision": "0" * 40, "dirty": False},
            "line": "dev", "profile": "services",
            "assembly": {"record": "other.json",
                         "bundle": "bundles/some-other-bundle"},
            "members": {"AthleteIdentity": {
                "status": "healthy", "run": "host"}},
            "problems": [],
        }
        emulation_path = self._write("emulate-other.json", emulation)
        result = self.admit("0.3.0", assembly_path,
                            "--emulation", str(emulation_path))
        self.assertEqual(result.returncode, 2)
        self.assertIn("chain does not connect", result.stderr)


if __name__ == "__main__":
    unittest.main()
