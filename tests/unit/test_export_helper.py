from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_export_helper_has_fixed_mount_and_safe_copy_boundary():
    script = (ROOT / "appliance" / "files" / "tzmcp-export-helper").read_text(encoding="utf-8")
    assert "SHARE_NAME=tzmcp-export" in script
    assert "MOUNT_POINT=/run/tzmcp-export" in script
    assert "nosuid,nodev,noexec" in script
    assert "realpath -e" in script
    assert "[ ! -L \"$source\" ]" in script
    assert "partial=\"$destination.partial\"" in script
    assert "trap cleanup" in script


def test_packer_installs_export_helper_before_scrubbing():
    config = (ROOT / "appliance" / "packer" / "tzmcp.pkr.hcl").read_text(encoding="utf-8")
    assert "install-export-helper.sh" in config
