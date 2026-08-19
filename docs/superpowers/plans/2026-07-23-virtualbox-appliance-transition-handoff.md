# tzMCP appliance transition handoff

Date: 2026-07-23

## Current state

- The appliance built successfully with Packer from `ubuntu-24.04.4-live-server-amd64.iso`.
- The OVF was packaged as `dist/tzMCP-appliance.ova` and checksummed.
- VirtualBox 7.2.12 is installed and `VBoxManage` is now on PATH.
- The OVA imported successfully as `tzMCP-appliance`.
- The host export folder was added manually after setup-script compatibility was fixed:
  `C:\Users\tagge\Documents\tzMCP Exports`.
- The VM currently auto-logs into the `tzmcp` account, but it opens a terminal instead of the desktop.

## Important credential detail

The Packer `BuildPassword` belongs to the temporary `tzmcp-build` provisioning account. It is not the runtime `tzmcp` account password. The runtime account is configured for automatic login and is not expected to prompt for a password.

## Current diagnostic

Inside the VM, `systemctl status lightdm --no-pager` showed:

- LightDM is enabled.
- LightDM is failed with exit status 1.
- This means the remaining problem is Xorg/display startup, not authentication.
- The VM has only 4 MB VRAM, which is likely insufficient for the desktop/display stack.

## Code changes already made

- `appliance/packer/tzmcp.pkr.hcl`: set VirtualBox VRAM to 128 MB and emit `--vram 128`.
- `appliance/provisioning/install-base.sh` and `configure-desktop.sh`: explicitly enable LightDM.
- `scripts/windows/Setup-tzMCP.ps1`: locate VirtualBox in standard install paths and use VirtualBox 7.2-compatible shared-folder syntax.

These changes are in the working tree but are not yet included in the already-built OVA.

## Next steps after reconnecting

1. Stop the current VM from the Windows host and raise its VRAM:

   ```powershell
   VBoxManage controlvm "tzMCP-appliance" acpipowerbutton
   VBoxManage modifyvm "tzMCP-appliance" --vram 128
   VBoxManage startvm "tzMCP-appliance" --type gui
   ```

2. If it still opens a terminal, collect the display error inside the VM:

   ```bash
   journalctl -u lightdm -b --no-pager
   ```

3. Rebuild and repackage the OVA so the VRAM and LightDM fixes are included in the distributable appliance.

4. The focused provisioning/release tests currently pass (`14 passed`); the full suite previously passed (`126 passed, 1 skipped`).
