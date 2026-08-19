from pathlib import Path

from tzMCP.sessions.versions import collect_versions


def test_version_metadata_has_expected_component_labels(monkeypatch):
    monkeypatch.setattr("tzMCP.sessions.versions._package_version", lambda _: "test-version")
    values = collect_versions(Path("missing-firefox"))
    assert set(values) == {"tzMCP", "appliance", "python", "mitmproxy", "ubuntu", "firefox"}
    assert values["tzMCP"] == "test-version"
    assert values["firefox"] == "unknown"
