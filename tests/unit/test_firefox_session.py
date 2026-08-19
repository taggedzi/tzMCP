from pathlib import Path
from types import SimpleNamespace

import pytest

from tzMCP.browser.firefox_session import CA_NICKNAME, FirefoxSession, FirefoxSessionError


def _runner(calls):
    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stderr="")
    return run


def test_profile_preferences_and_ca_commands_are_session_scoped(tmp_path):
    executable = tmp_path / "firefox"
    certificate = tmp_path / "mitmproxy-ca-cert.pem"
    executable.write_bytes(b"binary")
    certificate.write_text("certificate", encoding="utf-8")
    calls = []
    session = FirefoxSession(
        executable,
        tmp_path / "session" / "browser",
        certificate,
        9000,
        runner=_runner(calls),
    )

    profile = session.create_profile()
    session.import_ca()

    prefs = (profile / "user.js").read_text(encoding="utf-8")
    assert 'network.proxy.http", "127.0.0.1' in prefs
    assert "network.proxy.http_port\", 9000" in prefs
    assert "security.enterprise_roots" not in prefs
    assert any(CA_NICKNAME in command for command, _ in calls)
    assert all(str(profile) in " ".join(command) for command, _ in calls)


def test_missing_ca_fails_before_profile_creation(tmp_path):
    executable = tmp_path / "firefox"
    executable.write_bytes(b"binary")
    session = FirefoxSession(executable, tmp_path / "browser", tmp_path / "missing.pem", 8888)
    with pytest.raises(FirefoxSessionError, match="CA certificate"):
        session.create_profile()
    assert not (tmp_path / "browser").exists()


def test_start_cleans_profile_when_certutil_fails(tmp_path):
    executable = tmp_path / "firefox"
    certificate = tmp_path / "ca.pem"
    executable.write_bytes(b"binary")
    certificate.write_text("certificate", encoding="utf-8")

    def failed_runner(command, **kwargs):
        return SimpleNamespace(returncode=1, stderr="bad NSS database")

    session = FirefoxSession(executable, tmp_path / "browser", certificate, 8888, runner=failed_runner)
    with pytest.raises(FirefoxSessionError, match="certutil failed"):
        session.start()
    assert not session.profile_dir.exists()
