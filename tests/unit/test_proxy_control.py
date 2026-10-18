from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from tzMCP.gui_bits.proxy_control import ProxyController
from tzMCP.gui_bits import proxy_control
from tzMCP.sessions.processes import ProcessIdentity


def _controller(monkeypatch, tmp_path, process, port_in_use):
    controller = ProxyController(
        str(tmp_path / "save_media.py"),
        proxy_port=port_in_use,
        config_path=tmp_path / "capture-config.yaml",
        startup_timeout=0.01,
    )
    controller.process = process
    monkeypatch.setattr(controller, "_is_port_in_use", lambda: port_in_use is True)
    return controller


def test_wait_for_readiness_marks_proxy_ready(monkeypatch, tmp_path):
    process = SimpleNamespace(poll=lambda: None)
    controller = _controller(monkeypatch, tmp_path, process, True)
    controller._wait_for_readiness()
    assert controller.proxy_ready is True


def test_wait_for_readiness_reports_early_exit(monkeypatch, tmp_path):
    process = SimpleNamespace(poll=lambda: 17)
    controller = _controller(monkeypatch, tmp_path, process, False)
    with pytest.raises(RuntimeError, match="code 17"):
        controller._wait_for_readiness()


def test_wait_for_readiness_times_out(monkeypatch, tmp_path):
    process = SimpleNamespace(poll=lambda: None)
    controller = _controller(monkeypatch, tmp_path, process, False)
    with pytest.raises(TimeoutError, match="did not become ready"):
        controller._wait_for_readiness()


@pytest.mark.parametrize("failure", ["identity", "persistence", "readiness", None])
def test_proxy_records_identity_before_readiness_and_reaps_startup_failures(monkeypatch, tmp_path, failure):
    script = tmp_path / "save_media.py"
    script.write_text("# test addon", encoding="utf-8")
    config = tmp_path / "capture-config.yaml"
    config.write_text("{}", encoding="utf-8")
    controller = ProxyController(str(script), config_path=config)
    process = Mock(pid=42)
    process.poll.return_value = None
    process.stdout = None
    identity = ProcessIdentity(42, "/proxy", 123, "owner")
    events = []
    monkeypatch.setattr(controller, "_is_port_in_use", lambda: False)
    monkeypatch.setattr(controller, "_mitmdump_exe", lambda: tmp_path / "mitmdump")
    monkeypatch.setattr(proxy_control.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(proxy_control.psutil, "Process", lambda pid: process)

    def identify(_process):
        if failure == "identity":
            raise proxy_control.psutil.AccessDenied(42)
        return identity

    def persist(saved):
        assert saved == identity
        events.append("persist")
        if failure == "persistence":
            raise OSError("disk full")

    def ready():
        events.append("ready")
        if failure == "readiness":
            raise TimeoutError("startup timeout")

    monkeypatch.setattr(proxy_control.ProcessIdentity, "from_process", identify)
    monkeypatch.setattr(proxy_control, "stop_owned_process_tree", lambda saved: events.append("stop"))
    monkeypatch.setattr(controller, "_wait_for_readiness", ready)
    controller.on_process_started = persist
    if failure:
        with pytest.raises((OSError, TimeoutError, proxy_control.psutil.AccessDenied)):
            controller.start_proxy()
        process.wait.assert_called_once_with(timeout=5)
        assert controller.process is None
        if failure == "identity":
            process.terminate.assert_called_once()
        else:
            assert events[-1] == "stop"
    else:
        controller.start_proxy()
        assert events == ["persist", "ready"]
        assert controller.identity == identity
