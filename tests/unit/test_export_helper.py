from pathlib import Path
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
import io
import os
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).parents[2]


@unittest.skipUnless(os.name == "posix" and hasattr(os, "geteuid") and os.geteuid() == 0,
                     "requires isolated Linux root runner; run with unittest")
class ExportHelperBoundaryTests(unittest.TestCase):
    def setUp(self):
        loader = SourceFileLoader("export_helper", str(ROOT / "appliance/files/tzmcp-export-helper"))
        self.helper = module_from_spec(spec_from_loader(loader.name, loader))
        loader.exec_module(self.helper)
        # Use a root-owned private test tree, never appliance runtime paths.
        self.base = Path(tempfile.mkdtemp(prefix="tzmcp-test-", dir="/run"))
        self.base.chmod(0o755)
        self.addCleanup(shutil.rmtree, self.base)
        self.account = SimpleNamespace(pw_uid=65534, pw_gid=65534)
        self.root = self.base / "data/export-ready"
        self.root.mkdir(parents=True)
        for directory in (self.root.parent, self.root):
            os.chown(directory, 65534, 65534)
            directory.chmod(0o700)
        self.name = "20261018T120000Z-abcdef12.zip"
        self.archive = self.root / self.name
        self.archive.write_bytes(b"guest archive")
        os.chown(self.archive, 65534, 65534)
        self.secret = self.base / "synthetic-secret"
        self.secret.write_bytes(b"synthetic root-only fixture")
        self.secret.chmod(0o600)

    def open(self, name=None):
        return self.helper.open_archive(name or self.name, self.root, self.account)

    def rejected(self):
        with self.assertRaises((OSError, ValueError)):
            self.open()
        self.assertEqual(os.geteuid(), 0)

    def test_normal_and_path_replacement_after_open(self):
        fd = self.open()
        self.archive.unlink()
        self.archive.symlink_to(self.secret)
        with os.fdopen(fd, "rb") as source:
            self.assertEqual(source.read(), b"guest archive")

    def test_parent_symlinks(self):
        for directory in (self.root, self.root.parent):
            with self.subTest(directory=directory):
                moved = directory.with_name(directory.name + "-original")
                directory.rename(moved)
                directory.symlink_to(self.base, target_is_directory=True)
                self.rejected()
                directory.unlink()
                moved.rename(directory)

    def test_leaf_symlink(self):
        self.archive.unlink()
        self.archive.symlink_to(self.secret)
        self.rejected()

    def test_root_file_hardlink(self):
        self.archive.unlink()
        os.link(self.secret, self.archive)
        self.rejected()

    def test_guest_hardlink(self):
        os.link(self.archive, self.root / "second-link")
        self.rejected()

    def test_root_owned_readable_file(self):
        os.chown(self.archive, 0, 0)
        self.archive.chmod(0o644)
        self.rejected()

    def test_special_file(self):
        self.archive.unlink()
        os.mkfifo(self.archive)
        os.chown(self.archive, 65534, 65534)
        self.rejected()

    def test_writable_directory(self):
        self.root.chmod(0o777)
        self.rejected()

    def test_filename_contract(self):
        for name in ("shadow", "../" + self.name, self.name + "\n", "x.zip", self.name.upper()):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.open(name)

    def test_replacement_during_open_cannot_read_root_file(self):
        original = os.open

        def replace(path, flags, **kwargs):
            if path == self.name:
                # Simulate replacement immediately before the file open.
                # Even after a metadata check, effective guest credentials
                # prevent opening the synthetic root-only file.
                self.assertEqual(os.geteuid(), 65534)
                os.seteuid(0)
                try:
                    self.archive.unlink()
                    os.link(self.secret, self.archive)
                finally:
                    os.seteuid(65534)
            return original(path, flags, **kwargs)

        with patch.object(self.helper.os, "open", side_effect=replace):
            self.rejected()

    def test_publication_and_no_overwrite(self):
        mount = self.base / "mount"
        with patch.object(self.helper, "MOUNT_POINT", mount), patch.object(self.helper, "command") as command:
            self.helper.publish(self.name, io.BytesIO(b"archive"))
            self.assertEqual((mount / self.name).read_bytes(), b"archive")
            with self.assertRaises(FileExistsError):
                self.helper.publish(self.name, io.BytesIO(b"overwrite"))
            self.assertEqual((mount / self.name).read_bytes(), b"archive")
            self.assertEqual(command.call_args.args[0], "/usr/bin/umount")
            self.assertEqual(command.call_count, 4)

    def test_failed_copy_cleans_up_and_unmounts(self):
        mount = self.base / "mount"
        with patch.object(self.helper, "MOUNT_POINT", mount), patch.object(self.helper, "command") as command:
            with patch.object(self.helper.shutil, "copyfileobj", side_effect=OSError("full")):
                with self.assertRaises(OSError):
                    self.helper.publish(self.name, io.BytesIO(b"archive"))
            self.assertFalse((mount / self.name).exists())
            self.assertEqual(command.call_args.args[0], "/usr/bin/umount")
            self.assertEqual(self.archive.read_bytes(), b"guest archive")

    def test_direct_invocation_rejects_bad_names_before_mount(self):
        with patch.object(self.helper.sys, "argv", ["helper", "shadow"]), \
                patch.object(self.helper, "EXPORT_ROOT", self.root), \
                patch.object(self.helper.pwd, "getpwnam", return_value=self.account), \
                patch.object(self.helper, "publish") as publish, \
                patch.object(self.helper.signal, "signal"), patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(self.helper.main(), 1)
            publish.assert_not_called()

    def test_direct_invocation_snapshots_archive(self):
        mount = self.base / "mount"
        with patch.object(self.helper.sys, "argv", ["helper", self.name]), \
                patch.object(self.helper, "EXPORT_ROOT", self.root), \
                patch.object(self.helper, "MOUNT_POINT", mount), \
                patch.object(self.helper.pwd, "getpwnam", return_value=self.account), \
                patch.object(self.helper, "command"), \
                patch.object(self.helper.signal, "signal"), patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(self.helper.main(), 0)
            self.assertEqual((mount / self.name).read_bytes(), b"guest archive")
            self.assertEqual(self.archive.read_bytes(), b"guest archive")


def test_packer_installs_export_helper_before_scrubbing():
    config = (ROOT / "appliance" / "packer" / "tzmcp.pkr.hcl").read_text(encoding="utf-8")
    assert "install-export-helper.sh" in config
