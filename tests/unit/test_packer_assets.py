import re
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_packer_builder_contains_appliance_security_defaults():
    config = (ROOT / "appliance" / "packer" / "tzmcp.pkr.hcl").read_text(encoding="utf-8")
    variables = (ROOT / "appliance" / "packer" / "variables.pkr.hcl").read_text(encoding="utf-8")
    assert "virtualbox-iso" in config
    assert "ubuntu-24.04.4-live-server-amd64.iso" in variables
    assert re.search(r"(?m)^[ \t]*cpus[ \t]*=[ \t]*1[ \t]*$", config)
    assert re.search(r"(?m)^[ \t]*memory[ \t]*=[ \t]*4096[ \t]*$", config)
    assert re.search(r"(?m)^[ \t]*disk_size[ \t]*=[ \t]*61440[ \t]*$", config)
    assert '"--clipboard-mode", "disabled"' in config
    assert '"--drag-and-drop", "disabled"' in config
    assert '"--usb", "off"' in config
    assert '"--vrde", "off"' in config
    assert "vboxmanage_post" in config
    assert '"--nic1", "nat"' in config
    assert "cloud-config-url=/dev/null" in config
    assert "nocloud-net\\\\;s=http" in config


def test_packer_sources_do_not_embed_build_credentials():
    for path in (ROOT / "appliance").rglob("*"):
        if path.is_file() and path.suffix in {".hcl", ".sh", ".yaml"}:
            text = path.read_text(encoding="utf-8")
            assert "password123" not in text
