# Appliance checkpoint — 2026-10-19

Work resumed from the interrupted **Compare GitHub distribution options** chat.
Source changes belong to PR #38, branch `codex/compact-10gib-appliance`.

## Current candidate

- Directory: `dist/appliance-10gib-20261018-b/`.
- OVA: `tzMCP-appliance-20261018-10gib-b.ova`.
- Size: 1,634,260,992 bytes (1.52 GiB).
- SHA-256: `5ad93e746382b89106fe880718028071a41e83de34184435f68234f5508779fc`.
- Includes Tumbler, fixing Ristretto's missing thumbnail-service warning.

The OVA and evidence are local build outputs, not committed release assets.
This candidate supersedes the earlier `20261018-10gib` candidate for acceptance.

## Verified

The interrupted run saved successful sanitation and independent offline disk-audit
reports, HTTPS capture/export evidence (five images, seven member hashes), and
image/text/video preview evidence. Its audio monitor detected output; this does
not establish that a person heard playback.

The resumed run verified the OVA checksum and completed these checks:

- Default guest reboots into Xfce and automatically starts tzMCP.
- Certificate fingerprint persists across reboot; a separate import has a
  different certificate.
- Saved configuration and the prior completed export state remain present.
  No active session or temporary browser profile remains after reboot.
- Runtime Python file hashes in both guests match the expected wheel manifest.
- First-boot initialization succeeds and automatic update timers are enabled.
- The documented 20 GiB import expands the root filesystem and starts tzMCP.
- Default first-boot free space was 6.29 GiB; after later sessions and reboot it
  is 6.09 GiB. The expanded guest has 15.71 GiB free.
- Full Windows test suite: **255 passed, 17 skipped**. Command:
  `venv/Scripts/pytest.exe -q -p no:cacheprovider --tb=short -x --basetemp=dist/pytest-host-resume-20261019`,
  with `TZMCP_TEST_BASH=C:/Program Files/Git/bin/bash.exe` and host access.
  Skips require an isolated Linux root runner or unavailable symlink support.
  Earlier sandbox attempts failed on temporary-directory/MSYS permissions.

Detailed local evidence is in `dist/acceptance-10gib-20261018-b/`, including
`base.json`, `reboot.json`, `expanded.json`, `capture-export.json`, `preview.json`,
and `resume-summary.json`. Disk audit and sanitation reports are beside the OVA.
The original capture/export verification is recorded evidence; the resumed run
did not repeat that capture or revalidate the original archive bytes.

## Next work

Before publishing a production release, test this exact candidate on the second
Windows PC and have a person confirm audible playback. Keep those results tied
to the checksum above. The [initialization-failure and recovery acceptance
check](appliance-build.md#initialization-failure-and-recovery-acceptance), added
after the recorded run during PR review, is also pending. It must verify blocked
desktop startup, console diagnosis, and successful retry with the CA and saved
sessions preserved; it is not part of the completed evidence above.
Merge PR #38 and manually upload the OVA, checksum, and
setup script when release acceptance is complete.
