[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory = $true)]
    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Leaf })]
    [string]$OvaPath,

    [string]$ExpectedSha256,
    [string]$VmName = "tzMCP-appliance",
    [string]$VmBaseFolder,
    [string]$ExportPath = (Join-Path ([Environment]::GetFolderPath("MyDocuments")) "tzMCP Exports"),
    [ValidateRange(1, 32)] [int]$Cpu = 1,
    [ValidateRange(1024, 65536)] [int]$MemoryMb = 4096,
    [ValidateRange(10240, 1048576)] [int]$DiskSizeMb = 10240
)

$ErrorActionPreference = "Stop"

function Get-VBoxManage {
    $command = Get-Command VBoxManage.exe -ErrorAction SilentlyContinue
    if ($null -ne $command) {
        return $command.Path
    }
    $programFiles = [Environment]::GetFolderPath("ProgramFiles")
    $programFilesX86 = [Environment]::GetFolderPath("ProgramFilesX86")
    $candidates = @(@(
        (Join-Path $programFiles "Oracle\VirtualBox\VBoxManage.exe"),
        (Join-Path $programFilesX86 "Oracle\VirtualBox\VBoxManage.exe")
    ) | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) })
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

if ($PSCmdlet.ShouldProcess($VmName, "Import and configure VirtualBox appliance")) {
    New-Item -ItemType Directory -Path $ExportPath -Force | Out-Null
    $importArguments = @("import", $resolvedOva, "--options", "importtovdi", "--vsys", "0", "--vmname", $VmName)
    if (-not [string]::IsNullOrWhiteSpace($VmBaseFolder)) {
        $resolvedBaseFolder = [IO.Path]::GetFullPath($VmBaseFolder)
        [void][IO.Directory]::CreateDirectory($resolvedBaseFolder)
        $importArguments += @("--basefolder", $resolvedBaseFolder)
    }
    Invoke-VBoxManage $vbox $importArguments
    # This appliance has exactly one disk. Use its returned UUID, not a guessed
    # host path; VDI supports expansion and the guest grows ext4 on first boot.
    $importedInfo = @(& $vbox showvminfo $VmName --machinereadable)
    if ($LASTEXITCODE -ne 0) { throw "Could not inspect imported VM storage." }
    $diskIds = @($importedInfo | ForEach-Object {
        if ($_ -match '^"[^"\r\n]+-ImageUUID-[0-9]+-[0-9]+"="([a-fA-F0-9-]{36})"$' -and
            $Matches[1] -ne '00000000-0000-0000-0000-000000000000') { $Matches[1] }
    })
    if ($diskIds.Count -ne 1) { throw "Expected exactly one imported appliance disk." }
    # VirtualBox rejects shrinking if an older, larger OVA is supplied.
    # The default leaves such disks at their original capacity.
    if ($DiskSizeMb -gt 10240) {
        Invoke-VBoxManage $vbox @("modifymedium", "disk", $diskIds[0], "--resize", "$DiskSizeMb")
    }
    Invoke-VBoxManage $vbox @("modifyvm", $VmName, "--cpus", "$Cpu", "--memory", "$MemoryMb",
        "--nic1", "nat", "--nic2", "none", "--clipboard-mode", "disabled",
        "--drag-and-drop", "disabled", "--usb", "off", "--vram", "128",
        "--graphicscontroller", "vboxsvga", "--vrde", "off",
        "--audio-driver", "default", "--audio-controller", "hda",
        "--audio-enabled", "on", "--audio-out", "on", "--audio-in", "off")
    Invoke-VBoxManage $vbox @("sharedfolder", "add", $VmName, "--name", "tzmcp-export",
        "--hostpath", (Resolve-Path -LiteralPath $ExportPath).Path)
    $verifiedInfo = @(Invoke-VBoxManage $vbox @("showvminfo", $VmName, "--machinereadable"))
    $requiredSettings = @("cpus=$Cpu", "memory=$MemoryMb", 'nic1="nat"',
        'clipboard="disabled"', 'draganddrop="disabled"', 'usb="off"',
        'ehci="off"', 'xhci="off"', 'vrde="off"')
    foreach ($adapter in 2..8) { $requiredSettings += "nic$adapter=`"none`"" }
    foreach ($setting in $requiredSettings) {
        if ($verifiedInfo -notcontains $setting) {
            throw "VM verification failed before startup: expected $setting"
        }
    }
    if (@($verifiedInfo | Where-Object { $_ -match '^Forwarding\(' }).Count -ne 0) {
        throw "VM verification failed before startup: port forwarding is configured."
    }
    $shareNames = @($verifiedInfo | Where-Object { $_ -match '^SharedFolderNameMachineMapping[0-9]+=' })
    $expectedHostPath = (Resolve-Path -LiteralPath $ExportPath).Path.Replace('\', '\\')
    if ($shareNames.Count -ne 1 -or $shareNames[0] -ne 'SharedFolderNameMachineMapping1="tzmcp-export"' -or
        $verifiedInfo -notcontains "SharedFolderPathMachineMapping1=`"$expectedHostPath`"" -or
        @($verifiedInfo | Where-Object { $_ -match '^SharedFolderAutoMount.*="?(1|yes|on|true)' }).Count -ne 0) {
        throw "VM verification failed before startup: unexpected shared-folder configuration."
    }
    $verifiedInfo | Out-Host
    Invoke-VBoxManage $vbox @("startvm", $VmName, "--type", "gui")
}
