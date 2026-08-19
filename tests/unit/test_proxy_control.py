from types import SimpleNamespace

import pytest

from tzMCP.gui_bits.proxy_control import ProxyController


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
