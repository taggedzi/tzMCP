# AGENTS.md — tzMCP contributor guide

## Project at a glance

tzMCP is a Python 3.12+ GUI/CLI media-capture proxy built on `mitmproxy`.
Runtime code lives in `src/tzMCP/`; tests live in `tests/`. The app handles
untrusted network content and writes files to disk, so correctness and secure
path/content handling take priority over cleverness.

## Work efficiently

- Start with the smallest useful context. Read this file, then use
  `codebase_memory` to retrieve the relevant architecture, conventions,
  decisions, and prior work **when that MCP is available**. Query narrowly by
  feature/module; do not dump the full memory or repository into context.
- If `codebase_memory` is unavailable or insufficient, use targeted searches
  (`rg`) and read only the implementation, tests, config, and docs that affect
  the change. Prefer symbol/file searches to broad recursive reads.
- Reuse findings in a short working summary rather than repeatedly rereading
  files. Store durable, verified architectural decisions and non-obvious
  gotchas in `codebase_memory` when its write/update capability is available.
- Do not use internet research for codebase facts that can be verified locally.
  Use it only when the task needs current external information, and prefer
  primary documentation.
- Keep diffs small and focused. Do not opportunistically reformat, rename, or
  modernize unrelated code in this established codebase.

## Model and effort selection

When the agent environment provides model/effort controls, select the least
expensive capable option:

- Use a high-reasoning/high-effort model for ambiguous requirements, security
  or data-loss risks, architecture decisions, multi-file plans, debugging
  difficult failures, and final review of consequential changes.
- Use a capable low/medium-cost model for bounded implementation, targeted
  tests, mechanical edits, and documentation after the plan is clear.
- Escalate rather than guessing when tests, local evidence, or a low-effort
  pass leave meaningful uncertainty. Do not spend premium reasoning on simple
  retrieval or formatting.

## Planning and execution

- For a small, clearly bounded request, inspect the affected code and tests,
  implement, and verify directly.
- For work spanning multiple modules or involving a behavioral decision, first
  write a compact plan: goal, affected files, compatibility/security concerns,
  validation, and acceptance criteria. Keep it in the task conversation or a
  requested design document; do not create planning artifacts by default.
- Preserve public behavior unless the request explicitly changes it. Treat CLI
  flags, YAML configuration, GUI behavior, saved-file layout, and log formats
  as compatibility surfaces.
- Before editing, inspect nearby code and its existing tests. Extend the
  narrowest relevant test module instead of creating redundant coverage.
- After implementation, review the diff for unintended scope, then run the
  smallest test set that proves the change. Run the full suite for shared
  utilities, configuration, capture pipeline, packaging, or cross-module work.

## Code conventions and safety

- Follow the existing Python style and module boundaries; prefer clear,
  explicit code over new abstractions. Keep imports, names, and error handling
  consistent with the surrounding module.
- Use `pathlib` for file paths. Never weaken filename sanitization, traversal
  checks, MIME validation, file-size/pixel limits, executable safeguards, or
  SHA-256 deduplication without explicit approval and focused tests.
- Network data, HTTP headers, URLs, config values, and browser paths are
  untrusted input. Validate them before using them for file writes, subprocess
  arguments, regexes, or configuration changes.
- Do not make tests touch real `config/`, `logs/`, or `cache/` directories.
  Reuse `tests/conftest.py` isolation fixtures and `tmp_path`/mocks.
- Avoid GUI/browser/proxy integration launches in automated tests unless the
  task specifically requires them; favor unit tests with mocked flows.

## Common commands

```powershell
.\venv\Scripts\pytest.exe
.\venv\Scripts\pytest.exe tests/unit/test_config_manager.py -q
.\venv\Scripts\pytest.exe tests/integration/test_media_saver_response.py -q
.\venv\Scripts\pytest.exe --cov=tzMCP
.\venv\Scripts\python.exe -m tzMCP.cli --help
```

`pyproject.toml` configures pytest with `pythonpath = ["src"]`, so an editable
install is not required to run the suite. Use the repository's `venv`; the
system Python does not contain the project dependencies. Dependencies are
pinned in `requirements.txt`; do not casually change them or add undeclared
runtime dependencies.

## Completion checklist

- The requested behavior is implemented and scoped to the task.
- Relevant tests were added or updated when behavior changed, and appropriate
  tests pass. State exactly what was run and any test not run.
- Documentation/config examples are updated when user-facing behavior changes.
- The final response gives the outcome, key files changed, verification, and
  any remaining risk or follow-up—without claiming unverified results.
- If using `codebase_memory`, record only verified reusable knowledge; do not
  store secrets, personal data, generated output, or speculative conclusions.
