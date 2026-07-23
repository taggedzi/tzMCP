# tzMCP Test Suite — Design

**Date:** 2026-07-22
**Author:** Matthew Craig (with Claude)
**Status:** Approved for planning

## Goal

Give tzMCP its first automated test suite. The immediate driver is confidence
after a round of security dependency bumps (mitmproxy 12.2.2, pillow 12.3.0,
requests 2.33.0, urllib3 2.7.0, pytest 9.0.3, etc.). This first pass covers the
project's pure logic and the mitmproxy addon capture flow. GUI (tkinter), browser
launchers, and a live end-to-end proxy run are explicitly **out of scope** for
this pass.

## Verification result (already done)

Manual smoke testing on the updated dependency set (Python 3.13.7) confirmed:

- All third-party deps and all `tzMCP` modules import cleanly.
- Filename sanitization, MIME/extension detection, sensitive-URL redaction,
  MIME-group filtering, file-size filtering, Content-Length matching, and
  in-memory dedup all behave as designed.

**One pre-existing defect was found** (see "Known defect" below) — the domain
whitelist/blacklist matcher does not honor the regex entries the default config
and CLI docs imply.

## Scope

**In scope (unit):**

- `save_media_utils/save_media_utils.py` — all filter/sanitize/save helpers
- `gui_bits/config_manager.py` — `Config` defaults + `ConfigManager` validation/load/save
- `save_media_utils/hash_tracker.py` — in-memory set mode + SQLite mode
- `cli.py` — `build_config` argument-override merging
- `save_media_utils/gen_whitelist_regex.py` — `smart_regex`

**In scope (integration):**

- `save_media.py` — `MediaSaver.response()` filter pipeline driven by a fake
  mitmproxy flow, constructed without the watchdog observer / real hash DB.

**Out of scope (this pass):** tkinter GUI (`gui.py`, `gui_bits/*_tab.py`,
`proxy_control.py`, `log_server.py`, `status_bar.py`, `browser_launcher.py`),
browser plugin modules, live `mitmdump` execution, `cleanup_logs`/`cleanup_profiles`.

## Architecture

- **Runner:** pytest (already a dev dependency).
- **No install required:** add `[tool.pytest.ini_options]` to `pyproject.toml`
  with `pythonpath = ["src"]` and `testpaths = ["tests"]`, matching how the
  code was smoke-tested (`PYTHONPATH=src`).
- **Layout:**

  ```text
  tests/
    conftest.py                     # shared + autouse fixtures
    unit/
      test_save_media_utils.py
      test_config_manager.py
      test_hash_tracker.py
      test_cli.py
      test_gen_whitelist_regex.py
    integration/
      test_media_saver_response.py
  ```

## Fixtures (`tests/conftest.py`)

All isolation fixtures are **autouse** so ordering cannot leak state.

1. **`reset_config_provider` (autouse):** save and restore
   `config_provider._config_data` around each test; reset to `{}` afterward.
2. **`reset_hash_db` (autouse):** reset `hash_tracker._db` to `None` before/after
   each test; if a SQLite connection is open, close it.
3. **`silence_gui_log` (autouse):** monkeypatch
   `tzMCP.common_utils.log_config.send_log_to_gui` to a no-op so log records do
   not each spawn a `requests.post` thread to `localhost:5001`.
4. **`isolated_config` factory:** returns a `Config` whose `save_dir` is under
   `tmp_path` (created), registered via `config_provider.set_config(...)`.
   Guarantees no test ever touches the real `E:/…/cache`, `config/`, or `logs/`.
   The autouse form sets a default isolated config so bare-`Config()` code paths
   that call `_validate_config`/`is_directory_traversal_attempted` (both `mkdir`)
   never write outside `tmp_path`.
5. **`tiny_png` / `make_png(width, height)`:** generate real PNG bytes via Pillow
   for image-validity and pixel-dimension tests, plus a `not_an_image` bytes blob.
6. **`make_flow(url, content, headers=None)`:** build a fake object shaped like
   `mitmproxy.http.HTTPFlow` (via `types.SimpleNamespace`) exposing
   `request.pretty_url`, `response.content`, and
   `response.headers.get("Content-Length")`.
7. **`config_file` factory:** write a YAML config into `tmp_path` for
   `ConfigManager`/`cli` tests, returning its `Path`.

## Test coverage detail

### `test_save_media_utils.py`

- `sanitize_filename`: illegal chars → `_`; whitespace collapsed; truncation to
  255; Windows reserved name (`CON`) and empty name → `file_<hash>`.
- `safe_filename`: no dot → generated `file_<ts><ext>`; missing ext → ext
  appended; normal name passes through sanitized.
- `detect_mime_and_extension`: URL-extension path (`pic.png` → `image/png`);
  content path (real PNG bytes, no URL → `image/png`); fallback
  (`application/octet-stream`, `.bin`) for unknown bytes and no URL.
- `sanitize_url`: sensitive keys (`token`, `auth`, `session`, `key`,
  `access_token`) → `[REDACTED]`; non-sensitive preserved; blank values kept.
- `is_mime_type_allowed`: allowed group hit → True; type outside groups → False;
  empty `allowed_mime_groups` → False.
- `is_file_size_out_of_bounds`: disabled → False; within bounds → False; below
  min / above max → True.
- `is_domain_blocked_by_whitelist`: empty whitelist allows all (False); matching
  **substring** entry allows (False); non-matching entry blocks (True).
- `is_domain_blacklisted`: empty allows all (False); matching **substring** entry
  blocks (True); non-matching allows (False).
- `is_valid_image`: real PNG → True; garbage bytes → False.
- `is_image_size_out_of_bounds`: within bounds → False; too small / too large →
  True; non-image content handled without raising.
- `does_header_match_size`: `None` → True; equal → True; mismatch → False;
  non-integer header → True (logged, not fatal).
- `is_directory_traversal_attempted`: path inside `save_dir` → False; path
  escaping `save_dir` → True.
- `atomic_save`: writes content to `save_dir`; on name collision appends
  `_1`, `_2`; both files retained with correct bytes.
- `cleanup_temp_file`: removes an existing temp file; no-op / no raise on a
  missing path.

### `test_config_manager.py`

- `Config` dataclass defaults are the documented values.
- `_validate_config`: invalid MIME groups dropped (valid kept); `min_bytes`
  floored at 0; `max_bytes` raised to at least `min_bytes`; pixel dims floored at
  0 and `max_* >= min_*`; unknown `log_level` → `INFO`, lowercase normalized to
  upper; relative `save_dir` resolved to absolute.
- `load_config`: reads YAML and applies keys; `save_dir` becomes a `Path`;
  missing file → defaults (validated).
- `save_config`: writes YAML with `save_dir` serialized as `str`; load→save→load
  round-trip is stable.

### `test_hash_tracker.py`

- `init_hash_db(False)` → set mode: first `is_duplicate` False, second True.
- `init_hash_db(True, db_path=<tmp>)` → SQLite mode: duplicate detection works;
  a fresh connection to the same file still reports a previously seen hash
  (persistence); `shutdown_hash_db` closes the connection.

### `test_cli.py`

- `build_config` with a `Namespace` of all `None`/defaults returns validated
  defaults (using a tmp `--config`).
- Each override applies: `save_dir`, `mime_groups`, `whitelist`, `blacklist`,
  `min_bytes`/`max_bytes` (including `0`, guarded by `is not None`),
  pixel dims, `log_to_file`, `log_level`, `dedup`, `auto_reload=False`.
- `--config` is always a tmp path so the real project config is never read.

### `test_gen_whitelist_regex.py`

- 2-part domain → `re.escape`d literal.
- 3-part non-numeric subdomain → `.*\.<core>`.
- 3-part numeric subdomain → documents the **actual** output including the
  double-escape quirk (regex built then `re.escape`d). Marked with a comment
  linking it to the known matcher defect.

### `test_media_saver_response.py` (integration)

Construct a `MediaSaver` without side effects: patch `_start_watcher` to a no-op,
call `init_hash_db(False)`, and point both `self.config` and
`config_provider.set_config(...)` at the isolated tmp `Config`. Drive
`response()` with `make_flow(...)`:

- Allowed image within all filters → file appears in `save_dir`.
- Disallowed MIME → nothing saved.
- Size out of bounds → nothing saved.
- Blacklisted domain (using a **substring** entry that actually matches) →
  nothing saved.
- Whitelist set and URL not matching → nothing saved.
- Identical content twice → second is skipped as duplicate (one file).
- Content-Length header mismatch → nothing saved.

## Known defect (documented via xfail, not fixed in this pass)

`is_domain_blocked_by_whitelist` / `is_domain_blacklisted`
([save_media_utils.py:145](../../../src/tzMCP/save_media_utils/save_media_utils.py#L145),
[:162](../../../src/tzMCP/save_media_utils/save_media_utils.py#L162)) match with
plain substring containment (`domain in netloc`). The default config ships regex
entries (`ads\..*`, `.*\.doubleclick\.net`) and the CLI advertises "regex or
substring," so the built-in ad-blocking never fires
(`is_domain_blacklisted("http://ads.doubleclick.net/…")` → False).

Per decision, this pass does **not** change the matcher. Instead:

- Passing tests pin the current substring behavior.
- Additional `@pytest.mark.xfail(reason="matcher uses substring, not regex; see
  spec 2026-07-22", strict=True)` tests assert the *intended* regex behavior
  (e.g. default blacklist blocks `ads.doubleclick.net`). These stay red-as-xfail
  until someone fixes the matcher, at which point they flip to xpass and flag the
  fix. This keeps a living record of the bug without blessing it as correct.

The related `smart_regex` double-escaping is noted in the same theme but not
otherwise addressed here.

## Non-goals / notes (not addressed in this pass)

- `pyproject.toml` lists `pytest-qt` as a dev dep, but the GUI is tkinter, not
  Qt — unused. Left as-is; flagged for future cleanup.
- `pyproject.toml` `dependencies = []` means `pip install tzMCP` would not pull
  runtime deps (they live in `requirements.txt`). Out of scope; flagged.

## Success criteria

- `pytest` (via `invoke test`) runs green from a clean checkout with only
  `pip install -e .[dev]` (or the existing venv), no network, no GUI.
- No test reads or writes the real `config/`, `logs/`, or `cache/` directories.
- `invoke coverage` produces a meaningful coverage number for the in-scope
  modules; the xfail tests document the domain-filter defect.
