# tzMCP VirtualBox Appliance Transition Plan

**Date:** 2026-07-23  
**Status:** Phase 0 and Phase 1 implemented; later phases pending
**Primary platform:** 64-bit Windows host running VirtualBox 7.1+  
**Guest:** Ubuntu 24.04 LTS, x86-64, lightweight desktop, Firefox  
**Application mode:** `TZMCP_APPLIANCE=1`

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
- [ ] CLI overrides observed by the actual addon configuration;
- [ ] GUI-selected port and filter configuration observed by the addon;
- [x] invalid/missing explicit config fails closed;
- [x] proxy command binds loopback and includes the explicit CA directory.

Exit gate: one canonical test proves that the effective GUI/CLI configuration
used to launch the proxy is the configuration loaded by `MediaSaver`.

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
- [ ] corrupt/partial state handling — not covered;
- [x] interrupted-session recovery
      (`test_sessions.py::test_recovery_is_idempotent_and_preserves_capture`);
- [x] PID reuse and unrelated-process protection
      (`test_session_processes.py::test_process_identity_requires_executable_owner_and_start_time`);
- [ ] disk-full/atomic-write failures — atomic-write mechanism exists but has
      no failure-injection test yet;
- [ ] persistent configuration remains unchanged by session overrides — not
      covered.

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
- [ ] Set defaults: 2 CPUs, 4096 MB RAM, dynamic 60 GB disk.
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
- [ ] Validate Packer formatting/configuration without producing an OVA.
- [ ] Validate shell and PowerShell sources with pinned tooling.
- [ ] Test release-manifest/checksum generation.
- [ ] Run the complete Python test suite locally.
- [ ] Run the manual appliance acceptance matrix below.
- [ ] Review the final diff for scope, secrets, generated artifacts, and
      accidental native-workflow regressions.

## Manual appliance acceptance matrix

These checks require VirtualBox and cannot be claimed from Python tests alone:

- [ ] Clean Windows host imports the OVA with the setup script.
- [ ] VM has one NAT adapter, no port forwarding, and no other adapters.
- [ ] SSH is unavailable.
- [ ] Shared clipboard, drag-and-drop, USB, and automount are disabled.
- [ ] Desktop launcher starts tzMCP in appliance mode.
- [ ] Firefox reaches HTTPS sites through mitmproxy without certificate
      warnings.
- [ ] Captures land only in the active session.
- [ ] End Session stops Firefox and mitmproxy and removes the profile.
- [ ] Export creates one archive in the chosen host folder.
- [ ] All `SHA256SUMS` entries verify independently.
- [ ] Host browser, Windows proxy, and Windows trust store remain unchanged.
- [ ] Non-shared host files are inaccessible from the guest.
- [ ] Cookies, history, credentials, cache, and local storage do not survive a
      second session.
- [ ] Persistent configuration, completed sessions, and the VM CA do survive a
      reboot.
- [ ] Forced GUI/VM termination recovers the session as `INTERRUPTED`.
- [ ] Disk-full, Firefox-launch, proxy-start, CA-import, and export failures are
      visible and preserve evidence.
- [ ] Finalized VM inspection finds only intended listening services.
- [ ] `tzmcp` is non-admin and CA permissions are owner-only.
- [ ] Two independently initialized appliances have different CA fingerprints.
- [ ] OVA contains no build-time CA, credentials, logs, captures, shell history,
      machine identity, or SSH material.

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
- [ ] Whether the appliance permits automatic Ubuntu security updates by
      default or exposes an explicit maintenance action.

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

### Next actions on resume, in order

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
