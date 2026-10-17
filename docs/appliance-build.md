# Maintainer appliance builds

See the [developer and security guide](DEVELOPER_SECURITY_GUIDE.md) for the
code architecture, trust boundaries, and test workflow. User installation and
capture instructions are in the [appliance guide](appliance.md).

Build locally on the controlled maintainer machine. A successful build is a
candidate; publication still requires the transition plan's acceptance matrix.
Generated images, credentials, and audit output must remain outside Git.

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
(130 GiB for the default disk). Check the underlying Windows drive too when
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
