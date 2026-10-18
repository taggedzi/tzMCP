from types import SimpleNamespace

import pytest

from tzMCP.browser import firefox_session as firefox_session_module
from tzMCP.browser.firefox_session import (
    CA_NICKNAME,
    FirefoxSession,
    FirefoxSessionError,
)
from tzMCP.sessions.processes import ProcessIdentity


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


def test_firefox_launcher_symlink_is_preserved(tmp_path):
    snap = tmp_path / "snap"
    snap.write_bytes(b"binary")
    launcher = tmp_path / "firefox"
    try:
        launcher.symlink_to(snap)
    except OSError:
        pytest.skip("symlinks unavailable")
    session = FirefoxSession(launcher, tmp_path / "browser", tmp_path / "ca.pem", 8888)
    assert session.executable == launcher


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


def test_stop_treats_a_fully_exited_browser_as_already_stopped(tmp_path, monkeypatch):
    session = FirefoxSession(tmp_path / "firefox", tmp_path / "browser", tmp_path / "ca.pem", 8888)
    session.profile_dir.mkdir(parents=True)
    session.identity = ProcessIdentity(123, "/snap/bin/firefox", 10.0, "tzmcp")
    session.process = SimpleNamespace(poll=lambda: 0)
    monkeypatch.setattr(firefox_session_module, "verify_process_identity", lambda _: False)
    monkeypatch.setattr(firefox_session_module.psutil, "process_iter", lambda attrs: iter(()))

    session.stop()

    assert session.identity is None
    assert session.process is None


def test_stop_finds_snap_firefox_after_launcher_executable_changes(tmp_path, monkeypatch):
    profile = tmp_path / "browser" / "profile"

    class FakeProcess:
        def __init__(self, pid, cmdline=None, children=()):
            self.pid = pid
            self.info = {"cmdline": cmdline or [], "username": "tzmcp"}
            self._children = list(children)
            self.terminated = False
            self.killed = False

        def exe(self):
            return "/snap/firefox/current/usr/lib/firefox/firefox"

        def create_time(self):
            return 20.0

        def username(self):
            return "tzmcp"

        def cmdline(self):
            return self.info["cmdline"]

        def children(self, recursive=False):
            return self._children

        def terminate(self):
            self.terminated = True

        def kill(self):
            self.killed = True

    child = FakeProcess(78)
    browser = FakeProcess(77, ["firefox", "-profile", str(profile)], [child])
    session = FirefoxSession(tmp_path / "firefox", tmp_path / "browser", tmp_path / "ca.pem", 8888)
    session.profile_dir.mkdir(parents=True)
    session.identity = ProcessIdentity(77, "/usr/bin/snap", 19.0, "tzmcp")
    session.process = SimpleNamespace(poll=lambda: None)
    monkeypatch.setattr(
        firefox_session_module,
        "verify_process_identity",
        lambda identity: identity.pid == 77 and identity.executable != "/usr/bin/snap",
    )
    monkeypatch.setattr(firefox_session_module.psutil, "process_iter", lambda attrs: iter((browser,)))
    monkeypatch.setattr(firefox_session_module.psutil, "Process", lambda pid: browser if pid == 77 else child)
    monkeypatch.setattr(firefox_session_module.psutil, "wait_procs", lambda processes, timeout: (processes, []))

    session.stop()

    assert browser.terminated
    assert child.terminated
    assert session.identity is None
    assert session.process is None
