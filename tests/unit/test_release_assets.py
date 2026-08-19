from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_windows_setup_verifies_before_import_and_disables_integration_features():
    script = (ROOT / "scripts" / "windows" / "Setup-tzMCP.ps1").read_text(encoding="utf-8")
    assert "Get-FileHash" in script
    assert "VBoxManage failed" in script
    assert '"--nic1", "nat"' in script
    assert '"--nic2", "none"' in script
    assert '"--clipboard-mode", "disabled"' in script
    assert '"--drag-and-drop", "disabled"' in script
    assert '"--usb", "off"' in script
    assert '"--hostpath", (Resolve-Path -LiteralPath $ExportPath).Path)' in script
    assert '${LASTEXITCODE}:' in script
    assert 'Oracle\\VirtualBox\\VBoxManage.exe' in script


def test_checksum_generator_uses_sorted_sha256_entries():
    script = (ROOT / "scripts" / "release" / "generate-checksums.py").read_text(encoding="utf-8")
    assert "hashlib.sha256" in script
    assert "sorted(entries)" in script
    assert "cannot checksum itself" in script


def test_checksum_validator_rejects_unsafe_manifest_paths():
    script = (ROOT / "scripts" / "release" / "validate-checksums.py").read_text(encoding="utf-8")
    assert "path.parent != base" in script
    assert "checksum mismatch" in script


def test_ci_validates_sources_without_building_an_ova():
    workflow = (ROOT / ".github" / "workflows" / "appliance-validation.yml").read_text(encoding="utf-8")
    assert "packer validate" in workflow
    assert "packer build" not in workflow
    assert "shellcheck" in workflow


def test_build_script_accepts_a_local_iso_for_blocked_or_offline_mirrors():
    script = (ROOT / "scripts" / "release" / "build-appliance.ps1").read_text(encoding="utf-8")
    assert "IsoPath" in script
    assert "iso_url=$resolvedIso" in script


def test_build_script_rejects_placeholder_credentials_and_invalid_hashes():
    script = (ROOT / "scripts" / "release" / "build-appliance.ps1").read_text(encoding="utf-8")
    assert "Replace the BuildPassword placeholder" in script
    assert "sha512-crypt" in script


def test_ova_packaging_requires_ovf_and_disk_and_uses_relative_tar_members():
    script = (ROOT / "scripts" / "release" / "package-ova.ps1").read_text(encoding="utf-8")
    assert "Expected exactly one OVF" in script
    assert "tar.exe -cf" in script
    assert "-C $source @members" in script
    assert "Join-Path (Get-Location).Path" in script
