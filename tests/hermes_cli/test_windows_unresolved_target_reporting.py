"""Failed Windows relaunch reports exactly the still-owed targets."""
import pytest
from hermes_cli import update_cmd_windows as update


def test_error_and_warning_name_only_unresolved_targets(monkeypatch, tmp_path, capsys):
    from gateway import windows_service, status
    from profiles import paths

    monkeypatch.setattr(paths, "get_profile_dir", lambda name: tmp_path / name)
    monkeypatch.setattr(status, "_pid_exists", lambda pid: False)
    monkeypatch.setattr(update, "_relaunch_verify_timeout_s", lambda *args: 0)
    monkeypatch.setattr(update, "_poll_until_ready", lambda targets, deadline, taken: {
        ("profile", "ready"): [1001], ("unmapped", 0): [1002],
    })
    monkeypatch.setattr(windows_service, "_write_start_attestation", lambda *a, **kw: None)
    token = {}
    entries = [{"pid": 3, "argv": ["python"], "home": str(tmp_path)},
               {"pid": 4, "argv": ["python"], "home": str(tmp_path)}]
    with pytest.raises(RuntimeError) as exc:
        update._verify_relaunched_gateways_alive(token, {"ready": 1, "missing": 2}, entries)
    message = str(exc.value)
    warning = capsys.readouterr().out
    assert "missing, pid 4" in message
    assert "missing, pid 4" in warning
    assert "ready" not in message and "pid 3" not in message
    assert token["profiles"] == {"missing": 2}
    assert token["unmapped"] == [entries[1]]


def test_success_emits_no_unresolved_warning(monkeypatch, tmp_path, capsys):
    from gateway import windows_service, status
    from profiles import paths
    monkeypatch.setattr(paths, "get_profile_dir", lambda name: tmp_path / name)
    monkeypatch.setattr(status, "_pid_exists", lambda pid: False)
    monkeypatch.setattr(update, "_relaunch_verify_timeout_s", lambda *args: 0)
    monkeypatch.setattr(update, "_poll_until_ready", lambda targets, deadline, taken: {
        ("profile", "ready"): [1001]})
    monkeypatch.setattr(windows_service, "_write_start_attestation", lambda *a, **kw: None)
    token = {}
    update._verify_relaunched_gateways_alive(token, {"ready": 1}, [])
    assert capsys.readouterr().out == ""
    assert token["profiles"] == {}
