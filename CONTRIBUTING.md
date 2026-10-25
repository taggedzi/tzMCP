# Contributing to tzMCP

Read [AGENTS.md](AGENTS.md) and the [developer and security guide](docs/DEVELOPER_SECURITY_GUIDE.md) before changing code. The [README](README.md) explains the user workflow.

## Report or plan work

Use the repository's [issue chooser](https://github.com/taggedzi/tzMCP/issues/new/choose) for a bug report, feature request, or maintenance/documentation task. Bug reports should include the version, native/appliance setup, expected and actual behavior, and a minimal reproduction. Feature requests and tasks should include observable completion criteria. Search existing issues first and keep shared examples free of private data. For sensitive vulnerabilities, follow [Security findings](#security-findings).

The [pull request template](.github/pull_request_template.md) prompts for the problem, resulting behavior, validation, and compatibility/security impact. Record exact test commands and outcomes, including any checks not run and why.

## Prepare a change

1. Set up the repository virtual environment using the [development setup](docs/DEVELOPER_SECURITY_GUIDE.md#development-setup).
2. Read the affected implementation and nearby tests before editing.

Keep the diff focused. Preserve CLI flags, YAML keys, GUI behavior, saved-file layout, and log formats unless a change is intentional. Discuss changes to security controls or data retention explicitly; do not weaken sanitization, traversal checks, MIME/size limits, executable safeguards, or SHA-256 deduplication incidentally.

## Validate and submit

Run the narrowest relevant tests first. Run the full suite for shared utilities, configuration, capture pipeline, packaging, and cross-module changes:

```powershell
.\venv\Scripts\pytest.exe -q
```

Tests must use temporary directories and mocks rather than real capture data. Do not launch browsers, the GUI, or a live proxy in routine automated tests.

CI runs the full Python suite on Ubuntu 24.04 with Python 3.12/3.13 and on Windows with Python 3.12. Independent appliance checks cover shell sources, wheel construction, and Packer configuration. Keep workflows compatible with the repository policy requiring owner-hosted, SHA-pinned actions; the current workflows use runner tools directly. Production OVA builds and acceptance follow the [maintainer build guide](docs/appliance-build.md).

In the pull request, explain the problem, resulting behavior, tests run, and any remaining limitations. Update the user or technical docs when behavior changes. Review the diff for secrets, private captures, generated images, and unrelated edits before submitting.

## Security findings

Include the affected version, code location, impact, and a minimal reproduction using synthetic data. Never include live credentials, CA private keys, or another person's traffic. For a sensitive vulnerability, contact the maintainer privately through a trusted channel before publishing exploit details; this repository does not define a dedicated private-reporting process.

## License

Contribute only work you own or have permission to share. Contributions are offered under the project's [MIT license](LICENSE).
