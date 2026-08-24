import json
import os
import pathlib
import stat
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "Tool" / "src"))

from holobike.provision import device_identity


def identity(revision=1):
    return {
        "schema_version": 1,
        "device_id": "hb-test-001",
        "product_model": "holobike-v1",
        "provisioning_revision": revision,
        "provisioned_at_utc": "2026-08-04T12:00:00Z",
        "provenance": "HolobikeDeployment",
    }


class DeviceIdentityProvisioning(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.root = pathlib.Path(self.scratch.name) / "target"
        self.root.mkdir()

    @property
    def target(self):
        return self.root / "etc/holobike/device-identity.json"

    def test_install_is_atomic_bounded_and_leaves_accounts_unchanged(self):
        passwd = self.root / "etc/passwd"
        passwd.parent.mkdir()
        passwd.parent.chmod(0o755)
        passwd.write_text("fixture:x:1000:1000::/home/fixture:/bin/false\n")

        installed = device_identity.install_identity(self.root, identity())

        self.assertEqual(installed, identity())
        self.assertEqual(device_identity.verify_identity(self.root), identity())
        self.assertEqual(stat.S_IMODE(self.target.stat().st_mode), 0o644)
        self.assertEqual(
            passwd.read_text(),
            "fixture:x:1000:1000::/home/fixture:/bin/false\n",
        )
        self.assertEqual(
            list(self.target.parent.glob(".device-identity.json.*.tmp")), [])

    def test_unknown_or_secret_shaped_fields_are_rejected(self):
        document = identity()
        document["password"] = "not-allowed"
        with self.assertRaises(device_identity.IdentityProvisioningError):
            device_identity.validate_identity(document)

    def test_duplicate_input_fields_are_rejected(self):
        source = pathlib.Path(self.scratch.name) / "identity.json"
        source.write_text(
            '{"schema_version":1,"schema_version":1}', encoding="utf-8")
        with self.assertRaises(device_identity.IdentityProvisioningError):
            device_identity.load_identity(source)

    def test_linked_input_files_are_rejected(self):
        source = pathlib.Path(self.scratch.name) / "identity.json"
        source.write_text(json.dumps(identity()), encoding="utf-8")

        symbolic_link = pathlib.Path(self.scratch.name) / "identity-link.json"
        symbolic_link.symlink_to(source)
        with self.assertRaises(device_identity.IdentityProvisioningError):
            device_identity.load_identity(symbolic_link)

        hard_link = pathlib.Path(self.scratch.name) / "identity-hardlink.json"
        os.link(source, hard_link)
        with self.assertRaises(device_identity.IdentityProvisioningError):
            device_identity.load_identity(source)

    def test_timestamp_is_canonical_and_calendar_valid(self):
        for value in (
            "2026-08-04T12:00:00.5Z",
            "2026-02-30T12:00:00Z",
            "2026-08-04T24:00:00Z",
        ):
            document = identity()
            document["provisioned_at_utc"] = value
            with self.subTest(value=value):
                with self.assertRaises(
                        device_identity.IdentityProvisioningError):
                    device_identity.validate_identity(document)

    def test_revision_is_bounded_and_pathological_json_is_refused(self):
        document = identity(device_identity.MAX_PROVISIONING_REVISION + 1)
        with self.assertRaises(device_identity.IdentityProvisioningError):
            device_identity.validate_identity(document)

        source = pathlib.Path(self.scratch.name) / "identity.json"
        source.write_text(
            '{"schema_version":1,"device_id":"hb-test-001",'
            '"product_model":"holobike-v1","provisioning_revision":' +
            "9" * 5000 +
            ',"provisioned_at_utc":"2026-08-04T12:00:00Z",'
            '"provenance":"HolobikeDeployment"}',
            encoding="utf-8",
        )
        with self.assertRaises(device_identity.IdentityProvisioningError):
            device_identity.load_identity(source)

    def test_live_root_is_never_an_install_target(self):
        with self.assertRaises(device_identity.IdentityProvisioningError):
            device_identity.install_identity(pathlib.Path("/"), identity())

    def test_intermediate_and_final_links_are_rejected(self):
        outside = pathlib.Path(self.scratch.name) / "outside"
        outside.mkdir()
        (self.root / "etc").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(
                (device_identity.IdentityProvisioningError, OSError)):
            device_identity.install_identity(self.root, identity())
        self.assertEqual(list(outside.iterdir()), [])

        (self.root / "etc").unlink()
        (self.root / "etc/holobike").mkdir(parents=True)
        sentinel = outside / "sentinel"
        sentinel.write_text("unchanged", encoding="utf-8")
        self.target.symlink_to(sentinel)
        with self.assertRaises(device_identity.IdentityProvisioningError):
            device_identity.install_identity(self.root, identity())
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "unchanged")

    def test_hardlinked_target_is_rejected(self):
        self.target.parent.mkdir(parents=True)
        source = pathlib.Path(self.scratch.name) / "linked"
        source.write_text(json.dumps(identity()), encoding="utf-8")
        os.link(source, self.target)
        with self.assertRaises(device_identity.IdentityProvisioningError):
            device_identity.install_identity(self.root, identity(2))

    def test_existing_writable_target_directory_is_rejected(self):
        target_directory = self.root / "etc/holobike"
        target_directory.mkdir(parents=True)
        target_directory.chmod(0o775)

        with self.assertRaises(device_identity.IdentityProvisioningError):
            device_identity.install_identity(self.root, identity())
        self.assertFalse(self.target.exists())

    def test_replacement_revision_must_increase(self):
        device_identity.install_identity(self.root, identity(2))
        for revision in (1, 2):
            with self.assertRaises(device_identity.IdentityProvisioningError):
                device_identity.install_identity(
                    self.root, identity(revision))
        updated = device_identity.install_identity(self.root, identity(3))
        self.assertEqual(updated["provisioning_revision"], 3)

    def test_verify_rejects_wrong_mode(self):
        device_identity.install_identity(self.root, identity())
        self.target.chmod(0o664)
        with self.assertRaises(device_identity.IdentityProvisioningError):
            device_identity.verify_identity(self.root)

    def test_verify_absent_identity_is_read_only(self):
        self.assertFalse((self.root / "etc").exists())
        with self.assertRaises(device_identity.IdentityProvisioningError):
            device_identity.verify_identity(self.root)
        self.assertFalse((self.root / "etc").exists())


if __name__ == "__main__":
    unittest.main()
