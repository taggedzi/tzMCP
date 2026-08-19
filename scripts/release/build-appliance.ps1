[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string]$WheelPath,
    [Parameter(Mandatory = $true)] [string]$IsoPath,
    [string]$Packer = "packer",
    [string]$VmName = "tzMCP-appliance",
    [Parameter(Mandatory = $true)] [string]$BuildPassword,
    [Parameter(Mandatory = $true)] [string]$BuildPasswordHash
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $WheelPath -PathType Leaf)) { throw "Wheel not found: $WheelPath" }
if (-not (Test-Path -LiteralPath $IsoPath -PathType Leaf)) { throw "Ubuntu ISO not found: $IsoPath" }
if ($BuildPassword -match '^<.*>$') { throw "Replace the BuildPassword placeholder with a temporary password." }
if ($BuildPasswordHash -notmatch '^\$6\$') { throw "BuildPasswordHash must be a valid sha512-crypt hash beginning with `$6`$." }
$resolvedIso = (Resolve-Path -LiteralPath $IsoPath).Path
& $Packer fmt -check appliance/packer
if ($LASTEXITCODE -ne 0) { throw "Packer formatting check failed." }
& $Packer init appliance/packer
if ($LASTEXITCODE -ne 0) { throw "Packer plugin initialization failed." }
& $Packer validate -var "iso_url=$resolvedIso" -var "vm_name=$VmName" -var "tzmcp_wheel=$((Resolve-Path $WheelPath).Path)" -var "build_password=$BuildPassword" -var "build_password_hash=$BuildPasswordHash" appliance/packer
if ($LASTEXITCODE -ne 0) { throw "Packer validation failed." }
& $Packer build -var "iso_url=$resolvedIso" -var "vm_name=$VmName" -var "tzmcp_wheel=$((Resolve-Path $WheelPath).Path)" -var "build_password=$BuildPassword" -var "build_password_hash=$BuildPasswordHash" appliance/packer
if ($LASTEXITCODE -ne 0) { throw "Packer build failed." }
