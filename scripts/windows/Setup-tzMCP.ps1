[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory = $true)]
    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Leaf })]
    [string]$OvaPath,

    [string]$ExpectedSha256,
    [string]$VmName = "tzMCP-appliance",
    [string]$ExportPath = (Join-Path ([Environment]::GetFolderPath("MyDocuments")) "tzMCP Exports"),
    [ValidateRange(1, 32)] [int]$Cpu = 2,
    [ValidateRange(1024, 65536)] [int]$MemoryMb = 4096,
    [ValidateRange(10240, 1048576)] [int]$DiskSizeMb = 61440
)

$ErrorActionPreference = "Stop"

function Get-VBoxManage {
    $command = Get-Command VBoxManage.exe -ErrorAction SilentlyContinue
    if ($null -ne $command) {
        return $command.Path
    }
    $programFiles = [Environment]::GetFolderPath("ProgramFiles")
    $programFilesX86 = [Environment]::GetFolderPath("ProgramFilesX86")
    $candidates = @(
        (Join-Path $programFiles "Oracle\VirtualBox\VBoxManage.exe"),
        (Join-Path $programFilesX86 "Oracle\VirtualBox\VBoxManage.exe")
    ) | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) }
    if ($candidates.Count -eq 0) {
        throw "VirtualBox 7.1+ is required; VBoxManage.exe was not found on PATH or in the standard installation locations."
    }
    return $candidates[0]
}

function Invoke-VBoxManage {
    param([string]$Executable, [string[]]$Arguments)
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "VBoxManage failed with exit code ${LASTEXITCODE}: $($Arguments -join ' ')"
    }
}

$vbox = Get-VBoxManage
$versionText = (& $vbox --version | Select-Object -First 1)
$versionMatch = [regex]::Match($versionText, "(?<major>\d+)\.(?<minor>\d+)")
if (-not $versionMatch.Success -or [int]$versionMatch.Groups["major"].Value -lt 7 -or
    ([int]$versionMatch.Groups["major"].Value -eq 7 -and [int]$versionMatch.Groups["minor"].Value -lt 1)) {
    throw "VirtualBox 7.1+ is required; detected '$versionText'."
}

$resolvedOva = (Resolve-Path -LiteralPath $OvaPath).Path
if ([string]::IsNullOrWhiteSpace($ExpectedSha256)) {
    $sidecar = "$resolvedOva.sha256"
    if (-not (Test-Path -LiteralPath $sidecar -PathType Leaf)) {
        throw "ExpectedSha256 or a sidecar checksum file ($sidecar) is required."
    }
    $ExpectedSha256 = ((Get-Content -LiteralPath $sidecar -Raw) -split "\s+")[0]
}
$actualSha256 = (Get-FileHash -LiteralPath $resolvedOva -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualSha256 -ne $ExpectedSha256.Trim().ToLowerInvariant()) {
    throw "OVA SHA-256 mismatch. Expected $ExpectedSha256, got $actualSha256."
}

$existing = (& $vbox list vms) -join "`n"
if ($existing -match ('"' + [regex]::Escape($VmName) + '"')) {
    throw "A VirtualBox VM named '$VmName' already exists. Choose another name or remove it manually."
}

New-Item -ItemType Directory -Path $ExportPath -Force | Out-Null
if ($PSCmdlet.ShouldProcess($VmName, "Import and configure VirtualBox appliance")) {
    Invoke-VBoxManage $vbox @("import", $resolvedOva, "--vsys", "0", "--vmname", $VmName)
    Invoke-VBoxManage $vbox @("modifyvm", $VmName, "--cpus", "$Cpu", "--memory", "$MemoryMb",
        "--nic1", "nat", "--nic2", "none", "--clipboard-mode", "disabled",
        "--drag-and-drop", "disabled", "--usb", "off")
    Invoke-VBoxManage $vbox @("sharedfolder", "add", $VmName, "--name", "tzmcp-export",
        "--hostpath", (Resolve-Path -LiteralPath $ExportPath).Path)
    Invoke-VBoxManage $vbox @("showvminfo", $VmName, "--machinereadable") | Out-Host
    Invoke-VBoxManage $vbox @("startvm", $VmName, "--type", "gui")
}
