"""Admission behaviour, driven through the CLI against fabricated chains.

Admission is the one writer of Releases/; these tests build clean and
dirty chains in a temp Artifacts/ and prove that only a clean one is
promoted, that a release is self-contained, and that a version is
immutable.
"""

import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

SOURCE_ROOT = pathlib.Path(__file__).resolve().parents[2]


def run_cli(shim, *arguments):
    return subprocess.run(
        [sys.executable, str(shim), *arguments],
        capture_output=True, text=True, check=False)


def _resolution(deployment_revision, *, gate_status="pass",
                selection_status="resolved",
                source_dirty=False, deployment_dirty=False):
    return {
        "schema_version": 2, "kind": "resolution",
        "run": {"verb": "resolve",
                "started_at_utc": "2026-08-04T12:00:00Z",
                "finished_at_utc": "2026-08-04T12:00:01Z"},
        "deployment": {
            "revision": deployment_revision, "dirty": deployment_dirty},
        "line": "dev",
        "resolved": {"AthleteIdentity": {
            "selected": {"branch": "main"}, "status": selection_status,
            "revision": "1" * 40, "branch": "main",
            "dirty": source_dirty}},
        "gates": {"rider-dual-copy": {
            "kind": "tree_parity", "status": gate_status,
            "counts": {"compared": 1, "only_left": 0, "only_right": 0,
                       "differing": 0},
            "mismatches": [], "truncated": 0}},
        "problems": [],
    }


def _assembly(deployment_revision, resolution_name, resolution_digest,
              artifact_digest,
              *, build_status="built", with_artifact=True):
    exit_code = 1 if build_status == "failed" else 0
    steps = [] if build_status == "skipped" else [{
        "argv": ["fixture-build"], "exit": exit_code,
        "log": "logs/fixture.log"}]
    build = {"status": build_status, "steps": steps}
    if build_status == "skipped":
        build["detail"] = "fixture skip"
    return {
        "schema_version": 2, "kind": "assembly",
        "run": {"verb": "assemble",
                "started_at_utc": "2026-08-04T12:01:00Z",
                "finished_at_utc": "2026-08-04T12:01:01Z"},
        "deployment": {"revision": deployment_revision, "dirty": False},
        "line": "dev", "profile": "services",
        "deployables": ["AthleteIdentity.IdentityClient"],
        "resolution": {"record": resolution_name,
                       "sha256": resolution_digest, "line": "dev"},
        "builds": {"AthleteIdentity.IdentityClient": build},
        "artifacts": {"AthleteIdentity.IdentityClient": (
            [{"path": "AthleteIdentity.IdentityClient/svc", "sha256": artifact_digest,
              "bytes": 10}] if with_artifact else [])},
        "bundle": "bundles/services-fixture",
        "problems": [],
    }


class AdmitBehaviour(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._deployment_temp = tempfile.TemporaryDirectory()
        cls.deployment = pathlib.Path(cls._deployment_temp.name) / "deployment"
        shutil.copytree(
            SOURCE_ROOT,
            cls.deployment,
            ignore=shutil.ignore_patterns(
                ".git", ".local", "Artifacts", "__pycache__"),
        )
        subprocess.run(
            ["git", "init", "--quiet"], cwd=cls.deployment, check=True)
        subprocess.run(
            ["git", "config", "user.name", "Assembler Tests"],
            cwd=cls.deployment, check=True)
        subprocess.run(
            ["git", "config", "user.email", "assembler-tests@invalid"],
            cwd=cls.deployment, check=True)
        subprocess.run(
            ["git", "add", "."], cwd=cls.deployment, check=True)
        subprocess.run(
            ["git", "commit", "--quiet", "-m", "test deployment"],
            cwd=cls.deployment, check=True)
        cls.shim = cls.deployment / "Assembler" / "holobike-assemble"
        cls.deployment_revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cls.deployment,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

    @classmethod
    def tearDownClass(cls):
        cls._deployment_temp.cleanup()

    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._temp.name)
        self.addCleanup(self._temp.cleanup)
        self.artifacts = self.root / "Artifacts"
        self.records = self.artifacts / "records"
        self.records.mkdir(parents=True)
        self.releases = self.root / "Releases"
        self.bundle = self.artifacts / "bundles/services-fixture"
        (self.bundle / "AthleteIdentity.IdentityClient").mkdir(parents=True)
        self.service = self.bundle / "AthleteIdentity.IdentityClient/svc"
        self.service.write_bytes(b"0123456789")
        self.artifact_digest = hashlib.sha256(
            self.service.read_bytes()).hexdigest()

    def _write(self, name, document):
        path = self.records / name
        path.write_text(json.dumps(document), encoding="utf-8")
        return path

    @staticmethod
    def _digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _chain(self, **resolution_kwargs):
        resolution_name = "resolve-dev-fixture.json"
        resolution_path = self._write(
            resolution_name,
            _resolution(self.deployment_revision, **resolution_kwargs),
        )
        assembly_name = "assemble-services-fixture.json"
        assembly_path = self._write(
            assembly_name, _assembly(
                self.deployment_revision,
                resolution_name, self._digest(resolution_path),
                self.artifact_digest))
        return assembly_path

    def admit(self, version, assembly_path, *extra, shim=None):
        return run_cli(
            shim or self.shim,
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
        self.assertEqual(
            release["chain"]["assembly"]["record"],
            "assemble-services-fixture.json")
        for kind in ("resolution", "assembly"):
            source_name = release["chain"][kind]["record"]
            source = self.records / source_name
            copied = release_dir / f"{kind}.json"
            self.assertEqual(copied.read_bytes(), source.read_bytes())
            self.assertEqual(
                release["chain"][kind]["sha256"], self._digest(copied))
        # The release record validates as a release.
        judged = run_cli(
            self.shim,
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
        path = self._write(
            resolution_name, _resolution(self.deployment_revision))
        result = self.admit("0.1.0", path)
        self.assertEqual(result.returncode, 2)
        self.assertIn("assembly record", result.stderr)

    def test_a_healthy_emulation_gates_and_is_carried(self):
        assembly_path = self._chain()
        assembly_digest = self._digest(assembly_path)
        emulation = {
            "schema_version": 2, "kind": "emulation",
            "run": {"verb": "emulate",
                    "started_at_utc": "2026-08-04T12:02:00Z",
                    "finished_at_utc": "2026-08-04T12:02:01Z"},
            "deployment": {
                "revision": self.deployment_revision, "dirty": False},
            "line": "dev", "profile": "services",
            "deployables": ["AthleteIdentity.IdentityClient"],
            "assembly": {"record": "assemble-services-fixture.json",
                         "sha256": assembly_digest,
                         "bundle": "bundles/services-fixture"},
            "members": {"AthleteIdentity.IdentityClient": {
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
            "schema_version": 2, "kind": "emulation",
            "run": {"verb": "emulate",
                    "started_at_utc": "2026-08-04T12:02:00Z",
                    "finished_at_utc": "2026-08-04T12:02:01Z"},
            "deployment": {
                "revision": self.deployment_revision, "dirty": False},
            "line": "dev", "profile": "services",
            "deployables": ["AthleteIdentity.IdentityClient"],
            "assembly": {"record": "other.json",
                         "sha256": "2" * 64,
                         "bundle": "bundles/some-other-bundle"},
            "members": {"AthleteIdentity.IdentityClient": {
                "status": "healthy", "run": "host"}},
            "problems": [],
        }
        emulation_path = self._write("emulate-other.json", emulation)
        result = self.admit("0.3.0", assembly_path,
                            "--emulation", str(emulation_path))
        self.assertEqual(result.returncode, 2)
        self.assertIn("chain does not connect", result.stderr)

    def test_dirty_source_or_deployment_state_refuses_admission(self):
        for field in ("source_dirty", "deployment_dirty"):
            with self.subTest(field=field):
                assembly = self._chain(**{field: True})
                result = self.admit(f"0.4.{int(field == 'deployment_dirty')}",
                                    assembly)
                self.assertEqual(result.returncode, 1, result.stderr)

    def test_changed_parent_record_breaks_the_digest_chain(self):
        assembly = self._chain()
        resolution = self.records / "resolve-dev-fixture.json"
        resolution.write_text(
            resolution.read_text(encoding="utf-8") + "\n", encoding="utf-8")

        result = self.admit("0.5.0", assembly)

        self.assertEqual(result.returncode, 2)
        self.assertIn("digest", result.stderr)

    def test_changed_artifact_bytes_refuse_admission(self):
        assembly = self._chain()
        self.service.write_bytes(b"tampered!!")

        result = self.admit("0.6.0", assembly)

        self.assertEqual(result.returncode, 1)
        self.assertIn("digest", result.stdout)

    def test_admission_requires_the_current_deployment_to_remain_clean(self):
        assembly = self._chain()
        marker = self.deployment / "untracked-during-admission"
        marker.write_text("dirty", encoding="utf-8")
        try:
            result = self.admit("0.7.0", assembly)
        finally:
            marker.unlink()

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("currently dirty", result.stdout)
        self.assertFalse((self.releases / "0.7.0").exists())

    def test_admission_requires_the_chain_deployment_revision(self):
        assembly = self._chain()
        drifted = self.root / "drifted-deployment"
        shutil.copytree(self.deployment, drifted)
        subprocess.run(
            ["git", "commit", "--quiet", "--allow-empty", "-m", "drift"],
            cwd=drifted,
            check=True,
        )

        result = self.admit(
            "0.8.0",
            assembly,
            shim=drifted / "Assembler" / "holobike-assemble",
        )

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("differs from the lifecycle chain", result.stdout)
        self.assertFalse((self.releases / "0.8.0").exists())


if __name__ == "__main__":
    unittest.main()
