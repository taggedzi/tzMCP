# tzMCP VirtualBox appliance guide

For a visual introduction and first capture, see the [README](../README.md).
For architecture, configuration internals, and security limitations, see the
[developer and security guide](DEVELOPER_SECURITY_GUIDE.md).

This guide describes the supported end-user workflow for a published tzMCP
appliance on a 64-bit Windows host with VirtualBox 7.1 or newer.

> **Development status:** No production OVA is included in this repository.
> A verified local candidate is available in `dist/release-20261017k/` on the
> maintainer machine. It passed import, HTTPS capture/export, and reboot checks
> on the development host and a second clean Windows 11 PC. It has not been
> published as a production release.

## Install

Windows PowerShell 5.1 and PowerShell 7 are supported. Setup finds VirtualBox
in its standard installation directory even when it is absent from `PATH`.

Obtain the release OVA, its `SHA256SUMS` file, and
`Setup-tzMCP.ps1`. Run PowerShell in the directory containing the artifacts:

```powershell
.\Setup-tzMCP.ps1 `
  -OvaPath .\tzMCP-appliance.ova `
  -ExpectedSha256 <published-ova-sha256>
```

Exports default to `%USERPROFILE%\Documents\tzMCP Exports`. Choose another
host directory before import with `-ExportPath` if required. The setup script
uses the fixed guest share name `tzmcp-export`, disables automount, and does
not change the host browser, Windows proxy settings, or the host trust store.
Use `-VmBaseFolder <directory>` to choose where the VM disk is stored.
Use `-DiskSizeMb 73728` to expand the default 60 GiB disk to 72 GiB before
first boot. Setup imports a dynamic VDI; Ubuntu grows its root partition and
filesystem automatically. Shrinking below the image's 60 GiB size is rejected.
The VM defaults to one virtual CPU; this avoids guest CPU stalls observed with
two CPUs on the development host. `-Cpu` can be raised on a host where the
appliance has been verified to boot and capture reliably.

## Capture a session

1. Start the VM and open **tzMCP Capture** from the guest desktop.
2. Open **Capture Rules**, select the media types you want to save (such as
   **Image** or **Video**), and select **Save Configuration**. No MIME groups
   are enabled by default, so choose at least one before capturing.
3. Return to **Capture Session** and select **Start proxy**.
4. Select **Launch Firefox**. Firefox uses a new temporary profile and the
   appliance’s private loopback proxy.
5. Browse only the material appropriate for interception. HTTPS traffic is
   decrypted inside the VM; never enter passwords, payment details, recovery
   codes, or other sensitive credentials during capture.
6. Select **Stop** to stop Firefox and the proxy and finalize the session.

Capture rules can be edited while no session is running. The effective rules
are copied into the session and cannot change during capture.

## Export

After Firefox and the proxy have stopped, select **Export Session**. The
completed archive is copied through the controlled `tzmcp-export` share into
the selected host folder. If copying fails, the completed local archive stays
inside the VM and can be retried.

Each archive contains capture files, sanitized session logs, the effective
configuration, `session.json`, and `SHA256SUMS`. Recompute the listed hashes
after unpacking. SHA-256 proves file integrity after publication; it does not
prove who produced the archive or provide a digital signature.

Archives do not contain the Firefox profile, cookies, history, credentials,
cache, local storage, mitmproxy CA private key, unrelated sessions, or absolute
guest paths.

## Recovery and persistence

If the GUI or VM stops unexpectedly, reopen tzMCP. It will preserve captured
files, recover the active session as `INTERRUPTED`, and offer it for export
after owned processes have been handled. Disk-full and export-copy failures
must not delete captured evidence; free space and retry.

If Activity reports `No space left on device`, free guest disk space before
ending and exporting the session. Previously saved captures remain available.
An image whose save failed can be requested again after space is available;
only successfully saved content is marked as a duplicate.

The VM persists capture rules, completed/interrupted session records, and its
VM-specific CA across reboots. The temporary Firefox profile is deleted after
the session ends, so cookies, history, credentials, cache, and local storage
do not carry into the next session.

## Security boundary

The VM uses one NAT adapter and no port forwarding. Clipboard sharing,
drag-and-drop, USB passthrough, and automatic shared-folder mounting are
disabled. VirtualBox Remote Desktop Extension (VRDE) is disabled. The regular
guest account has no general mount privileges. The CA is trusted only by the
managed per-session Firefox profile and is not added to the Windows or guest
system trust store.

## Updates and limitations

Update tzMCP by importing a newer published appliance release according to its
release notes. Do not replace the application files manually inside the VM.
Ubuntu security updates run automatically. Firefox continues receiving its
normal Snap updates. Every exported session records exact component versions.

The native Windows/Linux/macOS CLI and portable-browser workflow are retained
for contributors and troubleshooting. They are not the supported end-user
workflow.
