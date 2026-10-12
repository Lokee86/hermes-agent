"""Destructive PID stops require a matching stamped and live home identity."""
import json
from gateway import process_lifecycle as lifecycle


def test_pid_home_probe_checks_exact_live_environ(monkeypatch, tmp_path):
    import pathlib
    from gateway import status  # import before simulating Linux on Windows
    home = tmp_path / "ours"
    original = pathlib.Path.read_bytes
    monkeypatch.setattr(lifecycle.sys, "platform", "linux")
    monkeypatch.setattr(pathlib.Path, "read_bytes",
                        lambda path: b"PATH=/bin\x00HERMES_HOME=" + str(home).encode() + b"\x00")
    assert lifecycle._pid_home_matches(123, home)
    assert not lifecycle._pid_home_matches(123, tmp_path / "other")


def test_stop_refuses_missing_or_foreign_home_without_signalling(monkeypatch, tmp_path):
    from gateway import status
    pidfile = tmp_path / "gateway.pid"
    monkeypatch.setattr(lifecycle, "_pid_home_matches", lambda pid, home: True)
    monkeypatch.setattr(status, "terminate_pid",
                        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected kill")))
    for record in ({"pid": 123}, {"pid": 123, "hermes_home": str(tmp_path / "other")}):
        pidfile.write_text(json.dumps(record))
        result = lifecycle.stop_gateway_process(tmp_path)
        assert result.status == "refused"


def test_stop_requires_live_home_match_even_with_matching_stamp(monkeypatch, tmp_path):
    from gateway import status
    (tmp_path / "gateway.pid").write_text(json.dumps({"pid": 123, "hermes_home": str(tmp_path)}))
    monkeypatch.setattr(lifecycle, "_pid_home_matches", lambda pid, home: False)
    monkeypatch.setattr(status, "terminate_pid",
                        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected kill")))
    assert lifecycle.stop_gateway_process(tmp_path).status == "refused"


def test_matching_live_home_can_stop(monkeypatch, tmp_path):
    from gateway import status
    (tmp_path / "gateway.pid").write_text(json.dumps({"pid": 123, "hermes_home": str(tmp_path),
                                                        "start_time": 42.0}))
    monkeypatch.setattr(lifecycle, "_pid_home_matches", lambda pid, home: True)
    calls = []
    monkeypatch.setattr(status, "terminate_pid", lambda pid: calls.append(pid))
    monkeypatch.setattr(lifecycle, "wait_then_force_kill", lambda pids, starts: True)
    assert lifecycle.stop_gateway_process(tmp_path).status == "stopped"
    assert calls == [123]
