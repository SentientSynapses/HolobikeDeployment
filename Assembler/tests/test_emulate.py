"""Emulate behaviour, driven through the CLI against scripted members.

The fake member is a bundle-staged script whose readiness is a file its
probe looks for — so a passing run proves substitution, spawning, probing,
settling, and teardown all at once.
"""

import hashlib
import json
import pathlib
import stat
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SHIM = REPO_ROOT / "Assembler" / "holobike"

MEMBER_SCRIPT = """\
import pathlib, signal, sys, time
state = pathlib.Path(sys.argv[1])
mode = sys.argv[2] if len(sys.argv) > 2 else "healthy"
if mode == "exit-early":
    sys.exit(3)
if mode == "stubborn":
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
if mode != "never-ready":
    (state / "up").write_text("ready")
while True:
    time.sleep(0.05)
"""

PROBE_SCRIPT = """\
import pathlib, sys
sys.exit(0 if (pathlib.Path(sys.argv[1]) / "up").exists() else 1)
"""


def run_cli(*arguments):
    return subprocess.run(
        [sys.executable, str(SHIM), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )


class EmulateBehaviour(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.scratch.name)
        self.addCleanup(self.scratch.cleanup)
        self.artifacts = self.root / "Artifacts"
        member_dir = self.artifacts / "bundles" / "bundle-test" / "HexAtlas.AtlasClient"
        member_dir.mkdir(parents=True)
        (member_dir / "member.py").write_text(
            MEMBER_SCRIPT, encoding="utf-8")
        (member_dir / "probe.py").write_text(PROBE_SCRIPT, encoding="utf-8")

    def write_inputs(self, mode="healthy", declare_serve=True):
        leaf = self.root / "Stack" / "HexAtlas"
        leaf.mkdir(parents=True, exist_ok=True)
        produced = {"destination": "device"}
        if declare_serve:
            produced["serve"] = {"argv": [
                sys.executable, "${BUNDLE}/member.py", "${STATE}", mode]}
            produced["probe"] = {"argv": [
                sys.executable, "${BUNDLE}/probe.py", "${STATE}"]}
        document = {
            "schema_version": 2,
            "integration": "HexAtlas",
            "domain": "geo",
            "repository": "HexAtlas",
            "deployables": {"AtlasClient": produced},
        }
        (leaf / "integration.json").write_text(
            json.dumps(document), encoding="utf-8")

        profiles = self.root / "Profiles"
        profiles.mkdir(exist_ok=True)
        (profiles / "bundle.json").write_text(json.dumps({
            "schema_version": 2,
            "profile": "bundle",
            "destination": "device",
            "deployables": [
                {"integration": "HexAtlas", "deployable": "AtlasClient"}],
            "topology": {"HexAtlas.AtlasClient": {"run": "host"}},
        }), encoding="utf-8")

        member = self.artifacts / "bundles/bundle-test/HexAtlas.AtlasClient/member.py"
        probe = self.artifacts / "bundles/bundle-test/HexAtlas.AtlasClient/probe.py"
        record = self.artifacts / "records" / "assemble-bundle-fixture.json"
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text(json.dumps({
            "schema_version": 2,
            "kind": "assembly",
            "run": {"verb": "assemble",
                    "started_at_utc": "2026-08-04T12:00:00Z",
                    "finished_at_utc": "2026-08-04T12:00:01Z"},
            "deployment": {"revision": "0" * 40, "dirty": False},
            "line": "dev",
            "profile": "bundle",
            "deployables": ["HexAtlas.AtlasClient"],
            "resolution": {"record": "resolve-dev-fixture.json",
                           "sha256": "1" * 64,
                           "line": "dev"},
            "builds": {"HexAtlas.AtlasClient": {"status": "built", "steps": [{
                "argv": ["fixture-build"], "exit": 0,
                "log": "logs/fixture.log"}]}},
            "artifacts": {"HexAtlas.AtlasClient": [
                {"path": "HexAtlas.AtlasClient/member.py",
                 "sha256": hashlib.sha256(member.read_bytes()).hexdigest(),
                 "bytes": member.stat().st_size},
                {"path": "HexAtlas.AtlasClient/probe.py",
                 "sha256": hashlib.sha256(probe.read_bytes()).hexdigest(),
                 "bytes": probe.stat().st_size},
            ]},
            "bundle": "bundles/bundle-test",
            "problems": [],
        }), encoding="utf-8")
        return record

    def emulate(self, record, ready_timeout="3", grace="2"):
        return run_cli(
            "build", "--only", "emulate",
            "--record", str(record),
            "--stack", str(self.root / "Stack"),
            "--profiles", str(self.root / "Profiles"),
            "--artifacts", str(self.artifacts),
            "--ready-timeout", ready_timeout,
            "--terminate-grace", grace)

    def member_of(self, result):
        prefix = "record: "
        line = next(line for line in result.stdout.splitlines()
                    if line.startswith(prefix))
        record_path = pathlib.Path(line[len(prefix):])
        judged = run_cli("check", "--validate-record", str(record_path))
        self.assertEqual(judged.returncode, 0, judged.stderr)
        record = json.loads(record_path.read_text(encoding="utf-8"))
        return record["members"]["HexAtlas.AtlasClient"], record

    def test_a_healthy_member_closes_the_provenance_chain(self):
        result = self.emulate(self.write_inputs())
        self.assertEqual(result.returncode, 0, result.stderr)
        member, record = self.member_of(result)
        self.assertEqual(member["status"], "healthy")
        self.assertGreaterEqual(member["probe"]["attempts"], 1)
        self.assertTrue(member["shutdown"]["clean"])
        # Substitution proven implicitly: the probe passed only because
        # ${STATE} resolved to a real directory the member wrote into.
        self.assertEqual(record["assembly"]["record"],
                         "assemble-bundle-fixture.json")
        self.assertEqual(len(record["assembly"]["sha256"]), 64)
        self.assertEqual(record["assembly"]["bundle"], "bundles/bundle-test")
        self.assertEqual(record["problems"], [])
        run_line = next(
            line for line in result.stdout.splitlines()
            if line.startswith("run: "))
        run_root = pathlib.Path(run_line[len("run: "):])
        for directory in (
            run_root,
            run_root / "logs",
            run_root / "members",
            run_root / "members/HexAtlas.AtlasClient",
        ):
            self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o700)
        self.assertEqual(
            stat.S_IMODE(
                (run_root / "logs/HexAtlas.AtlasClient.serve.log").stat().st_mode),
            0o600,
        )

    def test_a_member_that_never_readies_is_reaped_and_recorded(self):
        result = self.emulate(self.write_inputs(mode="never-ready"))
        self.assertEqual(result.returncode, 1)
        member, record = self.member_of(result)
        self.assertEqual(member["status"], "never_ready")
        self.assertTrue(record["problems"])
        # Teardown still happened: shutdown facts exist for the spawn.
        self.assertIn("shutdown", member)

    def test_a_member_that_exits_early_is_detected(self):
        result = self.emulate(self.write_inputs(mode="exit-early"))
        self.assertEqual(result.returncode, 1)
        member, _ = self.member_of(result)
        self.assertEqual(member["status"], "exited_early")
        self.assertIn("3", member["detail"])

    def test_a_sigterm_ignoring_member_is_killed_and_marked_unclean(self):
        result = self.emulate(self.write_inputs(mode="stubborn"))
        self.assertEqual(result.returncode, 1)
        member, _ = self.member_of(result)
        self.assertEqual(member["status"], "unclean_shutdown")
        self.assertFalse(member["shutdown"]["clean"])

    def test_a_member_without_serve_is_skipped_loudly(self):
        result = self.emulate(self.write_inputs(declare_serve=False))
        self.assertEqual(result.returncode, 1)
        member, record = self.member_of(result)
        self.assertEqual(member["status"], "skipped")
        self.assertTrue(record["problems"])

    def test_emulate_refuses_a_record_that_is_not_an_assembly(self):
        record = self.write_inputs()
        record.write_text(json.dumps({
            "schema_version": 2,
            "kind": "bootstrap",
            "run": {"verb": "bootstrap",
                    "started_at_utc": "2026-08-04T12:00:00Z",
                    "finished_at_utc": "2026-08-04T12:00:01Z"},
            "deployment": {"revision": "0" * 40, "dirty": False},
            "line": "dev",
            "actions": {"HexAtlas": {"status": "up_to_date"}},
            "problems": [],
        }), encoding="utf-8")
        result = self.emulate(record)
        self.assertEqual(result.returncode, 2)
        self.assertIn("assembly", result.stderr)

    def test_tampered_bundle_bytes_are_refused_before_spawn(self):
        record = self.write_inputs()
        (self.artifacts / "bundles/bundle-test/HexAtlas.AtlasClient/member.py").write_text(
            "raise SystemExit(99)\n", encoding="utf-8")

        result = self.emulate(record)

        self.assertEqual(result.returncode, 2)
        self.assertIn("artifact", result.stderr)
        self.assertFalse((self.artifacts / "emulations").exists())

    def test_nonfinite_timeout_is_refused_by_the_cli(self):
        result = self.emulate(self.write_inputs(), ready_timeout="nan")

        self.assertEqual(result.returncode, 2)
        self.assertIn("finite number", result.stderr)
        self.assertFalse((self.artifacts / "emulations").exists())


if __name__ == "__main__":
    unittest.main()
