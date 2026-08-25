"""The `provision` verb, driven through the CLI against fabricated declarations.

`provision` takes a profile (D-23). `device` runs the device-identity
primitive, which has its own suite; these tests are about the verb's contract:
a server profile is refused by naming what each of its deployables can and
cannot do, an unknown or unresolvable profile is refused before anything is
touched, and a device profile with nothing to do says so.
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


class ProvisionBehaviour(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.root = pathlib.Path(self.scratch.name)
        self.stack = self.root / "Stack"
        self.profiles = self.root / "Profiles"
        (self.stack / "geo").mkdir(parents=True)
        (self.stack / "ai").mkdir()
        self.profiles.mkdir()
        (self.stack / "nonmembers.json").write_text(json.dumps(
            {"schema_version": 1, "nonmembers": {}}), encoding="utf-8")
        self.leaf("geo", "HexAtlas", {
            "AtlasClient": {"destination": "device"},
            "AtlasServer": {
                "destination": "server",
                "build": {"steps": [{"argv": ["true"]}]},
                "artifacts": ["Builds/bin/HexAtlasServer"]}})
        self.leaf("ai", "drAIs", {
            "DraisClient": {"destination": "device"},
            "DraisServer": {"destination": "server"}})

    def leaf(self, domain, name, deployables):
        (self.stack / domain / f"{name}.json").write_text(json.dumps({
            "schema_version": 2, "integration": name, "domain": domain,
            "repository": name, "deployables": deployables}),
            encoding="utf-8")

    def profile(self, name, destination, *pairs):
        (self.profiles / f"{name}.json").write_text(json.dumps({
            "schema_version": 2, "profile": name,
            "destination": destination,
            "deployables": [{"integration": i, "deployable": d}
                            for i, d in pairs]}), encoding="utf-8")

    def provision(self, *arguments):
        return run_cli(
            "provision", *arguments,
            "--stack", str(self.stack), "--profiles", str(self.profiles))

    def test_server_profile_is_refused_by_naming_each_deployable(self):
        self.profile("estate", "server",
                     ("HexAtlas", "AtlasServer"), ("drAIs", "DraisServer"))
        result = self.provision("estate")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("provisioning estate is refused", result.stderr)
        self.assertIn("HexAtlas.AtlasServer: builds to bytes here, "
                      "and declares no way to place them", result.stderr)
        self.assertIn("drAIs.DraisServer: declares no build here",
                      result.stderr)
        # The reason is the leaf's to give, so the refusal points at it.
        self.assertIn("Stack/geo/HexAtlas.md", result.stderr)
        self.assertIn("Stack/ai/drAIs.md", result.stderr)

    def test_unknown_profile_is_refused(self):
        result = self.provision("nowhere")
        self.assertEqual(result.returncode, 2)
        self.assertIn("nowhere", result.stderr)
        self.assertIn("no profile", result.stderr)

    def test_unresolvable_selection_is_refused_before_anything_runs(self):
        # A device deployable in a server profile: caught by the same
        # cross-document check `build` uses, not by a failure somewhere later.
        self.profile("mixed", "server", ("HexAtlas", "AtlasClient"))
        result = self.provision("mixed")
        self.assertEqual(result.returncode, 2)
        self.assertIn("HexAtlas.AtlasClient", result.stderr)

    def test_device_profile_with_nothing_to_do_says_so(self):
        self.profile("device", "device", ("HexAtlas", "AtlasClient"))
        result = self.provision("device")
        self.assertEqual(result.returncode, 2)
        self.assertIn("nothing to provision", result.stderr)


if __name__ == "__main__":
    unittest.main()
