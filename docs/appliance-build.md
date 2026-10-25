# Maintainer appliance builds

See the [developer and security guide](DEVELOPER_SECURITY_GUIDE.md) for the
code architecture, trust boundaries, and test workflow. User installation and
capture instructions are in the [appliance guide](appliance.md).

Build locally on the controlled maintainer machine. A successful build is a
candidate; publication still requires the transition plan's acceptance matrix.
Generated images, credentials, and audit output must remain outside Git.

New builds use a 10 GiB virtual disk and Ubuntu Server's minimized installation
source (`ubuntu-server-minimal`). Keep the pinned ISO's source ID checked against
`casper/install-sources.yaml` when changing ISOs. The desktop remains Xfce,
installed without recommended extras; Ristretto, Parole, and Mousepad provide
local image, audio/video, and text inspection. Tumbler supplies image thumbnails
without a first-run missing-service warning. The standalone system pip is
omitted; the application's venv provides its own pip. Fonts, audio/volume
controls, guest integration, and unattended updates are explicitly installed
rather than relying on the full server installation. tzMCP starts at desktop
login, with the ordinary desktop still available.
Disk swap is disabled so the installer does not reserve several GiB of the
small base disk. Keep the 4 GiB RAM default and check memory use during acceptance.

This recipe needs a new build; existing release candidates are unchanged.
Acceptance must confirm installation fits in 10 GiB with useful free space,
automatic GUI startup after first boot and reboot, image/text/media inspection
(including audible playback), capture/export, and a 20 GiB setup import whose
guest root filesystem expands. Record actual used/free space and OVA size;
package changes alone do not establish a smaller download. Check that APT's
unattended upgrade service/timers and Firefox update origin remain enabled.

## Build the guest

Build a wheel from the repository's venv and retain its SHA-256. Use Packer
1.14+ and VirtualBox 7.1+ with the pinned Ubuntu ISO in
`appliance/packer/variables.pkr.hcl`.

Run `scripts/release/build-appliance.ps1` from a new temporary build directory
on a drive with enough capacity. Pass absolute wheel/ISO paths and fresh
temporary `BuildPassword` / SHA-512-crypt `BuildPasswordHash` variables. Generate
a shell-safe temporary password; do not save credentials in source or command
history. The wrapper passes credentials through Packer environment variables
and restores the caller's previous values even after failure.
Pass `-ApplianceVersion` with the candidate's release label. Provisioning stores
that label in the guest environment so GUI restarts and exports retain it;
omitting it retains the `development` default.

Wait for Packer's terminal success before using its OVF/VMDK output. Quiet
installer or shutdown output is not evidence of failure.

## Clean and independently verify the exported disk

The guest finalizer removes build accounts, account backups, cloud state,
identity, logs, and keys. Filling the live filesystem does **not** reliably
overwrite every freed block: a real exported image retained deleted account
records after that step. Offline sanitation is therefore required.

Use Linux or Ubuntu WSL with `qemu-utils`, `e2fsprogs`, and `zerofree` installed.
Allow twice the virtual disk size plus 10 GiB on the Linux temporary drive
(30 GiB for the new 10 GiB disk; 130 GiB for older 60 GiB images). This is
sanitation scratch space, in addition to the ISO and build/output bundles.
Check the underlying Windows drive too when
using WSL. Keep large temporary images off a nearly full repository drive.

With Linux paths, run:

```bash
python3 scripts/release/sanitize-appliance.py /path/to/completed-ovf /path/to/new-clean-bundle
python3 scripts/release/verify-appliance.py /path/to/new-clean-bundle/disk.vmdk /path/to/new-audit.json
```

Use the actual VMDK basename from the bundle. The sanitizer creates a new
directory, preserves the source bundle, checks ext4, zeros its unallocated
blocks offline, verifies the converted disk byte-for-byte, and creates a fresh
OVF manifest. Its `sanitization.json` records input/output hashes.

The independent verifier must exit zero with both `raw_scan_complete` and
`residue_checks_pass` true. A partial report is not a pass. It also checks
identity, logs, home directories, CA/session data, backups, SSH material, and
temporary files. Its decoded copy is removed by default; `--keep-work` retains
it for diagnosis and requires a later explicit cleanup.

## Package and exercise the candidate

Package **the sanitized bundle**, using `scripts/release/package-ova.ps1`.
Generate and validate checksums with the release scripts. Preserve the matching
Packer manifest and sanitation report alongside the OVA.

Import through `scripts/windows/Setup-tzMCP.ps1` and perform the manual capture,
recovery, export, host-boundary, and independent-CA checks in the
[transition plan](superpowers/plans/2026-07-23-virtualbox-appliance-transition.md).
Record any unavailable gate explicitly; a development-host import does not
prove clean-host compatibility.

### Maintenance boot for recovery

Use this only on a preserved VM or a disposable acceptance import. The regular
`tzmcp` account intentionally has no general sudo access; do not broaden its
sudoers rules for recovery.

1. At VM startup, hold Shift for the BIOS GRUB menu (or press Esc for an EFI
   guest). Select Ubuntu and press **e**. On the line beginning `linux`, replace
   the standalone `ro` with `rw` and append `init=/bin/bash`. Boot the edited
   entry with **Ctrl+X** or **F10**. This is a one-boot root shell, not a persistent
   boot configuration change.
2. Ensure the root filesystem is writable and inspect the latest retained logs:

   ```sh
   mount -o remount,rw /
   journalctl -u tzmcp-first-boot.service -u lightdm.service -n 100 --no-pager
   df -h /
   ```

If the journal has no retained boot, inspect
`/var/lib/tzmcp/logs/first-boot-ca.log` for CA-generation failures. Correct the
specific reported cause; do not erase captures, session metadata, or CA files.
Systemd is not running in this shell, so `systemctl restart` is not available.
Run `sync` and then `reboot -f` to boot normally. Initialization retries on each
boot; verify both services are active and tzMCP opens after the repair.

### Initialization-failure and recovery acceptance

**Pending:** this is a manual systemd/desktop check, not covered by the Windows
unit suite. Use a separate disposable import of the exact candidate checksum;
never inject failures into a user's working VM or the release image.

1. Complete a normal boot. Record the CA certificate SHA-256 and a known saved
   session's file hashes, shut down, and take a snapshot. Enter the maintenance
   shell above and inject a failure before initialization runs:

   ```sh
   mkdir -p /etc/systemd/system/tzmcp-first-boot.service.d
   printf '%s\n' '[Service]' 'ExecStartPre=/bin/false' \
     > /etc/systemd/system/tzmcp-first-boot.service.d/90-acceptance-failure.conf
   sync
   reboot -f
   ```

2. Use the guest console as described in the [user recovery guide](appliance.md#desktop-does-not-start).
   Record `systemctl status tzmcp-first-boot.service lightdm.service --no-pager`.
   Confirm initialization failed, LightDM is not active, and no tzMCP GUI opened.
   Confirm the console remains accessible for diagnosis.

3. Reenter maintenance boot. Confirm the journal identifies the injected
   `ExecStartPre` failure, then remove only the test override and retry:

   ```sh
   rm /etc/systemd/system/tzmcp-first-boot.service.d/90-acceptance-failure.conf
   sync
   reboot -f
   ```

4. Require successful initialization, active LightDM, automatic tzMCP startup,
   and unchanged CA/session hashes. Save the failure and recovery service
   output with the candidate checksum. Mark this gate complete only after those
   observations; restore the snapshot or discard the disposable import afterward.
