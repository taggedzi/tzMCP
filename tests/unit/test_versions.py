from pathlib import Path
from types import SimpleNamespace

from tzMCP.sessions.versions import collect_versions


def test_version_metadata_has_expected_component_labels(monkeypatch):
    monkeypatch.setattr("tzMCP.sessions.versions._package_version", lambda _: "test-version")
    values = collect_versions(Path("missing-firefox"))
    assert set(values) == {"tzMCP", "appliance", "python", "mitmproxy", "ubuntu", "firefox"}
    assert values["tzMCP"] == "test-version"
    assert values["firefox"] == "unknown"


def test_export_after_browser_cleanup_finds_installed_firefox(monkeypatch):
    monkeypatch.setattr("tzMCP.sessions.versions.shutil.which", lambda name: "/snap/bin/firefox")
    commands = []

    def run(command, **_kwargs):
        commands.append(command)
        return SimpleNamespace(returncode=0, stdout="Mozilla Firefox 146.0\n", stderr="")

    monkeypatch.setattr("tzMCP.sessions.versions.subprocess.run", run)

    values = collect_versions()

    assert values["firefox"] == "Mozilla Firefox 146.0"
    assert commands == [[str(Path("/snap/bin/firefox")), "--version"]]


def test_version_collection_does_not_launch_when_firefox_is_absent(monkeypatch):
    monkeypatch.setattr("tzMCP.sessions.versions.shutil.which", lambda name: None)

    def unexpected_run(*_args, **_kwargs):
        raise AssertionError("No browser executable was found")

    monkeypatch.setattr("tzMCP.sessions.versions.subprocess.run", unexpected_run)
    assert collect_versions()["firefox"] == "unknown"
