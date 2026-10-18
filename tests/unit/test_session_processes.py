from types import SimpleNamespace
from unittest.mock import Mock

import psutil
import pytest

from tzMCP.sessions import processes

from tzMCP.sessions.processes import ProcessIdentity, verify_process_identity


def test_process_identity_requires_executable_owner_and_start_time(tmp_path):
    executable = tmp_path / "mitmdump"
    executable.write_text("", encoding="utf-8")
    identity = ProcessIdentity(42, str(executable), 123.0, "tzmcp")

    process = SimpleNamespace(
        pid=42,
        exe=lambda: str(executable),
        create_time=lambda: 123.0,
        username=lambda: "tzmcp",
    )
    assert verify_process_identity(identity, lambda _: process)

    wrong_pid_reuse = SimpleNamespace(
        pid=42,
        exe=lambda: str(executable),
        create_time=lambda: 999.0,
        username=lambda: "tzmcp",
    )
    assert not verify_process_identity(identity, lambda _: wrong_pid_reuse)


@pytest.mark.parametrize("change", ["start_time", "owner", "executable"])
def test_shutdown_never_signals_an_unverified_pid(monkeypatch, change):
    identity = ProcessIdentity(42, "/proxy", 123, "owner")
    process = Mock(pid=42)
    process.exe.return_value = "/other" if change == "executable" else "/proxy"
    process.create_time.return_value = 999 if change == "start_time" else 123
    process.username.return_value = "other" if change == "owner" else "owner"
    monkeypatch.setattr(processes.psutil, "Process", lambda _: process)
    with pytest.raises(RuntimeError, match="Cannot verify"):
        processes.stop_owned_process_tree(identity)
    process.terminate.assert_not_called()
    process.kill.assert_not_called()


def test_shutdown_accepts_already_exited_process(monkeypatch):
    def absent(_pid):
        raise psutil.NoSuchProcess(42)
    monkeypatch.setattr(processes.psutil, "Process", absent)
    processes.stop_owned_process_tree(ProcessIdentity(42, "/proxy", 123, "owner"))


@pytest.mark.parametrize("survives", [False, True])
def test_shutdown_waits_after_termination_and_kill(monkeypatch, survives):
    root = Mock(pid=42)
    child = Mock(pid=43)
    root.children.return_value = [child]
    monkeypatch.setattr(processes.psutil, "Process", lambda _: root)
    monkeypatch.setattr(processes.ProcessIdentity, "from_process", lambda p: ProcessIdentity(p.pid, "/proxy", 123, "owner"))
    monkeypatch.setattr(processes, "verify_process_identity", lambda _: True)
    wait = Mock(side_effect=[([], [child]), ([], [child]) if survives else ([child], [])])
    monkeypatch.setattr(processes.psutil, "wait_procs", wait)
    identity = ProcessIdentity(42, "/proxy", 123, "owner")
    if survives:
        with pytest.raises(RuntimeError, match="did not exit"):
            processes.stop_owned_process_tree(identity)
    else:
        processes.stop_owned_process_tree(identity)
    root.terminate.assert_called_once()
    child.terminate.assert_called_once()
    child.kill.assert_called_once()
    assert wait.call_count == 2


def test_shutdown_finds_reparented_posix_session_children(monkeypatch):
    child = Mock(pid=43)
    child.exe.return_value = "/child"
    child.create_time.return_value = 124
    child.username.return_value = "owner"
    child.status.return_value = psutil.STATUS_RUNNING
    identity = ProcessIdentity(42, "/proxy", 123, "owner", session_id=42)
    monkeypatch.setattr(processes, "os", SimpleNamespace(name="posix", getsid=lambda pid: 42))

    def lookup(pid):
        if pid == 42:
            raise psutil.NoSuchProcess(pid)
        return child

    monkeypatch.setattr(processes.psutil, "Process", lookup)
    monkeypatch.setattr(processes.psutil, "process_iter", Mock(side_effect=[[child], []]))
    monkeypatch.setattr(processes.psutil, "wait_procs", lambda targets, timeout: (targets, []))
    processes.stop_owned_process_tree(identity)
    child.terminate.assert_called_once()


def test_shutdown_blocks_export_when_new_session_children_appear(monkeypatch):
    identity = ProcessIdentity(42, "/proxy", 123, "owner", session_id=42)
    root = Mock(pid=42)
    root.children.return_value = []
    monkeypatch.setattr(processes.psutil, "Process", lambda pid: root)
    monkeypatch.setattr(processes, "verify_process_identity", lambda saved: True)
    monkeypatch.setattr(processes.ProcessIdentity, "from_process", lambda p: identity)
    monkeypatch.setattr(processes, "_session_members", Mock(side_effect=[[], [Mock(pid=43)]]))
    monkeypatch.setattr(processes.psutil, "wait_procs", lambda targets, timeout: (targets, []))
    with pytest.raises(RuntimeError, match="spawned more processes"):
        processes.stop_owned_process_tree(identity)
