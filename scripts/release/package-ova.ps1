[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Container })]
    [string]$OvfDirectory,
    [string]$OutputOva = ".\dist\tzMCP-appliance.ova"
)

$ErrorActionPreference = "Stop"
$source = (Resolve-Path -LiteralPath $OvfDirectory).Path
$ovf = Get-ChildItem -LiteralPath $source -File -Filter *.ovf
$disks = Get-ChildItem -LiteralPath $source -File | Where-Object { $_.Extension -in @(".vmdk", ".hdd", ".vdi") }
if ($ovf.Count -ne 1 -or $disks.Count -lt 1) {
    throw "Expected exactly one OVF and at least one virtual disk in $source."
}
$members = @($ovf.Name) + @($disks.Name)
$manifest = Get-ChildItem -LiteralPath $source -File -Filter *.mf
if ($manifest) { $members += $manifest.Name }
$destinationInput = if ([IO.Path]::IsPathRooted($OutputOva)) {
    $OutputOva
} else {
    Join-Path (Get-Location).Path $OutputOva
}
$destination = [IO.Path]::GetFullPath($destinationInput)
if (Test-Path -LiteralPath $destination) { throw "Output already exists: $destination" }
New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($destination)) -Force | Out-Null

# An OVA is a tar archive containing the OVF descriptor, disks, and optional
# manifest. Keep paths relative to the bundle root so VirtualBox can import it.
& tar.exe -cf $destination -C $source @members
if ($LASTEXITCODE -ne 0) { throw "tar failed while creating $destination" }
Write-Output $destination
