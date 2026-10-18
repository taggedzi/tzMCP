# tzMCP VirtualBox Appliance Transition Plan

**Date:** 2026-07-23  
**Status:** Running configured appliance ready; development-host and clean Windows-host workflows verified; production publication not performed
**Primary platform:** 64-bit Windows host running VirtualBox 7.1+  
**Guest:** Ubuntu 24.04 LTS, x86-64, lightweight desktop, Firefox  
**Application mode:** `TZMCP_APPLIANCE=1`

## Current resume point (2026-10-17)

- User acceptance is confirmed: the user browsed Wikipedia, exported the
  session, found its ZIP in the host export folder, and reported success.
  Pre-commit project cleanup removed unused Ubuntu ISO downloads, Packer/build
  caches, obsolete wheel copies/checksum sidecars, and pytest scratch folders.
  Another **12.55 GiB** was recovered on E:, leaving **126.66 GiB free**.
  The final release, fallback OVA, all VM disks, captures, exports, and diagnostic
  acceptance records are preserved. Exact cleanup paths are in
  `dist/diagnostics/cleanup-precommit-20261017.json`. A locked disposable pytest
  cache was deleted after restoring access only for its existing owner.
  Fresh pre-commit validation: **185 passed, 2 Windows symlink checks skipped**;
  `git diff --check` passes. Generated images and runtime data remain outside Git.
- Clean-host gate passed: the user supplied a second Windows 11 Pro PC,
  reachable using the existing `ssh wo4` alias. SSH key authentication and
  administrator access work. It has firmware virtualization enabled, an active
  Windows hypervisor, about 14 GiB RAM, and 311 GiB free on C:. VirtualBox was
  absent. Oracle-signed VirtualBox 7.2.18 (published SHA-256 checked) installed
  successfully with only `VBoxApplication`, exit 0, no restart requested.
  Baseline records 22 proxy/browser/certificate digests before installation.
  Import of the unchanged release `k` OVA passed after fixing a real Windows
  PowerShell 5.1 setup bug: one standard-location match became a scalar string,
  and indexing it returned `C`. The filtered candidates are now explicitly an
  array. Regression coverage runs against PowerShell 7 and Windows PowerShell
  5.1; full suite: **185 passed, 2 Windows symlink checks skipped**.
  Current setup SHA-256 is
  `3e2dff99e305508eed033320392b42e3c1c9e448b6ed779e1128a53215c476dc`.
  All 48 guest modules and the first-boot script match the release; the 72 GiB
  disk expands correctly and security updates remain enabled. The fresh CA
  differs from the local VM. HTTPS capture, Stop, and GUI Export passed:
  10 images, 1,389,096 bytes, 12 verified archive hashes, eight valid raster
  images and two valid SVGs. Archive SHA-256:
  `ace85da3f621b682242bb6ffbcdd204048995d1fc33ec751fc28635dbb416d56`.
  Reboot preserved config, exported session, and public CA bytes exactly; no
  active pointer, browser profile, Firefox, firefox-bin, or mitmdump remains.
  All 22 post-install host boundary digests match after the appliance workflow.
  VirtualBox's own installation added its Oracle TrustedPublisher certificate;
  that prerequisite change is recorded separately from the appliance baseline.
  Remote VM UUID `8814f573-fbe6-4c65-8721-bb5f2e39cdf2` is running in desktop
  session 1 with the GUI idle, Image-only rules saved, and Start proxy enabled.
  The temporary launch task, diagnostic server, guest hash snapshot, transferred
  OVA, and installer were removed; 3,153,641,665 remote bytes reclaimed.
  Evidence: `dist/diagnostics/20261017k-cleanhost-*` and
  `dist/diagnostics/cleanhost-20261017k/`. The release bundles consolidated
  `clean-host-acceptance.json`. Earlier no-second-PC and scope-question gates
  are superseded. The requested running/configured appliance goal is satisfied;
  this is a verified candidate, not a publicly published production release.
  Final inventory: remote VM is running, test server/task are absent, and the
  export is preserved. E: has 114.11 GiB free. No local VM was running at that
  inventory; its previously verified configuration and data were left alone.
- Latest state supersedes the historical build notes below: `j` passed normal
  HTTPS capture/export (six images, eight verified archive hashes), real
  disk-full cleanup/retry/dedup, automatic interruption/export after Firefox
  and CA-import failures, reboot persistence, and all 27 host-setting digest
  comparisons. Evidence is in `dist/diagnostics/20261017j-*-acceptance.json`
  and the persistence screenshot. The `j` VM was found powered off on resume;
  it and its captures are preserved. It was subsequently started successfully;
  the normal Applications > Internet > tzMCP Capture launcher opened the GUI.
  Image-only rules (minimum 10,240 bytes, 301x301 pixels) remain saved, and the
  GUI is left idle on Capture Session with Start proxy available. Evidence:
  `dist/diagnostics/20261017j-restored-image-rules.png`. Inspect fresh state
  before any further input: the user may begin using this fallback.
- `j` exports incorrectly report Firefox as `unknown` after browser cleanup.
  Source now discovers the installed launcher when collecting versions after
  cleanup. Release labels are persisted through PAM in `/etc/environment`.
  Candidate `k` includes these corrections; do not claim it verified until
  offline sanitation, independent audit, import, and live export checks finish.
- The corrected candidate `k` build completed successfully in 15m55s in
  `%TEMP%\tzmcp-appliance-build-20261017k` (tool session `49920` ended zero). Its wheel
  SHA-256 is `e32f06c1b25801ef9d81b0b23a8aa3ee136b59c5feeebeb37f5dff70c8110eb2`;
  release label is `20261017k`. Initial Packer preflight rejected lowercase
  validation-message text before creating a VM; that text was corrected and
  the retried configuration validated successfully. The first actual install
  failed SSH authentication: Windows PowerShell's native stdin pipe added CR
  to the temporary password before Cygwin OpenSSL hashed it. A public test
  proved stdin/argument hashes differed. The failed Packer process tree was
  stopped, its disposable VM powered off/unregistered, and its checked temporary
  directory removed. Retry uses .NET redirected stdin with an explicit LF and
  verifies the public hashing roundtrip before creating any build credentials.
  No real password is passed in process arguments. Both Packer handles ended.
- Current validation: 184 tests passed, 2 Windows symlink checks skipped;
  setup PowerShell syntax and `git diff --check` passed. Setup now accepts
  optional `-VmBaseFolder` so the final VM can live on C: without changing
  VirtualBox's global default. Actual import with that option passed (`90603`).
  Setup now checks actual CPU/RAM, NAT-only adapters, disabled integrations,
  absence of port forwarding, and the intended export share before startup.
  A mocked networking mismatch confirms startup is refused. Export-directory
  creation also respects `ShouldProcess`.
- `DiskSizeMb` is now wired: import to dynamic VDI, select the returned disk
  UUID, resize before boot, and reject shrinking below 61440 MB. First boot
  grows only the mounted ext4 root partition using `growpart` and `resize2fs`;
  the base image installs `cloud-guest-utils`. These provisioning files were
  updated before the corrected `k` build started. Verify
  installed script hashes and the 73728 MB import's usable guest capacity.
  Source hashes: first-boot
  `45c903d87a2619ee993d4d3cd29f2297ce8e0f25eb94fcb541073500bb0bc804`;
  install-base
  `0a4d4a0c224dba56f835004cc5420af7740904219e99bd9b1a9d687a213d5280`.
  Full suite after this change: **183 passed, 2 skipped**. Setup and Bash
  behavioral tests cover resize ordering, spaced paths, shrink rejection,
  no-change output, actual grow errors, and unsupported filesystems. ShellCheck
  and `git diff --check` pass. Actual expanded import and second-boot no-change
  growth path both passed on `tzMCP Capture`.
- The corrected build connected successfully over SSH, installed Firefox
  `158.0-2`, uploaded the expected wheel and first-boot script, and finished
  provisioning, shut down, exported, and removed its disposable build VM.
  Offline sanitation completed (`8144` ended zero), producing
  `%TEMP%\tzmcp-appliance-clean-20261017k`. Independent audit `5901` also ended
  zero: full raw scan has zero markers, source unchanged, all identity/pristine
  checks pass, logs empty. Sanitized disk SHA-256:
  `810250e00fdbf7cd9cba07059a862c7306692b34fdd80dfd31c634eea3ec20d8`.
  Source/wheel equality for all 48 modules is recorded in
  `dist/runtime-expected-20261017k.json`; aggregate runtime hash is
  `49a2c0b44d7cf4671e23b2a8790f5660fcb4d0cef0eb370b6fcecef5b1385a12`.
  `dist/build-inputs-20261017k.json` records the build-time input hashes; the
  setup script was subsequently strengthened and needs its final release hash.
- `dist/release-20261017k/` is prepared with the final setup script (SHA-256
  `3e2dff99e305508eed033320392b42e3c1c9e448b6ed779e1128a53215c476dc`),
  matching Packer manifest, build inputs, and expected runtime digest.
  `source-20261017k.zip` contains 79 verified source entries and per-file hashes.
  The sanitized OVA is now packaged there (SHA-256
  `b691d54e73c4b14712c45cd8b31b5bfda072c57406b02b538065db026d65c6ce`),
  with its sidecar checksum. Setup import `90603` completed successfully as
  `tzMCP Capture`, UUID `4eb618b4-0bc3-4e3f-80cc-ce99d4670064`, at
  `C:\Users\tagge\VirtualBox VMs\tzMCP Capture`. Its 73728 MB VDI and root
  filesystem (75,771,174,912 bytes) expanded successfully. Export folder is
  `C:\Users\tagge\Documents\tzMCP Exports`. Runtime probe passed all 48 module
  hashes, first-boot script hash, service, owner-only CA, security updates,
  and exact versions (Firefox 158.0, appliance 20261017k). New CA fingerprint
  `91:1A:6C:73:B1:98:57:43:2D:71:18:26:69:C3:A4:DD:25:33:86:F8:00:D7:7B:E6:C3:3F:A1:E8:25:46:8D:E7`
  differs from independently initialized `j`. Evidence is in
  `dist/diagnostics/20261017k-first-boot-acceptance.json` and release
  `runtime-verification.json` / `components.json`.
  Capture rules are saved Image-only through the normal desktop launcher.
  Session `20261017T212827Z-17386b28` completed HTTPS capture, Stop, and GUI
  Export: 11 images, 1,512,925 bytes, all 13 archive hashes valid. Nine raster
  images and two SVGs validate with their appropriate decoders. Exported
  versions correctly report appliance 20261017k and Firefox 158.0, with no
  absolute guest save path, browser profile, or CA members. Archive SHA-256:
  `579d47ae931971b06cc3d17009d5b01a3d8eaf58765ac476e36d3851b80ad4bb`.
  After graceful shutdown/restart, saved rules, CA fingerprint, and exported
  session state match byte-for-byte. No active session, temporary browser
  profile, or owned Firefox/mitmdump remains. The first-boot service remains
  successful on the second boot. All 27 host-setting digests match before/after.
  Evidence: `20261017k-live-acceptance.json`, `20261017k-persistence-acceptance.json`,
  `20261017k-host-boundary-acceptance.json` in `dist/diagnostics/`, with copies
  in the release folder. The GUI was reopened normally after reboot; Image
  remains selected. It is left idle on Capture Session, Start proxy enabled
  (`dist/diagnostics/20261017k-ready.png`). Inspect fresh state before input;
  the user may start using it.
  Release notes, candidate manifest, and `SHA256SUMS` are complete. All 17
  listed release artifacts validate after the clean-host addition. Production
  publication is not claimed; clean-host verification is recorded above.
  Cross-artifact readiness audit also passes: all 79 archived source entries
  match the worktree, release setup matches its source, exact component versions
  match the capture export, and all 17 release files are covered by checksums
  (`dist/diagnostics/20261017k-readiness-audit.json`). The supplied second host
  resolved the prior testing gate without requiring a scope waiver.
- Project-only cleanup removed 26 superseded OVA/build-output copies after
  checking registered disk dependencies: 92.13 GiB recovered, E: free space
  108.23 GiB. Exact paths are recorded in
  `dist/diagnostics/cleanup-superseded-builds-20261017.json`. Source, captures,
  registered VM disks, and current `h`/`i`/`j` artifacts were preserved.
- Final cleanup subsequently removed superseded `h`/`i`/unversioned OVA
  packages and seven checked temporary build/clean bundles. Combined E: space
  recovered is **100.79 GiB**, with **114.11 GiB free**; final cleanup also
  recovered 19.37 GiB on C:. Exact additional paths/status are recorded in
  `dist/diagnostics/cleanup-final-builds-20261017.json`. The final release,
  fallback `j` OVA, all captures, source, and registered VM disks are preserved.
  Temporary `k` OVF/VMDK bundles were removed only after release checksum and
  live import verification; use the final release OVA as the retained image.
  The project fixture server and confirmed stale project Packer processes were
  stopped. Only `tzMCP Capture` was running at the final VM inventory; other
  registered machines were not deleted or modified during this cleanup.

### Historical build notes (superseded by the state above)

- User requires project-only disk cleanup before handoff: E: has become nearly
  full during appliance work. Remove confirmed disposable build outputs,
  superseded appliance packages, and test VM disks after checking dependencies.
  Preserve source, user captures, evidence needed for the handoff, and the final
  working appliance. Do not delete unrelated files or start another large build
  on E:. A read-only inventory found 72.8 GiB in repository `dist/`, plus several
  older `output-tzMCP-appliance-*` folders of roughly 3.6–4.2 GiB each; registered
  VM storage outside the repository still needs inspection before cleanup.

- Latest verified working VM: `tzMCP-appliance-20261017f-acceptance`. It has
  saved Image-only rules and completed Firefox capture, Stop, and host export:
  six images, 1,307,339 bytes, all eight archive hashes valid. It was powered
  off when rechecked; its saved configuration and disk remain available.
- Build `20261017g` completed. Its expanded offline audit passes the raw
  account-marker, identity, seed, and journal checks, but fails empty logs:
  shutdown recreated `/var/log/sysstat/sa17` (2,968 bytes). Do not promote it
  as a clean release image. The finalizer now stops and runtime-masks sysstat;
  that change requires a new build and completed offline audit.
- Firefox-launch and CA-import failure checks passed on the dedicated
  `tzMCP-failure-20261017` VM. Each showed the actual error and exported the
  original captured image with matching SHA-256 and valid archive manifest.
- Approval review is available again. The dedicated failure VM was restarted,
  the interrupted test recovered/exported, and its old filler removed.
- A fresh real disk-full test reached zero available bytes and displayed
  ENOSPC in Activity. The original capture exported unchanged, but an empty
  temporary file was also exported. Cleanup and dedup retry fixes now pass
  regression tests; the live gate must be repeated on the new candidate.
  The test filler has been removed and free space restored.
- Intermediate build `20261017h` completed in 16m41s from
  `%TEMP%\tzmcp-appliance-build-20261017h`, using wheel
  `appliance-wheel-20261017h2`. Its packaged OVA SHA-256 is
  `a812f2db386570c7976c62d73dc80729380bfe0915cd8f50c054a580d1854450`.
  The complete offline audit passed: zero raw account markers, empty logs,
  and clean identity, seed, and journal. Its generated decode was removed
  after preserving `dist/diagnostics/20261017h-raw-disk-audit.json`.
  A fresh setup-script import booted Xfce and generated an owner-only CA;
  `20261017h-first-boot-acceptance.json` records its fingerprint. That test VM
  was gracefully shut down after inspection.
  This image includes disk-full cleanup/retry and sysstat finalization fixes
  but predates the final GUI recovery changes.
- Build `20261017i` completed successfully in 16m19s from
  `%TEMP%\tzmcp-appliance-build-20261017i`. Its OVA checksum verifies, but the
  completed audit **fails** with 11 raw build-account markers, all confirmed in
  free ext4 blocks. Do not import/promote this unsanitized OVA as a clean image.
  Its wheel is
  `dist/appliance-wheel-20261017i/tzmcp-0.0.1-py3-none-any.whl`, SHA-256
  `5ac3f657a9e36b9e0e3fa523c96d49ba1010611a79519bc32e1e48353bf65db5`.
  All 48 modules match current source. Browser/CA startup failures now stop the
  proxy, persist their error, and interrupt the session for export. The GUI
  displays session ID/state/capture totals and prevents a second browser launch
  from replacing the owned Firefox object. These changes require live testing
  on `i`; the older browser-failure results prove only visible errors and
  preservation, not the new automatic interruption behavior.
  Both builds use existing file permissions; no ACL grants were performed.
- Offline `zerofree` on the generated, unmounted `i` filesystem copy removed
  all 11 markers; a complete rescan finds zero. Original artifacts were kept.
  The source-controlled `scripts/release/sanitize-appliance.py` completed the
  original `i` bundle into `%TEMP%\tzmcp-appliance-clean-20261017j`, with
  filesystem checks, zero raw markers, and successful converted-byte comparison.
  The independent source-controlled verifier also passed all residue and
  pristine-layout checks (`dist/diagnostics/20261017j-raw-disk-audit.json`).
  Sanitized VMDK SHA-256:
  `30a53fadc98430a255942278ed951ba8771e692e7b86a0ed1c26fb083d380f2b`.
  Packaged `j` OVA SHA-256:
  `cb94a51e5de81e15616f8549731dc57a8b451a4a3f8c7c948daa754bd918ece4`.
  The actual setup-script import is running (tool session `88582`), creating
  `tzMCP-appliance-20261017j-acceptance` with
  `dist/exports-20261017j-acceptance`. Live workflow/failure checks remain open.
  `docs/appliance-build.md` documents this required offline stage.
- The non-shared host-canary test passed under the normal guest account.
  Clean-host import remains unverified: the user confirmed no second PC is
  available. Host-setting invariance, proxy-start failure, and export-failure
  retry have live results. The dedicated failure VM is now powered off after
  cleanup and export, freeing build resources.
- User decision: retain automatic Ubuntu security updates. Windows tests:
  169 passed, 2 symlink checks skipped. Linux Firefox/export security modules:
  10 passed with no skips, including both checks skipped on Windows.

## Purpose of this document

This is the durable implementation and handoff plan for turning tzMCP into a
Windows-first VirtualBox appliance. It is intended to survive an interrupted
conversation and to give another developer or AI enough context to continue
without reconstructing the product decisions.

This document is a plan, not a record of completed work. Check an item only
after its implementation and verification are complete. Before resuming:

1. Read `AGENTS.md`.
2. Read this document in full.
3. Run `git status --short` and preserve unrelated user changes.
4. Inspect the current implementation and tests named by the next work package.
5. Use `codebase_memory` narrowly when available.
6. Implement one work package at a time and update this document as decisions
   are confirmed.

## Goal

Replace the supported native-browser workflow with a reproducibly built
VirtualBox appliance. Users import the appliance, browse entirely inside its
Firefox instance, capture through a guest-loopback mitmproxy process, end the
capture explicitly, and export one completed session through a controlled host
folder.

The appliance is the supported end-user product. Native execution remains a
developer facility. The first appliance release retains the Tk GUI, CLI,
configuration format, and existing media-capture pipeline.

## Agreed product decisions

- Keep the Tk GUI for appliance v1.
- Treat the GUI as the appliance's control panel, not as part of the capture
  engine.
- Put all session, proxy, browser, recovery, and export behavior behind
  non-Tk service classes so the GUI can be replaced later.
- Replace portable-browser selection in appliance mode with:
  **Start Session -> Launch Firefox -> End Session -> Export Session**.
- Retain portable-browser modules and native CLI support for development, but
  retire them from supported end-user documentation and release packaging.
- Firefox is the only supported appliance browser in v1.
- Keep captures inside the VM until the user explicitly exports an ended or
  interrupted session.
- Use SHA-256 manifests for integrity checking. They do not establish identity
  or authenticity; report signing remains out of scope.
- Update tzMCP itself only through versioned appliance releases. Guest security
  and Firefox updates may continue, and every exported session records exact
  component versions.

## Why the GUI remains

The GUI is not technically required by mitmproxy or the capture pipeline. It
remains because it gives nontechnical users one clear, recoverable workflow
while reusing the existing Tk application.

In appliance mode the GUI will:

- edit capture filters while no session is running;
- start a session and show its identifier and state;
- start mitmproxy with the session's immutable configuration snapshot;
- create and launch the temporary Firefox profile;
- show capture activity and actionable failures;
- stop Firefox and mitmproxy and finalize session metadata;
- recover and export interrupted sessions;
- export a completed package through the controlled shared folder.

The GUI will no longer select, add, remove, or acknowledge portable browsers in
appliance mode. It must not contain the state-machine logic itself.

```text
Tk GUI
  |
  v
SessionManager
  +-- ProxyController / mitmproxy addon
  +-- FirefoxSession
  +-- SessionExporter
  +-- appliance export helper
```

The CLI may call the same service classes. Native mode may continue using the
existing reusable browser modules until a later cleanup.

## Explicit non-goals for v1

- Docker or container-based distribution
- web UI
- Chromium or multiple guest browsers
- host-browser integration
- changes to Windows proxy settings or the Windows trust store
- automatic report/catalog generation
- digital signatures or evidence-authenticity claims
- cloud upload or network export
- Authenticode signing before a signing certificate is available
- automatic CI production builds of the OVA

## Current repository baseline

The repository currently has no appliance or Packer directory. Runtime code is
under `src/tzMCP/`; tests are under `tests/`.

Important current seams:

- `src/tzMCP/paths.py`
  - honors `TZMCP_DATA_DIR`;
  - provides `config_dir()`, `logs_dir()`, and `profiles_dir()`.
- `src/tzMCP/gui.py`
  - creates `ConfigManager`, `ProxyController`, `BrowserTab`, `ConfigTab`, and
    `ProxyTab`;
  - stops the proxy and calls global browser cleanup on window close.
- `src/tzMCP/gui_bits/browser_tab.py`
  - implements the current portable-browser workflow.
- `src/tzMCP/gui_bits/browser_launcher.py`
  - creates browser-specific profiles and tracks browser processes globally.
- `src/tzMCP/gui_bits/proxy_control.py`
  - launches `mitmdump` as a subprocess on guest loopback;
  - does not currently pass an explicit mitmproxy CA/config directory.
- `src/tzMCP/cli.py`
  - builds an in-memory configuration and invokes mitmdump.
- `src/tzMCP/save_media.py`
  - constructs a global `MediaSaver` addon at import time;
  - reloads the default YAML file from `config_dir()` and watches it;
  - therefore CLI overrides are not yet an authoritative addon input.
- `src/tzMCP/gui_bits/config_manager.py`
  - owns the existing YAML-compatible `Config` dataclass and validation.
- `src/tzMCP/save_media_utils/save_media_utils.py`
  - owns filename/path checks and atomic file saving; do not weaken them.
- `pyproject.toml`
  - exposes `tzMCP-cli` and `tzMCP-gui`;
  - currently declares version `0.0.1`;
  - currently has an empty runtime dependency list while dependencies are
    pinned in `requirements.txt`. Packaging must resolve this before the wheel
    is installed into the appliance.

Existing tests cover configuration, CLI merging, paths, hashing, save helpers,
basic GUI source behavior, and mocked `MediaSaver.response()` flows. There are
not yet tests for session lifecycle, live process management, Firefox profile
creation, CA import, exports, or appliance assets.

## Security and compatibility invariants

These are acceptance constraints, not implementation suggestions:

- Bind mitmproxy only to `127.0.0.1` inside the guest.
- Do not alter the host proxy, guest system trust store, or host trust store.
- Trust the mitmproxy CA only in a dedicated per-session Firefox profile.
- Keep the CA private key outside all session and export directories.
- Give CA files owner-only permissions and verify them after creation.
- Treat URLs, HTTP headers, config values, filenames, archive paths, PIDs, and
  shared-folder paths as untrusted input.
- Do not follow symlinks or include special files during export.
- Never delete captured evidence because browser launch, CA import, export, or
  disk operations fail.
- Disable configuration changes and export while a session is running.
- Do not kill a process merely because its PID appears in a stale file; verify
  recorded executable identity and process start time first.
- Preserve existing YAML fields and native CLI behavior unless a change is
  explicitly documented.
- Keep tests isolated with `tmp_path` and existing `tests/conftest.py`
  fixtures. Tests must not touch real config, log, cache, CA, or session paths.
- Keep appliance networking to one NAT adapter with no port forwarding.
- Disable shared clipboard, drag-and-drop, USB passthrough, and automatic
  shared-folder mounting.

## Target runtime data layout

`TZMCP_DATA_DIR` remains authoritative. In the appliance it should point to a
directory owned by the non-administrative `tzmcp` account.

```text
TZMCP_DATA_DIR/
  config/
    media_proxy_config.yaml       # persistent user capture rules
  ca/
    mitmproxy/                    # persistent VM-specific CA; never exported
  sessions/
    20260723T184512Z-a1b2c3d4/
      state.json                  # internal atomic lifecycle record
      capture/                    # captured media
      logs/                       # session-scoped raw/structured logs
      metadata/
        capture-config.yaml       # immutable effective snapshot
        versions.json             # exact component versions
      browser/                    # temporary profile; deleted after end
      staging/                    # local partial export; never archived
  runtime/
    active-session.json           # lock/identity for one active session
    process-records/              # verified PID/start-time records
  export-ready/                   # completed local archives accepted by helper
```

The exact directory names may change during implementation, but the following
boundaries must remain:

- CA material is outside sessions.
- Browser data is segregated from capture data.
- Export staging is segregated from archive payload.
- Persistent user configuration is copied into, not referenced from, a running
  session.
- Only one active session is permitted.

## Session identity and state machine

Use an identifier formed from a UTC timestamp and cryptographically random
suffix, for example `20260723T184512Z-a1b2c3d4`. Validate it against a strict
ASCII pattern before using it in any path.

Persist state atomically after every successful transition:

```text
NEW --------> RUNNING --------> ENDED --------> EXPORTED
 |                |
 |                +-----------> INTERRUPTED --> EXPORTED
 +----------------------------> INTERRUPTED
```

Required transition semantics:

- `NEW`
  - isolated directories and configuration snapshot exist;
  - proxy and Firefox are not yet considered healthy.
- `RUNNING`
  - mitmproxy passed a readiness check;
  - the session owns authoritative process records;
  - configuration is immutable and export is disabled.
- `ENDED`
  - Firefox and mitmproxy are stopped;
  - available metadata, counts, end time, and logs are finalized;
  - temporary Firefox data has been deleted or a cleanup failure is recorded.
- `INTERRUPTED`
  - startup partially failed or a previously running session ended abnormally;
  - captured data is preserved;
  - available metadata is finalized;
  - export is allowed after stale owned processes are dealt with.
- `EXPORTED`
  - an archive was copied successfully and atomically to the host folder;
  - export time, archive name, size, and hash are recorded internally.

Invalid transitions must raise a typed error and leave the prior state intact.
State writes use a temporary sibling file, flush/fsync where supported, and
`os.replace`.

Closing the GUI during `RUNNING` is an abnormal end unless the normal End
Session operation completes. The close handler should attempt orderly shutdown,
but preserve and mark the session `INTERRUPTED` if any required step fails.

## Authoritative configuration flow

The existing CLI/GUI configuration split must be removed before session work is
built on it.

Target flow:

1. Load and validate the persistent YAML configuration.
2. Apply CLI overrides when applicable.
3. At session creation, replace `save_dir` with that session's `capture/`
   directory and disable live reload for the effective snapshot.
4. Write the validated effective configuration to
   `metadata/capture-config.yaml`.
5. Pass that exact file path explicitly to the mitmproxy addon process.
6. Make `MediaSaver` read only that path for the session.

Do not rely on Python module globals crossing a mitmdump script boundary. Do
not let `MediaSaver` silently fall back to the persistent default config when a
session-specific path was requested. A missing or invalid session config is a
proxy-start failure.

The native CLI should use the same explicit launch specification so its
overrides actually reach the addon. Appliance runs should not watch the
persistent config file. Native auto-reload may remain available outside
appliance mode.

## Firefox and CA lifecycle

For each session:

1. Locate the appliance-managed Firefox executable; do not accept a GUI path.
2. Create a new profile inside the session's `browser/` directory.
3. Write only that profile's proxy preferences for `127.0.0.1:<port>`.
4. Initialize its NSS certificate database with `certutil`.
5. Import the public mitmproxy CA certificate with a fixed, recognizable
   nickname.
6. Verify the certificate is present before launching Firefox.
7. Launch Firefox with the explicit profile and no profile reuse.
8. Record PID, process start time, executable, Firefox version, and profile
   path.
9. On End Session, request termination, wait, then terminate/kill only the
   verified owned process tree if necessary.
10. Delete the profile after Firefox is fully stopped.

The appliance CA:

- is unique per installed VM;
- is generated on first boot, never during the image build;
- lives under `TZMCP_DATA_DIR/ca/mitmproxy`;
- is passed to mitmproxy as its explicit `confdir`;
- is not placed in the guest system trust store;
- is not present in the OVA;
- is never included in a session archive.

If CA import or Firefox launch fails, retain the session, logs, and configuration
snapshot and move it to `INTERRUPTED`. Profile cleanup may continue, but capture
data must not be removed.

## Recovery and stale-process handling

At appliance GUI startup:

1. Acquire a single-instance/runtime lock.
2. Read `active-session.json`, if present.
3. Validate the referenced session ID and paths.
4. For each recorded process, compare PID, executable identity, owner, and
   process start time.
5. Stop only a verified process belonging to the recorded session.
6. Finalize the session as `INTERRUPTED`.
7. Attempt browser-profile cleanup after the process is stopped.
8. Leave captured files intact and offer export.

Recovery must be idempotent. A corrupt state file is quarantined or reported,
not silently overwritten. The UI must explain what was recovered and what
requires manual attention.

## Export package and helper boundary

### Archive contents

Create one ZIP64 archive after an `ENDED` or `INTERRUPTED` session:

```text
<session-id>/
  capture/...
  logs/...                       # sanitized session logs
  capture-config.yaml
  session.json
  SHA256SUMS
```

`session.json` records:

- schema version;
- session ID;
- UTC start, end, and export times;
- completion state (`ENDED` or `INTERRUPTED`);
- tzMCP version;
- appliance image version;
- Ubuntu version;
- Firefox version;
- mitmproxy version;
- effective filters and proxy port;
- captured file count and total bytes;
- warning/error summary;
- archive format/version information.

Do not include:

- Firefox profile, cookies, history, credentials, cache, or local storage;
- mitmproxy CA certificate or private key;
- raw browser data;
- temporary, partial, lock, PID, database-journal, or staging files;
- unrelated application configuration, sessions, logs, or state;
- absolute guest paths.

### Integrity and archive safety

- Enable ZIP64 explicitly.
- Enumerate allowed payload roots; do not archive an entire session directory
  by exclusion alone.
- Resolve and validate every source path under its allowed root.
- Reject symlinks, hard-link surprises where detectable, device files, FIFOs,
  sockets, and archive member names containing absolute paths or `..`.
- Use normalized POSIX archive names and deterministic lexical ordering.
- Generate `SHA256SUMS` for every payload member except `SHA256SUMS` itself.
- Hash the exact bytes placed into the archive.
- Ensure `session.json` and the configuration snapshot are covered.
- Sanitize credentials, authorization headers, cookies, and sensitive URL query
  values from exported logs. Prefer structured capture-time sanitization, with
  export-time defense in depth.
- Write locally as `<name>.partial`, flush, close, verify, and atomically rename.
- On disk-full or write failure, remove only the partial export artifact; retain
  all session evidence and state.

### Privileged export helper

The regular `tzmcp` account must not receive general mount privileges.
Provision a small root-owned helper callable through one narrowly scoped
privilege rule. The helper must:

- accept only a validated archive already under the fixed `export-ready/`
  directory;
- use a fixed VirtualBox share name, `tzmcp-export`;
- mount only at a fixed directory such as `/run/tzmcp-export`;
- mount with restrictive options including `nosuid`, `nodev`, and `noexec`;
- reject symlinked source/destination components;
- copy one archive using a partial destination and atomic rename;
- fsync where supported;
- unmount in a `finally` path;
- return structured success/failure information to the GUI.

Export is disabled until Firefox and mitmproxy are stopped. Failure to mount or
copy must leave the local completed archive available for retry.

## Proposed code organization

Prefer small service modules and retain existing module boundaries:

```text
src/tzMCP/
  appliance.py                    # env detection and appliance metadata
  sessions/
    __init__.py
    models.py                     # SessionState and serialized records
    manager.py                    # lifecycle orchestration and recovery
    storage.py                    # safe paths and atomic JSON/YAML writes
    export.py                     # ZIP64 package creation and verification
    versions.py                   # component-version collection
  browser/
    __init__.py
    firefox_session.py            # appliance Firefox/NSS lifecycle
  gui_bits/
    appliance_session_tab.py      # thin Tk view/controller
    proxy_control.py              # refactored shared process controller
  proxy_runtime.py                # explicit config/addon launch boundary
```

Names may be adjusted to match the implementation, but the service/UI
separation is required. Do not move or delete the existing
`browser_plugins/` modules in this transition.

Likely modifications:

- `src/tzMCP/paths.py`
- `src/tzMCP/cli.py`
- `src/tzMCP/gui.py`
- `src/tzMCP/gui_bits/config_manager.py`
- `src/tzMCP/gui_bits/config_tab.py`
- `src/tzMCP/gui_bits/proxy_control.py`
- `src/tzMCP/save_media.py`
- `src/tzMCP/common_utils/log_config.py`
- `pyproject.toml`
- `requirements.txt`
- `config/media_proxy_config.yaml` only if a compatible default changes

## Appliance and release file layout

Proposed new repository structure:

```text
appliance/
  packer/
    tzmcp.pkr.hcl
    variables.pkr.hcl
    ubuntu/
      http/
        user-data
        meta-data
  provisioning/
    install-base.sh
    install-tzmcp.sh
    configure-desktop.sh
    configure-security.sh
    install-export-helper.sh
    first-boot.sh
    scrub-image.sh
  files/
    tzmcp.desktop
    tzmcp-first-boot.service
    tzmcp-export-helper
    appliance-version
  scripts/
    validate-image.sh
scripts/
  windows/
    Setup-tzMCP.ps1
  release/
    build-appliance.ps1
    generate-checksums.py
```

Do not commit generated OVA, ISO, wheel, checksum output, or build secrets.

## Phased implementation

### Phase 0 — resolve design/build prerequisites

Decisions confirmed for the initial implementation: appliance versions are
carried independently in `TZMCP_APPLIANCE_VERSION` (defaulting to
`development`), while the Python package version remains separate; pinned
runtime dependencies are declared in both `requirements.txt` and wheel
metadata; the target desktop is Xfce with LightDM; Firefox is image-managed;
and mitmproxy receives `--set confdir=<TZMCP_DATA_DIR>/ca/mitmproxy`. The
remaining schema and privileged-helper decisions are intentionally deferred to
the session/export phases.

- [x] Confirm the appliance versioning scheme independently from Python package
      versioning.
- [x] Decide how runtime Python dependencies become wheel metadata or otherwise
      install reproducibly from pinned artifacts.
- [x] Select the lightweight desktop package set (recommended starting point:
      Xfce + LightDM) and document why.
- [x] Confirm Ubuntu's Firefox packaging and executable/profile behavior in the
      target image.
- [x] Confirm the exact mitmproxy `confdir` invocation for the pinned version.
- [ ] Define JSON schemas and schema-version fields for internal state and
      exported `session.json`.
- [ ] Define the root-owned export helper interface and privilege rule before
      implementing GUI export.
- [x] Record final decisions in this document or an ADR.

Exit gate: no unresolved decision changes the session data model, trust
boundary, or build toolchain.

### Phase 1 — appliance mode, paths, and authoritative proxy configuration

- [x] Add strict `TZMCP_APPLIANCE` parsing (`1` enables; absent/other documented
      values preserve native mode).
- [x] Extend path helpers for sessions, CA, runtime, and export-ready roots.
- [x] Add safe directory creation and permission checks.
- [x] Refactor `MediaSaver` so an explicit config path is authoritative.
- [x] Refactor GUI and CLI proxy launches to use the same launch specification.
- [x] Pass loopback host, validated port, session config, log location, and CA
      `confdir` explicitly.
- [x] Preserve native auto-reload behavior only where intended.
- [x] Add proxy readiness/failure detection rather than treating `Popen`
      success as proxy readiness.

Tests:

- [x] appliance environment parsing;
- [x] path isolation under `TZMCP_DATA_DIR`;
- [x] CLI overrides observed through `build_config` and the explicit addon
      snapshot path (`tests/unit/test_cli.py` and
      `tests/integration/test_media_saver_response.py`);
- [x] GUI-equivalent selected port and filter configuration observed by the
      addon, while persistent settings remain unchanged
      (`tests/integration/test_media_saver_response.py`);
- [x] invalid/missing explicit config fails closed;
- [x] proxy command binds loopback and includes the explicit CA directory.

Exit gate: passed. The integration test loads a session snapshot through
`MediaSaver`, verifies its MIME and domain filters affect real response
handling, and confirms persistent configuration is unchanged.

### Phase 2 — session model, storage, and recovery

The initial service-layer implementation is present in `src/tzMCP/sessions/`.
It currently covers strict IDs, isolated layout creation, atomic state files,
the transition table, one-active-session locking, capture counting, recovery,
and PID/executable/owner/start-time verification. GUI/proxy orchestration and
failure-injection coverage remain to be completed in this phase.

The native GUI now creates a session before starting its proxy, points the
proxy at the session's immutable `metadata/capture-config.yaml`, transitions
successful starts to `RUNNING`, finalizes normal stops as `ENDED`, and marks
GUI-close or startup failures as `INTERRUPTED`. Browser process ownership and
the appliance-specific Firefox workflow remain later work.

The managed browser service is now present in `src/tzMCP/browser/`. It creates
fresh per-session Firefox profiles, writes loopback-only preferences, imports
and verifies the public CA with `certutil`, launches with `-no-remote`, and
refuses to terminate a process whose executable, owner, or start time no longer
matches its recorded identity. Appliance GUI wiring and first-boot CA
generation remain open.

Appliance-mode GUI sessions now use this service and hide the portable-browser
selection controls. Runtime roots are created with owner-only permissions at
appliance GUI/CLI startup. First-boot provisioning still needs to create the
CA before the application starts, and the release image must supply the
managed Firefox executable and `certutil`.

Initial provisioning assets are now present under `appliance/`: a first-boot
systemd service/script creates private runtime roots and generates the
VM-specific CA outside the image build, and a desktop launcher starts the GUI
with `TZMCP_APPLIANCE=1`. Packer image construction, account provisioning, and
manual VM verification remain open.

The initial Packer source and unattended Ubuntu seed are now present under
`appliance/packer/`, with pinned Ubuntu 24.04.4 live-server ISO metadata, 2 CPU /
4096 MB / 60 GB defaults, NAT-only networking, disabled clipboard/drag-and-drop
/USB, and provisioning hooks for the desktop, application wheel, security
scrub, and first-boot service. Packer validation and an actual clean build have
not yet been run on a maintainer machine.

The Ubuntu 24.04.4 appliance provisioning path installs Firefox explicitly as
the Ubuntu Snap after the base APT transaction, with seed readiness and retry
handling. This avoids coupling the complete desktop package transaction to
Snapd startup/watchdog timing; the exact Firefox snap revision remains part of
the recorded image manifest.

Initial Phase 7 release tooling is now present: `scripts/windows/Setup-tzMCP.ps1`
verifies VirtualBox 7.1+, validates the OVA hash before import, applies the
NAT-only and disabled-integration settings, adds the non-automounted export
share, and starts only after configuration. The release scripts also provide
Packer validation/build orchestration and deterministic SHA-256 manifest
generation. Live Windows/VirtualBox execution remains manual acceptance work.

The maintainer build currently produces an OVF bundle; `scripts/release/package-ova.ps1`
packages its OVF descriptor and virtual disk into the distributable OVA, after
which the checksum generator can create the published sidecar/manifest.

The README now identifies the appliance as the target end-user workflow while
clearly stating that no production OVA is currently published.
`docs/appliance.md` documents installation, first capture, export verification,
recovery, persistence, and the host/guest security boundary; native setup
remains marked developer-only.

Initial Phase 9 source validation is now present in
`.github/workflows/appliance-validation.yml`: it runs the Python suite,
ShellCheck, Packer formatting, plugin initialization, and Packer validation
without producing an OVA. Release checksum generation now has a matching
manifest validator. CI and maintainer-machine execution still need to record
their real results before the transition can be called complete.

The initial secure export implementation is now present in
`src/tzMCP/sessions/export.py`: it allow-lists capture/log/metadata payloads,
rejects symlinks and special/multiply-linked files, sanitizes sensitive logs,
creates deterministic ZIP64 archives and manifests, and uses partial-file plus
atomic-rename semantics. The root-owned helper and sudoers installation are
present under `appliance/`; GUI export integration and live mount/disk-full
tests remain open.

Export is now exposed through the appliance capture tab only after the proxy
and Firefox stop. The GUI creates/reuses the local archive, invokes the helper
with only its validated basename, records `EXPORTED` only after structured
success, and leaves a failed local archive available for retry. Live Tk/helper
integration and mount/disk-full acceptance remain manual work.

Export metadata now records collected tzMCP, appliance, Python, mitmproxy,
Ubuntu, and Firefox versions, plus effective capture settings with the session
path removed from `session.json`.

- [x] Implement `SessionState` and validated records. (`sessions/models.py`)
- [x] Implement unique ID generation and safe session paths. (`sessions/storage.py`)
- [x] Implement atomic state writes. (`storage.py` uses `tempfile.mkstemp` +
      `fsync` + `os.replace`)
- [x] Implement the transition table and typed errors. (`sessions/manager.py`)
- [x] Snapshot effective configuration into the session. (GUI writes the
      session's immutable `metadata/capture-config.yaml` before proxy start)
- [x] Add one-active-session locking.
- [x] Store verified process identity records. (`sessions/processes.py`)
- [x] Implement idempotent interrupted-session recovery. (`recover_active`,
      wired into GUI startup)
- [x] Count captures and bytes without trusting filenames.
      (`manager._count_capture_files` stats the actual capture dir)

Tests:

- [x] every allowed and rejected state transition
      (`test_sessions.py::test_invalid_transitions_are_rejected_without_state_change`);
- [x] collision-resistant IDs and isolated directories
      (`test_sessions.py::test_session_ids_are_strict`);
- [x] corrupt/partial active state is preserved and recovery refuses to erase
      its marker or captures (`test_corrupt_active_state_is_preserved_for_recovery`);
- [x] interrupted-session recovery
      (`test_sessions.py::test_recovery_is_idempotent_and_preserves_capture`);
- [x] PID reuse and unrelated-process protection
      (`test_session_processes.py::test_process_identity_requires_executable_owner_and_start_time`);
- [x] simulated disk-full failures preserve the old state, clean temporary
      files, retain active recovery metadata, and release a failed initialization
      lock (`test_sessions.py` failure-injection tests);
- [x] persistent configuration remains unchanged by session overrides
      (`test_explicit_session_snapshot_controls_addon_without_changing_saved_config`).

Exit gate: simulated crashes at each lifecycle point preserve capture files and
produce a recoverable `INTERRUPTED` session.

### Phase 3 — managed Firefox and private CA

- [ ] Add first-boot CA generation outside the image build.
- [ ] Enforce/verify owner-only CA permissions.
- [ ] Create a fresh Firefox profile per session.
- [ ] Write per-profile loopback proxy preferences.
- [ ] Initialize the NSS database and import only the public CA.
- [ ] Verify CA presence before browser launch.
- [ ] Launch Firefox with explicit no-reuse profile arguments.
- [ ] Stop only the owned Firefox process tree.
- [ ] Remove the profile after session end and during recovery.
- [ ] Record cleanup failures without deleting evidence.

Tests:

- [ ] profile paths are unique and reset between sessions;
- [ ] expected proxy preferences only;
- [ ] `certutil` command and verification failures;
- [ ] Firefox launch failure -> `INTERRUPTED`;
- [ ] owned-process termination and unrelated-process protection;
- [ ] profile cleanup after normal and abnormal ends;
- [ ] CA paths cannot enter export roots.

Exit gate: two consecutive sessions have independent browser storage, both use
the VM-specific CA, and neither trusts it outside its profile.

### Phase 4 — GUI appliance workflow

- [ ] Add an appliance-specific capture-session tab or appliance presentation
      mode for the existing tab.
- [ ] Present Start Session, Launch Firefox, End Session, and Export Session in
      state-dependent order.
- [ ] Remove portable-browser controls and acknowledgement in appliance mode.
- [ ] Keep current native browser UI available only in native/developer mode.
- [ ] Disable capture-rule editing while `RUNNING`.
- [ ] Disable export while proxy or Firefox is running.
- [ ] Display current session ID/state, capture counts, and actionable errors.
- [ ] Make GUI close use `SessionManager` shutdown/recovery semantics.
- [ ] Offer export for a recovered interrupted session.

Tests should exercise view-model/controller behavior without launching a real
Tk desktop where possible. Keep Tk callbacks thin and unit-test the underlying
state.

Exit gate: the GUI cannot issue an invalid transition or bypass configuration
and export locks.

### Phase 5 — secure ZIP64 export

- [ ] Implement allow-list archive enumeration.
- [ ] Implement path/type/symlink validation.
- [ ] Implement log sanitization.
- [ ] Build `session.json` from finalized state and exact component versions.
- [ ] Build deterministic, complete `SHA256SUMS`.
- [ ] Write, flush, atomically rename, and verify the local ZIP64 archive.
- [ ] Implement retry-safe disk-full and interruption behavior.
- [ ] Add the constrained privileged mount/copy/unmount helper.
- [ ] Integrate helper results into the GUI.

Tests:

- [ ] normal and interrupted session exports;
- [ ] deterministic member ordering and manifest coverage;
- [ ] recomputed SHA-256 verification;
- [ ] traversal, absolute path, symlink, and special-file rejection;
- [ ] explicit CA/browser/temp exclusion;
- [ ] sensitive log-data redaction;
- [ ] ZIP64 capability, plus a marked large-file integration test where
      practical;
- [ ] local and destination disk-full failures;
- [ ] atomic local staging and atomic host copy;
- [ ] mount/copy failure always attempts unmount;
- [ ] helper rejects arbitrary source, destination, share, and mount paths.

Exit gate: an independent verifier can unpack a completed archive, recompute
every listed hash, and find no browser or CA material.

### Phase 6 — reproducible VirtualBox appliance

- [ ] Add a Packer 1.14+ VirtualBox ISO builder.
- [ ] Pin the official Ubuntu 24.04 LTS ISO URL and SHA-256 checksum.
- [ ] Use an ephemeral build account for Packer provisioning.
- [ ] Create the non-administrative `tzmcp` desktop account.
- [ ] Install the lightweight desktop, Firefox, Python 3.12 venv, pinned tzMCP
      wheel/dependencies, mitmproxy, `libnss3-tools`, and Guest Additions.
- [ ] Install the desktop launcher, first-boot service, and export helper.
- [ ] Disable/remove SSH after provisioning.
- [ ] Configure one NAT adapter and no port forwarding.
- [ ] Disable clipboard, drag-and-drop, USB, and automatic shared-folder mounts.
- [ ] Set defaults: 1 CPU, 4096 MB RAM, dynamic 60 GB disk. The one-CPU
      default avoids a reproducible guest RCU stall with two CPUs on the
      development host; revisit after testing other host configurations.
- [ ] Make first boot generate the VM-specific CA and any non-user Firefox
      profile template.
- [ ] Scrub build credentials, SSH keys, machine ID, CA material, evidence,
      logs, shell history, package caches, and temporary files.
- [ ] Emit a Packer build manifest and OVA.

Build-time checks:

- [ ] Packer formatting and validation;
- [ ] provisioning-script static checks;
- [ ] no build account or authorized keys remain;
- [ ] no CA/private key, session, capture, or browser profile remains;
- [ ] expected service enable/disable state;
- [ ] expected ownership and permissions.

Exit gate: two clean builds boot successfully and generate different first-boot
CA fingerprints.

### Phase 7 — Windows setup and release artifacts

- [ ] Add readable `Setup-tzMCP.ps1`.
- [ ] Verify installed VirtualBox version is at least 7.1.
- [ ] Verify the OVA checksum before import.
- [ ] Import with a configurable VM name.
- [ ] Apply/verify NAT-only networking and disabled integration features.
- [ ] Create the host export directory, defaulting to
      `%USERPROFILE%\Documents\tzMCP Exports`.
- [ ] Add the `tzmcp-export` shared folder without automount.
- [ ] Allow CPU, memory, disk-size, VM-name, and export-path overrides before
      first boot.
- [ ] Launch the VM only after post-import verification passes.
- [ ] Add release tooling for the OVA, setup PowerShell source, Packer manifest,
      appliance manifest, and SHA-256 checksums.
- [ ] Document the controlled-maintainer-machine release procedure.

The setup script must be idempotent or stop with a clear conflict message. It
must not modify host browser configuration, host proxy settings, or trust
stores.

Exit gate: a clean supported Windows host can verify, import, configure, and
start the appliance using only published release artifacts.

### Phase 8 — documentation and supported-workflow transition

- [ ] Rewrite the README around the OVA workflow.
- [ ] Add appliance installation, first-session, export, verification,
      troubleshooting, update, and security-boundary documentation.
- [ ] Mark portable-browser/native setup documents as developer-only or archive
      them without breaking useful historical links.
- [ ] Explain that HTTPS is decrypted inside the VM and caution against entering
      sensitive credentials during capture.
- [ ] Explain what persists: configuration, completed captures, session state,
      and VM CA.
- [ ] Explain what does not persist between sessions: cookies, history,
      credentials, cache, local storage, and temporary browser profile.
- [ ] Explain SHA-256 integrity versus cryptographic authenticity.
- [ ] Document recovery and retry after disk-full/export failures.

Exit gate: the supported end-user docs never instruct users to configure a host
browser, host proxy, host CA trust, or portable browser.

### Phase 9 — CI and final verification

- [ ] Add CI jobs for the complete Python suite.
- [x] Validate Packer formatting/configuration without producing an OVA
      (`packer fmt -check appliance/packer`; `packer validate` with the
      existing wheel and validation-only required credentials).
- [ ] Validate shell and PowerShell sources with pinned tooling.
- [ ] Test release-manifest/checksum generation.
- [x] Run the complete Python test suite locally (**175 passed, 2 skipped**;
      symlink-dependent tests skipped on this Windows filesystem).
- [ ] Run the manual appliance acceptance matrix below.
- [ ] Review the final diff for scope, secrets, generated artifacts, and
      accidental native-workflow regressions.

## Manual appliance acceptance matrix

These checks require VirtualBox and cannot be claimed from Python tests alone:

- [x] Clean Windows host imports the OVA with the setup script. Windows 11 Pro
      build 26300, VirtualBox 7.2.18, Windows PowerShell 5.1; actual capture,
      export, reboot, runtime hashes, unique CA, and host-boundary checks passed.
      See release `clean-host-acceptance.json` and current resume notes above.
- [x] VM has one NAT adapter, no port forwarding, and no other adapters.
- [x] SSH is masked and inactive in the running guest.
- [x] Shared clipboard, drag-and-drop, USB, and automount are disabled.
- [x] Windows setup disables VirtualBox VRDE before starting the VM.
- [x] XFCE Internet-menu entry starts tzMCP in appliance mode
      (`dist/diagnostics/20261017-desktop-launcher.png`).
- [x] Managed Firefox reaches an HTTPS page through mitmproxy without a
      certificate warning (`dist/diagnostics/20261017-firefox-second-tab.png`);
      its profile routes SSL to loopback and imports the appliance CA.
- [x] Captures land only in the active session (live run
      `20261017T042151Z-c59cb129`; six media files in its archive).
- [x] Saving Image-only rules in the open GUI applies them to the next session
      without restarting the app; the `20261017c` export records Image,
      10,240-byte minimum, and 301x301 minimum dimensions.
- [x] End Session stops Firefox and mitmproxy and removes the profile.
- [x] Export creates one archive in the chosen host folder
      (`dist/exports-20261017-acceptance/20261017T042151Z-c59cb129.zip`).
- [x] All eight `SHA256SUMS` entries in that archive verify independently.
- [x] Host browser configuration, Windows proxy, and Windows trust store remain
      unchanged: all 27 recorded before/after digests match for the `20261017d`
      import, capture, interrupted startup, and export-retry workflow.
- [x] A non-shared host-file canary is inaccessible under the normal guest
      account: all six read attempts fail, only the intended export folder is
      configured as a share, and the host canary hash is unchanged
      (`dist/diagnostics/20261017-host-private-acceptance.json`). This tests the
      configured sharing boundary, not unknown hypervisor vulnerabilities.
- [x] Cookies, history, credentials, cache, and local storage do not survive a
      second session: the active profile was inside its unique session directory
      (`dist/diagnostics/20261017-profile-active.png`); after Stop, the same
      directory search returned no paths and no Firefox process remained
      (`dist/diagnostics/20261017-profile-cleaned.png`,
      `dist/diagnostics/20261017-firefox-process-after-end.png`).
- [x] Saved non-default Image MIME capture configuration survives reboot; the
      YAML SHA-256 is unchanged (`0a98018b83da16b01d09662bc38423cee930c49b256aa12eddea6f8189a1b3fb`)
      and Image remains enabled in Capture Rules after relaunch.
- [x] Completed session records and the VM CA survive reboot; all three session
      states remain `EXPORTED` and the CA fingerprint is unchanged.
- [x] Forced GUI/VM termination recovers the session as `INTERRUPTED` and the
      GUI exports it through the host share.
- [x] Proxy-start failure is visible, produces an exportable interrupted
      session, and persists its actionable error in the exported metadata
      (`20261017T101508Z-bf0b9721.zip`).
- [x] A missing host export folder produces a visible export error and retains
      the local archive and six captured images. Restoring the folder and
      retrying publishes the identical archive (`20261017T101744Z-248be41a.zip`).
- [x] Firefox-launch failure is visible and preserves evidence
      (`dist/diagnostics/20261017-firefox-launch-acceptance.json`).
- [x] CA-import failure is visible and preserves evidence
      (`dist/diagnostics/20261017-ca-import-acceptance.json`).
- [x] Disk-full failures are visible and preserve evidence: `j` reached zero
      free bytes, retained the first capture, removed partial output, saved the
      failed image on retry, and deduplicated only after a successful save
      (`dist/diagnostics/20261017j-disk-full-acceptance.json`).
- [x] Idle guest listeners are loopback DNS and the tzMCP GUI log receiver,
      plus the NAT DHCP client; no SSH or externally bound service appears
      (`dist/diagnostics/20261017-all-listeners.png`).
- [x] `tzmcp` is non-admin and both CA files are `tzmcp:tzmcp` mode `600`.
- [x] Two independently initialized appliances have different CA fingerprints:
      `20261016g` = `DC:82:AC:D6:31:4E:69:E4:48:71:6A:DC:7A:14:4B:AA:10:AE:14:52:3B:56:3E:A4:1F:E7:0A:A4:2B:6B:A8:55`;
      `20261016i` = `5F:53:2C:1C:75:AF:1B:96:3F:61:89:AA:52:8E:50:16:D8:5C:D2:DD:20:5B:6A:26:73:E3:C5:EB:15:67:89:F7`
      (`dist/diagnostics/20261017-ca-fingerprint-g.png` and
      `dist/diagnostics/20261017-ca-fingerprint-i.png`).
- [x] Sanitized `j` OVA contains no build-time CA, credentials, logs, captures,
      shell history, machine identity, or SSH material: complete raw scan and
      filesystem checks pass in
      `dist/diagnostics/20261017j-raw-disk-audit.json`. Every later candidate
      requires its own completed sanitation and independent audit.

## Release contents

Each versioned release should publish:

- OVA;
- `Setup-tzMCP.ps1`;
- Packer/build manifest;
- appliance component/version manifest;
- PowerShell and provisioning sources, directly or by source tag;
- `SHA256SUMS` covering every published artifact;
- release notes with known limitations and manual verification result.

Production OVAs are built on a controlled maintainer machine initially. CI
validates sources and artifact-generation logic but does not claim to have built
or verified the production OVA.

## Open decisions

Resolve these in Phase 0 and replace each item with the decision:

- [ ] Exact appliance-version scheme and its relationship to Python package
      version `0.0.1`.
- [ ] Exact lightweight desktop package set.
- [ ] Exact Firefox source/package used in Ubuntu 24.04 and update policy.
- [ ] Whether native CLI receives session commands in v1 or only shares the
      lower-level proxy configuration path.
- [ ] Whether a successfully exported session may be re-exported, and how a
      second export is represented without weakening the state model.
- [ ] Export-name collision policy on the host.
- [ ] Log schema and precise sanitization fields.
- [ ] Internal JSON schema details and forward-compatibility policy.
- [ ] Privileged helper implementation language and authorization mechanism.
- [x] Keep automatic Ubuntu security updates enabled by default (user decision,
      2026-10-17). Update tzMCP itself through versioned appliance releases;
      record exact component versions with every exported session.

## Definition of done

The transition is complete only when:

- the appliance workflow is the documented supported workflow;
- all service logic is usable independently of Tk;
- session transitions, recovery, Firefox isolation, CA handling, config
  authority, and export security have focused automated tests;
- the complete Python suite passes;
- Packer, provisioning, PowerShell, and artifact logic validate;
- two clean appliances demonstrate unique first-boot CAs and no build residue;
- the full Windows/VirtualBox acceptance matrix has recorded results;
- release artifacts and checksums are generated reproducibly;
- remaining limitations are explicit and no unverified result is presented as
  complete.

## Handoff status

As of 2026-08-19 (paused for a Claude usage-limit reset; resume ~2026-08-22):

- Product direction is agreed. Retaining the Tk GUI as an appliance control
  panel is agreed.
- Work is on branch `feature/virtualbox-appliance-transition` (created from
  `main` at commit `271c43f`), **not** on `main`. All Python implementation
  that used to sit uncommitted in the working tree is now committed there in
  6 reviewable commits: appliance-mode plumbing, session service layer,
  managed-browser/Firefox isolation, GUI wiring, appliance/Packer
  provisioning + CI, and release tooling. Local unit suite: **120 passed, 1
  skipped** (skip is symlink support, expected on Windows).
- Contrary to what this doc said as of 2026-07-23, GUI/proxy/session/export
  integration is **not** open — it is implemented and committed (see Phase 2
  checklist above and Phase 4/5 code references). That earlier status line
  was stale relative to the working tree; this pass corrected the Phase 2
  checkboxes against the actual code and tests. Phases 3/4/5 checklists below
  have not yet received the same line-by-line reconciliation pass — treat
  their unchecked boxes with the same suspicion until re-verified.
- `.gitignore` now excludes `packer_cache/`, `*.iso`, and
  `VirtualBoxVM_*.png`. Two multi-GB Ubuntu ISOs and a stray VM debug
  screenshot were sitting untracked in the repo root; they were never staged
  or committed, just newly ignored. They still exist on disk if needed for a
  local Packer build.
- Checked for secrets before committing: `appliance/packer/variables.pkr.hcl`
  and `scripts/release/build-appliance.ps1` require `build_password` /
  `build_password_hash` as caller-supplied arguments with no default and a
  placeholder guard — nothing sensitive is checked in.
- A prior manual build attempt (recorded in
  `2026-07-23-virtualbox-appliance-transition-handoff.md`) produced
  `dist/tzMCP-appliance.ova`, which VirtualBox could import but which booted
  to a terminal instead of Xfce (LightDM failed; suspected 4MB VRAM). That
  fix (VRAM → 128MB, explicit LightDM enable) is in the committed provisioning
  scripts but was never baked into a rebuilt OVA. **That VM
  (`tzMCP-appliance`) no longer exists in `VBoxManage list vms`** — the old
  handoff note's "power off and modify the running VM" steps are dead; do not
  follow them.

### Historical next actions (superseded by the verification update below)

The August resume steps below describe the state before the October build and
end-to-end verification. Do not follow them as current instructions. Remaining
work is listed in the verification update below.

1. Re-import `dist/tzMCP-appliance.ova` (the old build, still on disk),
   `VBoxManage modifyvm <name> --vram 128`, then `VBoxManage startvm --type
   headless` and `VBoxManage controlvm <name> screenshotpng out.png` to check
   whether it now reaches the Xfce desktop without needing a full rebuild —
   this splits the VRAM-vs-LightDM-config hypothesis in minutes.
   - If it boots to desktop: VRAM was the whole problem; a rebuild is just to
     bake the fix into the distributable OVA.
   - If it still drops to a terminal: capture `journalctl -u lightdm -b`
     (`VBoxManage guestcontrol` may not work since `tzmcp` uses passwordless
     auto-login with no known guestcontrol credential — may need a
     first-boot log dump to the shared folder instead).
2. Only after a booting appliance is confirmed: rebuild the OVA via
   `scripts/release/build-appliance.ps1`, re-import via
   `scripts/windows/Setup-tzMCP.ps1`, and start recording results against the
   "Manual appliance acceptance matrix" below (currently entirely unchecked).
3. Reconcile Phase 3/4/5/6 checkboxes against code the same way Phase 2 was
   just reconciled above — in particular, `appliance/files/tzmcp-export-helper`
   and `install-export-helper.sh` already exist, and `sessions/export.py`
   already does log sanitization and `sessions/versions.py` already does
   schema/version recording, so several "Open decisions" items below are
   likely already answered by existing code, not actually open — verify and
   record rather than re-deciding them.
4. The one open decision that's a genuine product/security call rather than
   something already implemented: whether the appliance permits automatic
   Ubuntu security updates by default. Surface that one to the user; don't
   guess it.

### Verification update (2026-10-16)

The worktree is on `feature/virtualbox-appliance-transition`. The current test
artifact is `dist/tzMCP-appliance-20261016e.ova`. It passes checksum
verification, imports with `scripts/windows/Setup-tzMCP.ps1`, and reaches the
Xfce desktop at 1024x768. The imported VM uses VBoxSVGA and NAT-only
networking, with clipboard, drag-and-drop, and USB disabled and the export
share attached. Its first-boot terminal shortcut works after adding
`xfce4-terminal` to the base package set.

The full primary workflow has now been exercised on the `e` image: tzMCP opens
in appliance mode, starts its loopback proxy, launches managed Firefox to
`http://mitm.it`, captures a host-served test PNG through the proxy, stops
Firefox from the GUI, and exports a ZIP through the shared-folder helper. The
exported PNG hash matches the source file, all nine `SHA256SUMS` entries
verify, and the archive contains no Firefox profile or CA private key. Stop
also passed an independent check that no session profile directory or process
using it remains. This test exposed a Snap launcher identity change; cleanup
now finds the Firefox process by the exact private profile path and owner
before verifying its fresh PID identity. A separate unit test covers the
already-exited-browser case.

Build and code checks: Packer format/validate passed; the full Python suite
passed (**137 passed, 2 skipped**); Ruff passed on the changed source/tests;
OVA packaging, checksum verification, and VirtualBox import passed; and
`git diff --check` passed. The image finalizer ran before export. The local
OVA remains a test artifact, not a published production release.

The broader manual acceptance matrix remains incomplete. Still unverified are
independent first-boot CA fingerprints across two appliances, non-shared host
file isolation, host browser/proxy/trust-store invariance, persistent state
across reboot, forced-interruption recovery, disk-full and other failure
paths, and finalized service/credential inspection. Several design and phase
checklists earlier in this document also remain unchecked and need a focused
reconciliation pass before calling the transition complete.

### Verification update (continued, 2026-10-16)

The `20261016f` build adds a post-shutdown Packer step to disable VRDE, and the
Windows setup script now disables VRDE before VM startup. The packaged OVA and
SHA-256 sidecar were generated and validated. A fresh setup-script import
confirmed `vrde="off"`, NAT on adapter 1 only, clipboard and drag-and-drop
disabled, USB off, and the export share attached. The VM launch command
reported success and the VirtualBox log reached X11 at 1024x768, but the VM
reported powered off by the first follow-up check. The reason is unresolved;
keep the desktop/first-boot acceptance items open until a stable running check
passes.

The full Python suite remains green (**137 passed, 2 skipped**), including an
integration check that loads the effective GUI session snapshot through
`MediaSaver`, observes its MIME/domain filters on real response handling, and
confirms persistent settings are unchanged.

### Verification update (continued, session failure handling)

Session-state persistence now publishes the active-session pointer atomically,
releases the startup lock after initialization failures, and keeps active
recovery metadata until a terminal state has been written successfully.
Failure-injection tests confirm that partial state writes and simulated
disk-full errors preserve the prior state and captures; corrupt active state
is left intact for diagnosis. The full suite now passes (**142 passed, 2
skipped**). These tests cover local state handling, not VM-level disk exhaustion
or export failures; those manual checks remain open.

### Verification update (continued, VirtualBox runtime diagnosis)

A headless retry also failed to establish a stable running state. The host log
recorded the guest entering `Running` and emitting X11 display events at
1024x768, but VBoxManage later reported the VM `aborted` and rejected a
screenshot request. A VirtualBox process chain remained after the API reported
the VM stopped; its parent IDs matched the test VM launch in `VBoxSVC.log`.
Those processes were cleared after verifying the VM was no longer running.
The guest shutdown/abort cause remains unknown, so keep the live-appliance
acceptance incomplete.

### Verification update (continued, 2026-10-17)

The `20261016g` appliance passed a live capture/export exercise: the guest
Firefox loaded a host-loopback fixture through the guest NAT path, the proxy
saved the image with a matching SHA-256, and the exported ZIP passed all eight
manifest checks. The archive contained session metadata and no Firefox profile
or CA private key.

That exercise exposed a GUI recovery handoff defect: startup recovery returned
an interrupted session but the browser tab never received it, leaving export
unavailable. The GUI now restores the recovered record and gates Start/Export
by session state. Unit coverage was added. The full suite passes (**144 passed,
2 skipped**); Ruff was unavailable in the environment, and `git diff --check`
passes.

The corrected `20261016i` OVA was built, checksummed, imported through the
Windows setup script, and reached a stable Xfce desktop with the intended
isolation settings. The original verification VM later entered an aborted
VirtualBox state, so a fresh import was used for the recovery acceptance test.
On the fresh VM, tzMCP started a session, VirtualBox forced power-off, and the
rebooted GUI recovered it as interrupted with Start disabled and Export
enabled. Export produced one ZIP for that session in the configured host
folder. Both `SHA256SUMS` entries verified; the ZIP contains the interrupted
session metadata and configuration, with no browser profile or CA private key.
After publication the GUI disabled Export and re-enabled Start. A follow-up
ended session also exported as a second ZIP; its two manifest entries verified
and it contained no browser profile or CA private key. The fresh VM remains
running at its clean tzMCP capture screen with the expected NAT-only, VRDE-off,
clipboard/drag-and-drop/USB-off configuration.

Further checks on the same import confirmed the XFCE Internet-menu launcher,
managed Firefox HTTPS rendering without a certificate warning, a non-root
`tzmcp` account, mode-`600` CA certificate/key ownership, masked/inactive SSH,
and only loopback application/DNS listeners plus the NAT DHCP client. Two
separately initialized appliances have distinct SHA-256 CA fingerprints. A
clean reboot preserved the CA fingerprint and all three `EXPORTED` session
records. After saving the Image MIME rule in Capture Rules, a second clean
reboot preserved the config file hash
`0a98018b83da16b01d09662bc38423cee930c49b256aa12eddea6f8189a1b3fb`; the GUI
reloaded Image as enabled.

The manual acceptance matrix remains incomplete: file isolation across
appliances, host browser/proxy/trust-store invariance,
browser-data cleanup, disk-full and other failure paths, and a clean-host
import still need verification. The automatic Ubuntu
security-update policy also remains a product decision.
The `20261016i` OVA is a local test artifact, not a production release. The
full Python suite passes (**145 passed, 2 skipped**).

### Verification update (continued, 2026-10-17 live appliance)

The running `20261016i` import completed another end-to-end GUI session using
the saved Image-only capture rules. Managed Firefox loaded `http://mitm.it`;
the ended session contained six image captures (1,307,339 bytes). Stop removed
the unique Firefox profile and left no Firefox process. Export created
`dist/exports-20261017-acceptance/20261017T042151Z-c59cb129.zip`; all eight
manifest entries independently matched SHA-256. The VM remains running at the
idle Capture Session screen with Start proxy enabled.

Local checks on this worktree: Packer formatting and configuration validation
passed without building an OVA. An automated GUI regression test now verifies
that a host-share publication failure leaves the local archive intact, keeps
the session ended and exportable, and shows an error. The full Python suite
passed (**147 passed, 2 skipped**); symlink-dependent tests were skipped on
this Windows filesystem. `git diff --check` passed. Clean-host import,
host-setting invariance, guest file isolation, runtime failure-path checks,
and OVA residue inspection remain open.

### Verification update (continued, 2026-10-17 rebuilt appliance)

The session archive review found that `capture-config.yaml` still exposed the
guest's absolute session `save_dir`. The exporter now removes that field while
preserving the effective capture rules, with regression coverage for the
archive contents. The GUI also has regression coverage confirming that a host
share publication failure preserves the local archive and leaves the session
retryable. The full suite passes (**147 passed, 2 skipped**); `git diff
--check` passes.

Packer formatting and validation passed, and a new `20261017b` OVA was built
from the updated wheel, packaged, and checksum-validated. Its SHA-256 is
`3087f66dd30c6a01fa01c7be6f44cd24664e2fca39a23ff39a112b6f6f484b55`. The
Windows setup import completed with NAT-only networking and host integration
features disabled. The guest reached the Xfce desktop; appliance-mode tzMCP
started its loopback proxy and managed Firefox loaded `mitm.it` plus Mozilla's
first-run privacy page.

The fresh `20261017b` VM completed an end-to-end export. A metadata-only
session archive verified both manifest hashes and confirmed that neither
`capture-config.yaml` nor `session.json` contains the absolute guest session
path. A second run loaded the built-in `http://mitm.it` page and captured eight
images totaling 1,313,360 bytes. All ten manifest entries in
`dist/exports-20261017b-acceptance/20261017T051718Z-31fdde6a.zip` independently
matched SHA-256; the archive config omits `save_dir`. The test temporarily set
lower image thresholds to capture the local page's small assets; afterward,
the GUI saved the normal minimum file size (10,240 bytes) and minimum image
dimensions (301 by 301) with Image still enabled. The appliance remains
running at its idle Capture Session screen with Start proxy enabled. Its
settings show 4,096 MB RAM, one CPU, NAT-only networking, clipboard and
drag-and-drop disabled, USB off, and VRDE off.

Static review of `scripts/windows/Setup-tzMCP.ps1` confirms its host-side
actions are limited to validating the OVA, importing/configuring/starting the
VirtualBox VM, and creating the selected export directory; it contains no
browser, proxy, or certificate-store writes. The `20261017` and `20261017b`
acceptance VMs map `tzmcp-export` to separate host folders. This supports the
intended boundary and export separation, but does not replace a measured
before/after host settings comparison or a clean-host import.

Read-only checks inside the imported `20261017b` guest show only the `tzmcp`
home under `/home`; the `tzmcp-build` account and home are absent. SSH is
masked and inactive. After Stop, no Firefox process remained and the managed
Firefox profile root was empty. TCP listeners were limited to loopback DNS
and the tzMCP GUI. These checks support build-residue and browser-cleanup
acceptance, but do not inspect every file in the raw OVA disk image.

The broader clean-host, host-setting, file-isolation, runtime-failure, and
OVA-residue checks remain open. The automatic Ubuntu security-update policy
remains a product decision.

### Verification update (continued, 2026-10-17 live config refresh)

The `20261017c` rebuild was imported into VirtualBox and reached the Xfce
desktop. The first GUI session was useful as a control: it exported an empty
MIME group list because the Image rule had not actually been saved. After
explicitly clicking Image and Save Configuration, the GUI reported a
successful save. Without restarting tzMCP, a second session loaded
`http://mitm.it`, captured six images totaling 1,307,339 bytes, stopped the
managed browser and proxy, and exported
`dist/exports-20261017c-acceptance/20261017T091816Z-5727afbc.zip`.

The second archive's `session.json` records `allowed_mime_groups: ["image"]`,
`filter_file_size.min_bytes: 10240`, and image minimum width/height of 301.
All eight `SHA256SUMS` entries independently match. The archive contains no
Firefox profile or CA files and no absolute guest session path. This verifies
the saved-config handoff in the rebuilt appliance, in addition to the unit
regression test. The full Python suite passes (**148 passed, 2 skipped**);
the two skips require symlink support unavailable on this Windows filesystem.
Packer formatting and validation pass, as does `git diff --check`. The
previous empty-rule archive is retained as a failed operator interaction and
is not used as acceptance evidence. The acceptance VM remains running at the
idle Capture Session screen.

An idle-state guest inspection confirmed the application runs as `uid=1001`
(`tzmcp`) with only `tzmcp`, `audio`, and `video` groups. No `vboxsf` mount was
present; `/run/tzmcp-export`, the helper's fixed mount point, was not mounted.
`sudo -n -l` showed only the root-owned `tzmcp-export-helper *` command is
allowed without a password. This supports the host-share boundary but does not
by itself prove that arbitrary non-shared host files are inaccessible.

The same inspection found `unattended-upgrades.service`, `apt-daily.timer`, and
`apt-daily-upgrade.timer` enabled, with APT periodic package-list updates and
unattended upgrades set to `1`. The current image therefore applies Ubuntu
updates automatically; the product decision is whether to keep that default.

Clean-host import, measured host browser/proxy/trust-store invariance, guest
access to non-shared host files, VM-level failure-path checks, raw OVA residue
inspection, and the Ubuntu security-update policy remain open.

### Verification update (continued, proxy-start diagnostics)

A controlled port conflict in the `20261017c` guest made Start proxy report
`Port 8888 is already in use`. The resulting interrupted session remained
exportable, but its exported `errors` array was empty. After removing the
temporary loopback HTTP server, starting the proxy succeeded again.

The current source now persists the proxy-start error before marking the
session interrupted and sanitizes errors when exporting session metadata.
Regression tests cover error persistence, the interrupted/exportable GUI
state, restored persistent configuration, and redaction of sensitive error
content. The complete Python suite passes (**151 passed, 2 skipped**); the
skips require Windows symlink support, and pytest reports a cache-permission
warning. This source change still requires verification in a rebuilt OVA.

The tested wheel is
`dist/appliance-wheel-20261017d/tzmcp-0.0.1-py3-none-any.whl`, SHA-256
`51a6f0237cc352512cb25b1a3d034e2e53d506cefc1229f165c839cea091f769`.
Its changed runtime modules match the current source byte-for-byte. This
canonical filename and explicitly readable artifact directory avoid the
earlier failed builds caused by wheel permissions and an invalid wheel
basename. Packer formatting and validation pass. ShellCheck 0.9.0 passes for
all provisioning scripts, the export helper, and the display-mode helper;
the PowerShell sources parse successfully, and `git diff --check` passes.

The `20261017d` Packer rebuild is in progress. Hashed host proxy, browser
configuration, and trust-store baselines were recorded before its import in
`dist/diagnostics/20261017d-host-before.json`; these are baseline observations,
not a completed before/after acceptance check.

### Verification update (continued, offline residue audit and update policy)

The user confirmed that automatic Ubuntu security updates should remain
enabled. The appliance guide and open-decision checklist now record that
decision; tzMCP application upgrades still use versioned appliance releases.

A read-only offline inspection of the exported `20261017c` VMDK found the
deleted build account in `/etc/passwd-`, `/etc/shadow-`, `/etc/group-`, and
`/etc/gshadow-`. The earlier running-guest account check did not cover those
backup files. The audit report records presence flags only, never password
hashes: `dist/diagnostics/20261017c-raw-disk-audit.json`. Its temporary decoded
filesystem has been removed; the source image was never modified.

The finalizer now removes account-database backups and the cloud-init sudoers
entry, clears build logs, and overwrites free filesystem space before export
so deleted installer credentials are not retained in free blocks. Focused
tests verify that only ENOSPC is accepted as the end of zero-filling, other
storage errors propagate, and a preexisting file is never removed. The full
suite passes (**154 passed, 2 skipped**), ShellCheck passes, and
`git diff --check` passes.

The `20261017d` build completed before the finalizer change was uploaded. Its
OVA SHA-256 is
`61ad64ee4cd55d8c96270b6afebda41a445557f53c74f6b488f55549a4e8de36`.
It is an intermediate diagnostic-test artifact, not the residue-cleaned
candidate. The `20261017e` Packer rebuild includes the new finalizer from the
start and remains in progress. Its raw-disk audit and live acceptance are
still required.

### Verification update (continued, live diagnostics and export retry)

The `20261017d` acceptance VM imported successfully through the Windows setup
script. A controlled loopback server occupying port 8888 produced a visible
proxy-start error and an exportable interrupted session. Its archive,
`dist/exports-20261017d-acceptance/20261017T101508Z-bf0b9721.zip`, records
`Proxy startup failed: Port 8888 is already in use.` Both manifest entries
verify, with no browser/CA members or absolute guest data paths. The temporary
server was stopped only after verifying its recorded PID's exact command.

Without restarting tzMCP, Image-only rules were saved, the proxy started, and
managed Firefox loaded `http://mitm.it`. Stop ended Firefox and the proxy.
Temporarily renaming this VM's host export folder caused the expected visible
`mount.vboxsf` missing-directory error. The guest retained the ended session,
six captures totaling 1,307,339 bytes, and the completed local archive. After
the folder was immediately restored, retry exported
`dist/exports-20261017d-acceptance/20261017T101744Z-248be41a.zip`. Its SHA-256,
`7462260526812e76fc1d9dddc9fae926da3a23712c9a2958a50b2efc6676c70b`, matches
the hash measured inside the guest before retry. All eight manifest entries
verify. Image-only rules are present in the archive; browser/CA data and
absolute guest data paths are absent.

The host baseline comparison after that workflow found zero differences
across 27 digests: Internet Settings/connection proxy configuration, WinHTTP,
HTTP/HTTPS browser associations, browser policies and proxy preferences,
Firefox configuration files, and user/machine Root, CA, TrustedPeople, and
TrustedPublisher stores. Evidence is in
`dist/diagnostics/20261017d-host-before.json` and
`dist/diagnostics/20261017d-host-after.json`. This verifies those measured
settings on the development host; a clean-host import is still open.

### Verification update (continued, fresh `e` workflow and deeper residue scan)

The `20261017e` OVA built and passed checksum validation. Its SHA-256 is
`e98f65f306edab390ccec3c3918d74ff01e3c725c4b91818e348e5678f895809`.
The setup script imported it into `tzMCP-appliance-20261017e-acceptance` with
its own `dist/exports-20261017e-acceptance` host folder. The guest reached Xfce,
and the Internet-menu launcher opened tzMCP. Image-only rules were saved in
the GUI. The proxy started, Firefox loaded `http://mitm.it`, and Stop ended
the browser and proxy. Export produced
`20261017T103938Z-07e1d436.zip` containing six images totaling 1,307,339 bytes.
All eight manifest entries verify, and its effective rules record Image,
10,240-byte minimum size, and 301x301 minimum dimensions. Browser/CA members
and absolute guest data paths are absent. Archive SHA-256 is
`56966bbd32b448b4dde281624cb1e4a3f3f94a9c308097f4c6ad2ada7ad52eef`.
The independent report is `dist/diagnostics/20261017e-live-acceptance.json`.
All 27 before/after host-boundary digests also match for this fresh workflow.

The offline `e` audit verified that the account-database backups no longer
contain the build account and that the installed finalizer matches its
intended source (`1d4b2f5c6320ff7a9ee8b8e098637187cf770cc43331ac5250a35af455d7ba05`).
The deeper raw scan nevertheless found five `tzmcp-build:` markers in blocks
6866316, 6866318, 6866320, 6866322, and 6866324. `debugfs testb` confirms all
five are free blocks, not current files or the filesystem journal. Thus the
first free-space fill did not prove complete erasure. The audit also found
that shutdown had recreated the random-seed file and log entries, and that a
persistent journal directory retained the build machine identity. The complete
report is `dist/diagnostics/20261017e-raw-disk-audit.json`; no account contents
or password hashes are printed in it. `e` remains an intermediate test image.

The finalizer now stops syslog socket activation, shutdown accounting, and
random-seed persistence before cleanup; switches journald to volatile
storage; removes persistent journal identity and random-seed data; resets the
DBus machine-ID symlink; and commits preceding deletes with `sync` before
allocating the free-space fill file. That ordering must still be verified
against the five residual blocks in a newly built artifact. The current
finalizer source SHA-256 is
`de0b70d7eb415d5855dd1ba49843fd9274560e6dd7bf56d634205ae3dc40f033`.
Packer now permits ten minutes for finalization before shutdown timeout.

The initial decoded `e` audit file on E: exhausted host free space. Only that
generated temporary raw file was removed, recovering about 48 GB; original
OVAs, VM disks, and captured sessions were preserved. Both acceptance VMs
remained running. The successful repeat audit used the Linux temp filesystem
on C:, and that decoded temporary filesystem was removed after preserving its
report. Future full-disk decodes must use the temp drive with a space preflight.

The `20261017f` rebuild is running from
`%TEMP%\tzmcp-appliance-build-20261017f`, with its output under
`output-tzMCP-appliance-20261017f` there, not in the repository. It reuses the
tested wheel and cached ISO. The build checked that its temp drive had at
least 100 GiB available. Do not restart it solely because installer output is
quiet. Before promoting its OVA, verify the installed finalizer SHA-256 and rerun the
offline account-marker, identity, log, and free-block checks. Its artifact
acceptance is unproven while the build is running.

An additional live `d` guest check confirmed that direct `vboxsf` mounting is
root-only, arbitrary sudo commands require a password, an export-helper
`../outside.zip` argument is rejected as `invalid_archive_name`, and no shared
folder remains mounted while idle. These checks support the host-file boundary
but do not replace the still-open non-shared-host-file acceptance item.

### Verification update (continued, `f` raw scan and final accounting write)

The `20261017f` build completed from the temp-drive output directory. Its OVA
SHA-256 is
`9ebf9d2b59998899498197487bc7ce58584346c2e7eaa3abf61a5375432abe0f`.
The expanded read-only audit verifies the installed finalizer SHA-256 matches
`de0b70d7eb415d5855dd1ba49843fd9274560e6dd7bf56d634205ae3dc40f033`.
The complete decoded-filesystem scan finds **zero** `tzmcp-build:` markers.
Account-database and cloud-init sudoers checks are clean. `/etc/machine-id`
is empty, the DBus ID is its symlink, the random seed is absent, and the
persistent journal directory is empty.

The audit deliberately still returns failure: `/var/log/wtmp` contains one
384-byte record. Binary inspection identifies type 8 (`DEAD_PROCESS`) for
`tty1`, with an empty user label. All other inspected log files are empty.
The report is `dist/diagnostics/20261017f-raw-disk-audit.json`; its decoded
temporary filesystem was removed afterward. This confirms the credential,
identity, seed, and journal fixes but does not close the complete residue gate.

The finalizer now stops `getty@tty1.service` before truncating accounting and
applies runtime-only masks to that getty and both systemd utmp writer units.
The masks live under `/run`, so normal console/accounting behavior resumes
on the appliance's first boot. The current finalizer source SHA-256 is
`3084f16efda5f674ac5971860d3b24b96aaa1493536a7b736c13d94ebf8a6b74`.
ShellCheck and Packer formatting/validation pass; the full Python suite has
**154 passed, 2 skipped** (Windows symlink support), with the known pytest
cache-permission warning.

The `20261017g` build is running in
`%TEMP%\tzmcp-appliance-build-20261017g`, with output under
`output-tzMCP-appliance-20261017g` there. It uses the same tested wheel and
cached ISO and checks temp-drive capacity before starting. Its final raw
account-marker, identity, journal, seed, and empty-log checks remain unproven
until the completed disk is inspected. The `f` OVA was imported into
`tzMCP-appliance-20261017f-acceptance`; its desktop launcher opens tzMCP,
Image-only rules have been saved, and a live capture test is in progress.

### Verification update (continued, `f` live capture and Linux symlink checks)

The `f` appliance completed its fresh desktop workflow. Managed Firefox loaded
`http://mitm.it` and the HTTPS Mozilla Firefox privacy page without a
certificate warning (`dist/diagnostics/20261017f-firefox-https.png`). Stop
ended Firefox and the proxy. Export produced
`dist/exports-20261017f-acceptance/20261017T110109Z-ebf60355.zip`, containing
six images totaling 1,307,339 bytes. Its SHA-256 is
`6be0b6662c98366f8c1206002b627f665cfb172088804d99d702c9ad369e3dda`.
All eight manifest entries independently verify; Image-only rules, the
10,240-byte minimum, and 301x301 minimum dimensions are recorded. Browser/CA
members and absolute guest data paths are absent. The independent report is
`dist/diagnostics/20261017f-live-acceptance.json`. All 27 measured host-boundary
digests match before and after this workflow. The VM is running and idle with
Start proxy enabled (`dist/diagnostics/20261017f-ready.png`).

The Windows command `venv\Scripts\pytest.exe -q -p no:cacheprovider` passes
with **154 passed, 2 skipped**. The two skips were then covered on Linux:
`tests/unit/test_firefox_session.py` and `tests/unit/test_session_export.py`
pass with **10 passed, no skips**, using an isolated temporary WSL venv with
the repository's pinned pytest, PyYAML, Pillow, psutil, and requests versions.
`TZMCP_DATA_DIR` was explicitly pointed at a temporary test directory before
importing the application. This verifies actual launcher-symlink preservation
and export-symlink rejection rather than counting the Windows skips as passes.

The older `d` and `e` acceptance VMs have shut down gracefully. The `f` VM
remains running at its ready screen. The `g` build remains live and has
uploaded the finalizer matching the current `3084f16e...` source, completed
package provisioning, and reached graceful shutdown before export. Its
runtime getty/utmp mask and final artifact audit still require verification.
Recheck actual VM/process state when resuming. Do not power off the working
`f` VM without first checking whether the user has started a new session.

### Verification update (continued, failure tests and next wheel)

The completed `g` offline audit has zero raw build-account markers and clean
identity, seed, and journal checks, but its full residue gate fails because
`/var/log/sysstat/sa17` has 2,968 bytes. The unbuilt finalizer now stops and
runtime-masks the sysstat service and timers before clearing logs. Its SHA-256
is `77874d1771310a685c4390298f010c9acd507a0b012064eebb8e8bfce7ac66a3`.

The dedicated failure VM completed two live failure checks. A missing Firefox
executable produced its exact visible error; a controlled certutil wrapper
produced `Controlled-CA-import-failure`. Both sessions exported one original
666,974-byte fixture image with matching SHA-256 and all three manifest entries
valid. Evidence reports are `20261017-firefox-launch-acceptance.json` and
`20261017-ca-import-acceptance.json` under `dist/diagnostics/`.

For disk-full acceptance, the normal GUI was relaunched, its proxy started,
and the original fixture was requested successfully. The reviewed bounded
helper was downloaded and started in the dedicated guest. It writes only the
exclusive `/home/tzmcp/tzmcp-disk-full-test.bin` file. Its completion, the
second-image failed save, filler removal, and recovery/export remain unverified.
The VM windows subsequently disappeared from the current UI inventory.
Automatic approval review failed due to an account usage limit before a
read-only CLI inspection could execute. Resume by inspecting actual VM state;
do not assume the disk is full or the guest is still running.

A focused regression test independently demonstrated that `atomic_save`
left a partial temporary file when `write` raised ENOSPC. The temporary path
is now recorded before writing, so existing cleanup can remove that partial
file. The test verifies the prior capture remains unchanged. The full command
`venv\Scripts\pytest.exe -q -p no:cacheprovider` passes with **155 passed,
2 skipped** (Windows symlinks unavailable); `git diff --check` passes.

The next immutable runtime wheel is
`dist/appliance-wheel-20261017h/tzmcp-0.0.1-py3-none-any.whl`, SHA-256
`bdfa2f09413e11eb6e3ef853dc5f0675ea8a15dc587862ae6f1d6e317ab23c81`.
All 48 packaged Python modules match current source byte-for-byte. It includes
the partial-file cleanup fix; no OVA contains that fix yet. Build `h` has not
started. Revalidate capacity, review availability, and current guest activity
before building or operating the VMs. Keep automatic Ubuntu security updates,
as confirmed by the user.

### Verification update (continued, full-disk findings and final candidate)

After approval review became available, both earlier VMs were confirmed powered
off. The failure VM was restarted. Its interrupted helper had left a
48,351,936,512-byte filler with 2.5 GiB still available, so that run was not a
completed disk-full test. The exact test-owned filler was removed after checking
its path, ownership, and non-symlink type. The GUI recovered/exported session
`20261017T113358Z-21dce69b`; its original fixture and all three hashes verify.

A fresh test used bounded `posix_fallocate` allocation and confirmed zero
available guest bytes. Requesting the distinct second PNG displayed ENOSPC in
the GUI Activity tab. Removing the exact filler restored 51,009,535,616 bytes.
The resulting `20261017T153623Z-c308178f.zip` preserved the original image and
all four manifest hashes verify, but it also contained an empty temporary file.
This is recorded as a failed acceptance result, not a pass, in
`dist/diagnostics/20261017-disk-full-acceptance.json`.

Two focused fixes follow that evidence: record the temporary path before the
write so partial cleanup can run; and register the SHA-256 dedup hash only after
successful publication. Regression tests reproduce the former leak and verify
same-content retry after ENOSPC with both memory and SQLite deduplication.

Plan review also found that Firefox/CA startup failures did not implement the
specified `INTERRUPTED` transition. They now persist their error, stop owned
browser/proxy resources, and expose the preserved session for export. Focused
tests cover both error paths. A second launch cannot replace the owned Firefox
object. The appliance control panel now displays the session ID, state, file
count, and bytes; live summary reads do not rewrite persisted session state.

The full Windows suite passes with **161 passed, 2 skipped**. Both skipped
symlink checks pass in the Linux Firefox/export modules (**10 passed, no
skips**). All appliance shell scripts/helpers pass ShellCheck; PowerShell
sources parse; Packer validates; `git diff --check` passes. Build `h` contains
the earlier `h2` runtime wheel. Build `i` contains all current runtime fixes,
with 48 wheel modules compared byte-for-byte to source. Poll tool sessions
`30042` and `91900`; no build is proven complete merely by reaching shutdown.

The host-file canary check denied all six normal-guest read attempts, verified
that only the intended export folder is shared, and preserved the host canary
hash. Its scope and evidence are recorded in
`dist/diagnostics/20261017-host-private-acceptance.json`. The dedicated failure
VM was then gracefully powered off. The user confirmed no second Windows PC is
available, so clean-host import remains explicitly unverified. A codebase-memory
ADR update returned `write_error`; this document holds the durable findings.
