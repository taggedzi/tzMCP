from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_first_boot_provisioning_has_required_security_guards():
    script = (ROOT / "appliance" / "provisioning" / "first-boot.sh").read_text(encoding="utf-8")
    assert "runuser -u" in script
    assert "127.0.0.1" in script
    assert "chmod 600" in script
    assert "rm -f -- \"$CERT\" \"$KEY\"" in script
    assert "timeout 30s" in script


def test_desktop_launcher_enables_appliance_mode_without_host_integration():
    desktop = (ROOT / "appliance" / "files" / "tzmcp.desktop").read_text(encoding="utf-8")
    assert "TZMCP_APPLIANCE=1" in desktop
    assert "TZMCP_DATA_DIR=/var/lib/tzmcp" in desktop
    assert "Terminal=false" in desktop
