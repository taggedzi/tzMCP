import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

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
    assert '"--vrde", "off"' in script
    assert '"--vram", "128"' in script
    assert '"--graphicscontroller", "vboxsvga"' in script
    assert '"--hostpath", (Resolve-Path -LiteralPath $ExportPath).Path)' in script
    assert '[int]$Cpu = 1' in script
    assert '${LASTEXITCODE}:' in script
    assert 'Oracle\\VirtualBox\\VBoxManage.exe' in script
    assert '$importArguments += @("--basefolder", $resolvedBaseFolder)' in script


def test_checksum_generator_uses_sorted_sha256_entries():
    script = (ROOT / "scripts" / "release" / "generate-checksums.py").read_text(encoding="utf-8")
    assert "hashlib.sha256" in script
    assert "sorted(entries)" in script
    assert "cannot checksum itself" in script


@pytest.mark.skipif(os.name != "nt", reason="Standard VirtualBox installation paths are Windows-only")
def test_setup_finds_one_standard_installation_without_path(tmp_path):
    shells = [os.environ.get("TZMCP_TEST_POWERSHELL") or shutil.which("pwsh")]
    if os.name == "nt":
        shells.append(shutil.which("powershell"))
    shells = list(dict.fromkeys(shell for shell in shells if shell))
    if not shells:
        pytest.skip("PowerShell is unavailable")
    setup = str(ROOT / "scripts/windows/Setup-tzMCP.ps1").replace("'", "''")
    command = rf'''
$ErrorActionPreference = 'Stop'
$tokens = $null; $parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile('{setup}', [ref]$tokens, [ref]$parseErrors)
$function = $ast.Find({{param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Get-VBoxManage'}}, $true)
. ([scriptblock]::Create($function.Extent.Text))
$expected = Join-Path ([Environment]::GetFolderPath('ProgramFiles')) 'Oracle\VirtualBox\VBoxManage.exe'
function Get-Command {{ [CmdletBinding()] param([string]$Name) return $null }}
function Test-Path {{ param([string]$LiteralPath, [string]$PathType) return $LiteralPath -eq $expected }}
$actual = Get-VBoxManage
if ($actual -isnot [string] -or $actual -ne $expected) {{ throw "Truncated installation path: $actual" }}
'ok'
'''
    for shell in shells:
        result = subprocess.run([shell, "-NoProfile", "-NonInteractive", "-Command", command],
                                cwd=tmp_path, capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("size,bad_nic", [
    (None, False), (10240, False), (20480, False), (5120, False), (10240, True),
])
def test_setup_disk_override_resizes_before_boot_and_rejects_shrinking(tmp_path, size, bad_nic):
    powershell = os.environ.get("TZMCP_TEST_POWERSHELL") or shutil.which("pwsh")
    if powershell is None:
        pytest.skip("PowerShell is unavailable")
    ova = tmp_path / "candidate.ova"
    ova.write_bytes(b"test appliance")
    log = tmp_path / "vbox.jsonl"
    fake = tmp_path / "fake-vbox.ps1"
    disk_id = "12345678-1234-1234-1234-123456789abc"
    fake.write_text(f'''
ConvertTo-Json -InputObject @($args) -Compress | Add-Content -LiteralPath $env:TZMCP_TEST_VBOX_LOG
switch ($args[0]) {{
    '--version' {{ '7.2.18' }}
    'showvminfo' {{
        '"IDE-ImageUUID-0-0"="{disk_id}"'
        'cpus=1'; 'memory=4096'
        if ($env:TZMCP_TEST_BAD_NIC -eq '1') {{ 'nic1="bridged"' }} else {{ 'nic1="nat"' }}
        foreach ($adapter in 2..8) {{ 'nic' + $adapter + '="none"' }}
        'clipboard="disabled"'; 'draganddrop="disabled"'; 'usb="off"'
        'ehci="off"'; 'xhci="off"'; 'vrde="off"'
        'SharedFolderNameMachineMapping1="tzmcp-export"'
        'SharedFolderPathMachineMapping1="' + $env:TZMCP_TEST_EXPORT.Replace([string][char]92, ([string][char]92 + [char]92)) + '"'
    }}
}}
exit 0
''', encoding="utf-8")

    def literal(path):
        return "'" + str(path).replace("'", "''") + "'"

    size_argument = "" if size is None else f"-DiskSizeMb {size}"
    command = f'''
function Get-Command {{
    [CmdletBinding()] param([string]$Name)
    if ($Name -eq 'VBoxManage.exe') {{ [pscustomobject]@{{Path={literal(fake)}}} }}
    else {{ Microsoft.PowerShell.Core\\Get-Command $Name }}
}}
try {{
    & {literal(ROOT / 'scripts/windows/Setup-tzMCP.ps1')} -OvaPath {literal(ova)} -ExpectedSha256 (Get-FileHash {literal(ova)}).Hash -VmName 'test-only' -ExportPath {literal(tmp_path / 'exports')} -VmBaseFolder {literal(tmp_path / 'VM storage')} {size_argument} | Out-Null
    'ok'
}} catch {{ $_.Exception.Message; exit 7 }}
'''
    result = subprocess.run([powershell, "-NoProfile", "-NonInteractive", "-Command", command],
                            env=dict(os.environ, TZMCP_TEST_VBOX_LOG=str(log),
                                     TZMCP_TEST_EXPORT=str(tmp_path / "exports"),
                                     TZMCP_TEST_BAD_NIC="1" if bad_nic else "0"),
                            capture_output=True, text=True)
    if size is not None and size < 10240:
        assert result.returncode == 7
        assert "10240" in result.stdout
        assert not log.exists()
        return
    calls = [json.loads(line) for line in log.read_text(encoding="utf-8-sig").splitlines()]
    if bad_nic:
        assert result.returncode == 7
        assert "VM verification failed before startup" in result.stdout
        assert not any(call[0] == "startvm" for call in calls)
        return
    assert result.returncode == 0, result.stdout + result.stderr
    imported = next(call for call in calls if call[0] == "import")
    assert imported[imported.index("--options") + 1] == "importtovdi"
    assert imported[imported.index("--basefolder") + 1] == str(tmp_path / "VM storage")
    resized = [call for call in calls if call[0] == "modifymedium"]
    if size is not None and size > 10240:
        assert resized == [["modifymedium", "disk", disk_id, "--resize", str(size)]]
        assert calls.index(resized[0]) < next(i for i, call in enumerate(calls) if call[0] == "startvm")
    else:
        assert resized == []
    configured = next(call for call in calls if call[0] == "modifyvm")
    for option, value in (("--audio-enabled", "on"), ("--audio-out", "on"), ("--audio-in", "off")):
        assert configured[configured.index(option) + 1] == value


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


@pytest.mark.parametrize("fail_stage", ["", "validate", "build"])
def test_build_credentials_use_environment_and_are_restored(tmp_path, fail_stage):
    powershell = os.environ.get("TZMCP_TEST_POWERSHELL") or shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        pytest.skip("PowerShell is unavailable")
    wheel, iso = tmp_path / "test.whl", tmp_path / "test.iso"
    wheel.write_bytes(b"test wheel")
    iso.write_bytes(b"test iso")
    log = tmp_path / "packer-calls.jsonl"
    fake = tmp_path / "fake-packer.ps1"
    fake.write_text('''
$entry = @{
    arguments = @($args)
    password_present = ($env:PKR_VAR_build_password -eq 'temporary-test-password')
    hash_present = ($env:PKR_VAR_build_password_hash -eq '$6$temporary-test-hash')
}
$entry | ConvertTo-Json -Compress | Add-Content -LiteralPath $env:TZMCP_TEST_PACKER_LOG -Encoding utf8
if ($env:TZMCP_TEST_FAIL_STAGE -eq $args[0]) { exit 17 }
exit 0
''', encoding="utf-8")

    def literal(path):
        return "'" + str(path).replace("'", "''") + "'"

    command = f'''
$env:PKR_VAR_build_password = 'previous-test-password'
$env:PKR_VAR_build_password_hash = 'previous-test-hash'
$failure = ''
try {{
    & {literal(ROOT / 'scripts/release/build-appliance.ps1')} -WheelPath {literal(wheel)} -IsoPath {literal(iso)} -Packer {literal(fake)} -ApplianceVersion '20261017k' -BuildPassword 'temporary-test-password' -BuildPasswordHash '$6$temporary-test-hash'
    $result = 'ok'
}} catch {{ $failure = $_.Exception.Message; $result = 'failed' }}
if ($env:PKR_VAR_build_password -ne 'previous-test-password' -or $env:PKR_VAR_build_password_hash -ne 'previous-test-hash') {{ throw 'Environment was not restored' }}
Write-Output (@{{result=$result; error=$failure}} | ConvertTo-Json -Compress)
'''
    environment = dict(os.environ, TZMCP_TEST_PACKER_LOG=str(log),
                       TZMCP_TEST_FAIL_STAGE=fail_stage)
    result = subprocess.run([powershell, "-NoProfile", "-NonInteractive", "-Command", command],
                            cwd=tmp_path, env=environment, capture_output=True, text=True, check=True)
    outcome = json.loads(result.stdout)
    assert outcome["result"] == ("failed" if fail_stage else "ok"), outcome["error"]
    calls = [json.loads(line) for line in log.read_text(encoding="utf-8-sig").splitlines()]
    protected = [call for call in calls if call["arguments"][0] in ("validate", "build")]
    assert protected
    assert all(call["password_present"] and call["hash_present"] for call in protected)
    assert all("appliance_version=20261017k" in call["arguments"] for call in protected)
    assert all("temporary-test" not in str(call["arguments"]) for call in calls)
    assert all(Path(call["arguments"][-1]) == ROOT / "appliance/packer" for call in calls)
