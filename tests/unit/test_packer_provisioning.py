import errno
import os
from pathlib import Path
import shutil
import subprocess
import tomllib
from unittest.mock import MagicMock, patch

import pytest
import yaml


ROOT = Path(__file__).parents[2]


def test_packer_transfers_files_before_provisioning_scripts_run():
    config = (ROOT / "appliance" / "packer" / "tzmcp.pkr.hcl").read_text(encoding="utf-8")
    assert 'destination = "/tmp/tzmcp-first-boot.service"' in config
    assert 'destination = "/tmp/tzmcp.desktop"' in config
    assert 'destination = "/tmp/tzmcp-display-mode"' in config
    assert 'destination = "/tmp/tzmcp-display-mode.desktop"' in config
    assert 'destination = "/tmp/tzmcp-finalize-image"' in config
    assert 'destination = "/tmp/tzmcp-export-helper"' in config
    assert 'destination = "/tmp/tzmcp-first-boot"' in config
    desktop = (ROOT / "appliance" / "provisioning" / "configure-desktop.sh").read_text(encoding="utf-8")
    helper = (ROOT / "appliance" / "provisioning" / "install-export-helper.sh").read_text(encoding="utf-8")
    assert "/tmp/tzmcp-first-boot" in desktop
    assert "/tmp/tzmcp-export-helper" in helper


def test_desktop_provisioning_configures_lightdm_for_tzmcp():
    script = (ROOT / "appliance" / "provisioning" / "configure-desktop.sh").read_text(encoding="utf-8")
    assert "autologin-user=tzmcp" in script
    assert "user-session=xfce" in script
    assert "systemctl enable lightdm" in script
    assert "/tmp/tzmcp-display-mode" in script
    assert "/etc/xdg/autostart/tzmcp-display-mode.desktop" in script
    assert "install -D -m 644 /tmp/tzmcp.desktop /etc/xdg/autostart/tzmcp.desktop" in script
    assert "Requires=tzmcp-first-boot.service" in script
    assert "After=tzmcp-first-boot.service" in script


def test_display_mode_autostarts_and_applies_a_known_xrandr_mode():
    script = (ROOT / "appliance" / "files" / "tzmcp-display-mode").read_text(encoding="utf-8")
    desktop = (ROOT / "appliance" / "files" / "tzmcp-display-mode.desktop").read_text(encoding="utf-8")
    assert 'xrandr --output "$output" --mode 1024x768' in script
    assert "OnlyShowIn=XFCE;" in desktop
    assert "X-GNOME-Autostart-enabled=true" in desktop


def test_base_provisioning_installs_display_server_and_greeter():
    script = (ROOT / "appliance" / "provisioning" / "install-base.sh").read_text(encoding="utf-8")
    assert "xfce4-terminal" in script
    assert "lightdm-gtk-greeter" in script
    assert "xserver-xorg-core" in script
    assert "xserver-xorg-input-libinput" in script
    assert "xserver-xorg-video-vmware" in script
    assert "python3-tk" in script
    assert "virtualbox-guest-utils" in script
    assert "virtualbox-guest-x11" in script
    for package in ("ristretto", "tumbler", "parole", "mousepad", "pulseaudio", "pavucontrol",
                    "gstreamer1.0-pulseaudio", "fonts-dejavu-core", "fonts-noto-core",
                    "gnupg", "procps", "unattended-upgrades"):
        assert package in script.split()
    assert "python3-pip" not in script.split()


def test_autoinstall_selects_minimized_server_with_direct_storage():
    data = yaml.safe_load((ROOT / "appliance/packer/ubuntu/http/user-data").read_text(encoding="utf-8"))
    assert data["autoinstall"]["source"]["id"] == "ubuntu-server-minimal"
    assert data["autoinstall"]["storage"]["layout"]["name"] == "direct"
    assert data["autoinstall"]["storage"]["swap"]["size"] == 0


def test_wheel_declares_direct_runtime_imports():
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = metadata["project"]["dependencies"]
    assert "psutil==7.0.0" in dependencies
    assert "requests==2.33.0" in dependencies


def test_packer_allocates_usable_virtualbox_video_memory():
    config = (ROOT / "appliance" / "packer" / "tzmcp.pkr.hcl").read_text(encoding="utf-8")
    assert '"--vram", "128"' in config
    assert '["modifyvm", "{{.Name}}", "--graphicscontroller", "vboxsvga"]' in config


def test_image_finalizer_removes_build_account_and_cloud_credentials():
    script = (ROOT / "appliance" / "provisioning" / "finalize-image.sh").read_text(encoding="utf-8")
    assert "userdel --remove --force tzmcp-build" in script
    assert "cloud-init.disabled" in script
    assert "rm -rf /var/lib/cloud /var/log/installer" in script
    assert "systemctl poweroff" in script


def test_image_finalizer_removes_build_account_and_cloud_credentials():
    script = (ROOT / "appliance" / "provisioning" / "finalize-image.sh").read_text(encoding="utf-8")
    assert "userdel --remove --force tzmcp-build" in script
    assert "cloud-init.disabled" in script
    assert "rm -rf /var/lib/cloud /var/log/installer" in script
    assert "systemctl poweroff" in script


def test_packer_emits_a_build_manifest():
    config = (ROOT / "appliance" / "packer" / "tzmcp.pkr.hcl").read_text(encoding="utf-8")
    assert 'post-processor "manifest"' in config
    assert "appliance-manifest.json" in config


@pytest.mark.parametrize("load_state,stop_status", [("not-found", 0), ("loaded", 0), ("loaded", 9)])
def test_finalizer_skips_missing_services_but_fails_if_present_service_cannot_stop(load_state, stop_status):
    bash = os.environ.get("TZMCP_TEST_BASH")
    if bash is None and os.name != "nt":
        bash = shutil.which("bash")
    if bash is None:
        pytest.skip("Bash is unavailable")
    script = (ROOT / "appliance/provisioning/finalize-image.sh").read_text(encoding="utf-8")
    body = script.split("stop_optional_unit() {", 1)[1].split("\n}\n", 1)[0]
    # No real systemd calls: exercise only the optional-service stop contract.
    harness = '''set -eu
systemctl() {
    if [ "$1" = show ]; then
        printf '%s\\n' "$TEST_LOAD_STATE"
    else
        printf 'STOP:%s\\n' "$2"
        return "$TEST_STOP_STATUS"
    fi
}
'''
    result = subprocess.run([bash, "-c", harness + "stop_optional_unit() {" + body
                             + "\n}\nstop_optional_unit rsyslog.service"],
                            env=dict(os.environ, TEST_LOAD_STATE=load_state,
                                     TEST_STOP_STATUS=str(stop_status)),
                            capture_output=True, text=True)
    assert result.returncode == stop_status, result.stdout + result.stderr
    assert ("STOP:rsyslog.service" in result.stdout) is (load_state != "not-found")


@pytest.mark.parametrize("error_number", [errno.ENOSPC, errno.EIO])
def test_free_space_cleanup_accepts_only_a_full_disk_and_removes_its_own_file(error_number):
    script = (ROOT / "appliance" / "provisioning" / "finalize-image.sh").read_text(encoding="utf-8")
    code = script.split("python3 - <<'PY'\n", 1)[1].split("\nPY", 1)[0]
    filler = MagicMock()
    handle = filler.open.return_value.__enter__.return_value
    handle.write.side_effect = OSError(error_number, "simulated storage failure")

    with patch("pathlib.Path", return_value=filler), patch("os.sync", create=True) as sync:
        if error_number == errno.ENOSPC:
            exec(compile(code, "<image-zero-fill>", "exec"), {})
            assert sync.call_count == 2
        else:
            with pytest.raises(OSError) as error:
                exec(compile(code, "<image-zero-fill>", "exec"), {})
            assert error.value.errno == errno.EIO
            sync.assert_called_once()
    filler.unlink.assert_called_once_with(missing_ok=True)


def test_free_space_cleanup_does_not_remove_a_preexisting_file():
    script = (ROOT / "appliance" / "provisioning" / "finalize-image.sh").read_text(encoding="utf-8")
    code = script.split("python3 - <<'PY'\n", 1)[1].split("\nPY", 1)[0]
    filler = MagicMock()
    filler.open.side_effect = FileExistsError("existing file")

    with patch("pathlib.Path", return_value=filler), patch("os.sync", create=True) as sync:
        with pytest.raises(FileExistsError):
            exec(compile(code, "<image-zero-fill>", "exec"), {})
    filler.unlink.assert_not_called()
    sync.assert_not_called()


def test_packer_resolves_guest_source_files_from_absolute_paths():
    config = (ROOT / "appliance" / "packer" / "tzmcp.pkr.hcl").read_text(encoding="utf-8")
    assert 'templatefile(abspath(' in config
    assert 'file(abspath(' in config
    assert 'script          = abspath(' in config


def test_wheel_provisioning_preserves_and_validates_the_wheel_filename():
    config = (ROOT / "appliance" / "packer" / "tzmcp.pkr.hcl").read_text(encoding="utf-8")
    script = (ROOT / "appliance" / "provisioning" / "install-tzmcp.sh").read_text(encoding="utf-8")
    assert 'destination = "/tmp/"' in config
    assert "expected exactly one wheel" in script
    assert "pip install --no-cache-dir \"$wheel_path\"" in script


def test_first_boot_uses_mitmdump_from_the_installed_venv():
    script = (ROOT / "appliance" / "provisioning" / "first-boot.sh").read_text(encoding="utf-8")
    assert "timeout 30s /opt/tzmcp/venv/bin/mitmdump" in script


@pytest.mark.parametrize("status,message,filesystem,success", [
    (0, "CHANGED: partition=3", "ext4", True),
    (1, "NOCHANGE: partition 3 is size 100", "ext4", True),
    (1, "FAILED: invalid partition", "ext4", False),
    (2, "unexpected storage error", "ext4", False),
    (0, "CHANGED: partition=3", "btrfs", False),
])
def test_first_boot_growth_handles_nochange_and_stops_on_errors(status, message, filesystem, success):
    # Windows' system32 bash.exe may be an unconfigured WSL launcher. Use an
    # explicitly selected Bash there; Linux CI exercises this without overrides.
    bash = os.environ.get("TZMCP_TEST_BASH")
    if bash is None and os.name != "nt":
        bash = shutil.which("bash")
    if bash is None:
        pytest.skip("Bash is unavailable")
    script = (ROOT / "appliance/provisioning/first-boot.sh").read_text(encoding="utf-8")
    growth = script.split("# An imported VDI", 1)[1].split("\ninstall -d", 1)[0]
    growth = "# An imported VDI" + growth
    # Every device inspection and storage command is replaced. No test reads
    # real sysfs or opens a block device, even on a privileged Linux runner.
    fixtures = '''
set -eu
function [ { if [[ "$1" == -b ]]; then return 0; fi; builtin [ "$@"; }
findmnt() { case "$*" in *SOURCE*) printf /dev/vda3;; *FSTYPE*) printf '%s' "$TEST_ROOT_TYPE";; esac; }
readlink() { printf /dev/vda3; }
cat() { printf 3; }
lsblk() { printf vda; }
growpart() { printf '%s\\n' "$TEST_GROW_MESSAGE"; return "$TEST_GROW_STATUS"; }
resize2fs() { printf 'RESIZE:%s\\n' "$*"; }
'''
    result = subprocess.run([bash, "-c", fixtures + growth], capture_output=True, text=True,
                            env=dict(os.environ, TEST_ROOT_TYPE=filesystem,
                                     TEST_GROW_STATUS=str(status), TEST_GROW_MESSAGE=message))
    assert (result.returncode == 0) is success, result.stdout + result.stderr
    assert ("RESIZE:/dev/vda3" in result.stdout) is success


def test_image_release_label_preserves_other_environment_values(tmp_path, monkeypatch):
    script = (ROOT / "appliance/provisioning/install-tzmcp.sh").read_text(encoding="utf-8")
    code = script.split("python3 - <<'PY'\n", 1)[1].split("\nPY", 1)[0]
    environment = tmp_path / "environment"
    environment.write_text('PATH="/usr/bin"\nTZMCP_APPLIANCE_VERSION=old\nOTHER=keep\n')
    monkeypatch.setenv("TZMCP_APPLIANCE_VERSION", "20261017k")

    with patch("pathlib.Path", return_value=environment):
        exec(compile(code, "<image-version>", "exec"), {})

    assert environment.read_text() == 'PATH="/usr/bin"\nOTHER=keep\nTZMCP_APPLIANCE_VERSION=20261017k\n'


@pytest.mark.parametrize("label", ["", "bad release", "bad'\nOTHER=unsafe"])
def test_image_release_label_rejects_environment_injection(tmp_path, monkeypatch, label):
    script = (ROOT / "appliance/provisioning/install-tzmcp.sh").read_text(encoding="utf-8")
    code = script.split("python3 - <<'PY'\n", 1)[1].split("\nPY", 1)[0]
    environment = tmp_path / "environment"
    environment.write_bytes(b"OTHER=keep\n")
    monkeypatch.setenv("TZMCP_APPLIANCE_VERSION", label)

    with patch("pathlib.Path", return_value=environment), pytest.raises(ValueError):
        exec(compile(code, "<image-version>", "exec"), {})

    assert environment.read_bytes() == b"OTHER=keep\n"


def test_provisioning_disables_ssh_socket_activation():
    script = (ROOT / "appliance" / "provisioning" / "configure-security.sh").read_text(encoding="utf-8")
    assert "disable --now ssh.service ssh.socket" in script
    assert "mask ssh.service ssh.socket" in script


def test_base_provisioning_installs_mozilla_firefox_without_snap_runtime():
    script = (ROOT / "appliance" / "provisioning" / "install-base.sh").read_text(encoding="utf-8")
    assert "35BAA0B33E9EB396F59CA838C0BA5CE6DC6315A3" in script
    assert "signed-by=/etc/apt/keyrings/packages.mozilla.org.asc" in script
    assert "Pin: release o=Ubuntu" in script
    assert "site=packages.mozilla.org" in script
    assert "apt-get install -y --no-install-recommends firefox" in script
    assert "apt-get purge -y snapd" in script
