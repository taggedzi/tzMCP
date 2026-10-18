# tzMCP VirtualBox appliance guide

For a visual introduction and first capture, see the [README](../README.md).
For architecture, configuration internals, and security limitations, see the
[developer and security guide](DEVELOPER_SECURITY_GUIDE.md).

This guide describes the supported end-user workflow for a published tzMCP
appliance on a 64-bit Windows host with VirtualBox 7.1 or newer.

> **Development status:** No production OVA is included in this repository.
> A compact local candidate is available in `dist/appliance-compact-20261018/`
> on the maintainer machine. It passed sanitization, disk audit, import, and
> HTTPS image capture/export on the development host. The earlier candidate in
> `dist/release-20261017k/` also passed reboot checks on a second Windows 11 PC.
> The compact candidate has not been tested on that second PC or published as a
> production release.

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
inside the VM. The session remains awaiting export, including after a GUI or
VM restart, and **Export Session** retries publication of that archive.

The root helper accepts only session names such as
`20261018T120000Z-abcdef12.zip`. It opens the handoff directories without
following symlinks, checks their ownership and permissions, and opens the
single-link regular archive using the `tzmcp` account's permissions. It copies
from that open descriptor into a private snapshot before temporarily mounting
the host share; this requires extra guest disk space equal to the archive size.
Existing host exports are never overwritten. A failed copy
removes its newly created host file and attempts to unmount the share; captures
and the local archive remain intact. While copying, the host ZIP is incomplete;
wait for the guest to report successful export before opening it.

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
only after verified browser and proxy processes have stopped and exited.
Ending a session releases the active-session pointer and lock. Those files
track the live capture. Sessions that still need export are discovered from
each session directory's `state.json`.

Reopening tzMCP lists every `ENDED` or `INTERRUPTED` session under **Awaiting
export**, oldest session ID first. Choose one and export it. The other
sessions stay in the list. Closing the GUI before export leaves those sessions
on the list for the next startup. A session moves off the list when **Export
Session** publishes its archive. An exported session does not block the next
capture. When several sessions are waiting, export each one before starting
another capture.

A second GUI cannot recover a session while its original GUI is still alive.
If ownership cannot be verified or a process will not stop, recovery blocks
export and preserves the session and Firefox profile. Close the original GUI
or stop the remaining capture processes, then reopen tzMCP to retry. Do not
delete session locks or profiles to bypass this check.
Older running sessions without a saved proxy identity require administrator
inspection; tzMCP cannot safely infer which proxy process belongs to them.

Disk-full and export-copy failures
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
Ubuntu security updates run automatically. Firefox receives updates from
Mozilla's signed APT repository. Every exported session records exact component versions.

The native Windows/Linux/macOS CLI and portable-browser workflow are retained
for contributors and troubleshooting. They are not the supported end-user
workflow.
