[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string]$WheelPath,
    [Parameter(Mandatory = $true)] [string]$IsoPath,
    [string]$Packer = "packer",
    [string]$VmName = "tzMCP-appliance",
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$')]
    [string]$ApplianceVersion = "development",
    [Parameter(Mandatory = $true)] [string]$BuildPassword,
    [Parameter(Mandatory = $true)] [string]$BuildPasswordHash
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $WheelPath -PathType Leaf)) { throw "Wheel not found: $WheelPath" }
if (-not (Test-Path -LiteralPath $IsoPath -PathType Leaf)) { throw "Ubuntu ISO not found: $IsoPath" }
if ($BuildPassword -match '^<.*>$') { throw "Replace the BuildPassword placeholder with a temporary password." }
if ($BuildPasswordHash -notmatch '^\$6\$') { throw "BuildPasswordHash must be a valid sha512-crypt hash beginning with `$6`$." }
$resolvedIso = (Resolve-Path -LiteralPath $IsoPath).Path
$packerSource = (Resolve-Path (Join-Path $PSScriptRoot "../../appliance/packer")).Path
& $Packer fmt -check $packerSource
if ($LASTEXITCODE -ne 0) { throw "Packer formatting check failed." }
& $Packer init $packerSource
if ($LASTEXITCODE -ne 0) { throw "Packer plugin initialization failed." }
$previousBuildPassword = $env:PKR_VAR_build_password
$previousBuildPasswordHash = $env:PKR_VAR_build_password_hash
try {
    # Avoid exposing temporary credentials in Packer's process arguments.
    $env:PKR_VAR_build_password = $BuildPassword
    $env:PKR_VAR_build_password_hash = $BuildPasswordHash
    & $Packer validate -var "iso_url=$resolvedIso" -var "vm_name=$VmName" -var "appliance_version=$ApplianceVersion" -var "tzmcp_wheel=$((Resolve-Path $WheelPath).Path)" $packerSource
    if ($LASTEXITCODE -ne 0) { throw "Packer validation failed." }
    & $Packer build -var "iso_url=$resolvedIso" -var "vm_name=$VmName" -var "appliance_version=$ApplianceVersion" -var "tzmcp_wheel=$((Resolve-Path $WheelPath).Path)" $packerSource
    if ($LASTEXITCODE -ne 0) { throw "Packer build failed." }
} finally {
    $env:PKR_VAR_build_password = $previousBuildPassword
    $env:PKR_VAR_build_password_hash = $previousBuildPasswordHash
}
