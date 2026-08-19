from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_packer_transfers_files_before_provisioning_scripts_run():
    config = (ROOT / "appliance" / "packer" / "tzmcp.pkr.hcl").read_text(encoding="utf-8")
    assert 'destination = "/tmp/tzmcp-first-boot.service"' in config
    assert 'destination = "/tmp/tzmcp.desktop"' in config
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


def test_packer_allocates_usable_virtualbox_video_memory():
    config = (ROOT / "appliance" / "packer" / "tzmcp.pkr.hcl").read_text(encoding="utf-8")
    assert '"--vram", "128"' in config


def test_packer_emits_a_build_manifest():
    config = (ROOT / "appliance" / "packer" / "tzmcp.pkr.hcl").read_text(encoding="utf-8")
    assert 'post-processor "manifest"' in config
    assert "appliance-manifest.json" in config


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


def test_base_provisioning_installs_firefox_outside_the_apt_transaction():
    script = (ROOT / "appliance" / "provisioning" / "install-base.sh").read_text(encoding="utf-8")
    apt_line = script.split("apt-get install", 1)[1].split("\n", 4)[0]
    assert "firefox" not in apt_line
    assert "snapd" in script
    assert "snap install firefox" in script
    assert "Firefox snap installation failed" in script
