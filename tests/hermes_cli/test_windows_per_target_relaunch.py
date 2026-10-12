"""Windows updater owes independent readiness for each relaunched gateway."""
import pytest
from hermes_cli import update_cmd_windows as update


def test_relaunch_profiles_and_unmapped_debts(monkeypatch, tmp_path):
    from gateway import windows_service, status
    from profiles import paths
    monkeypatch.setattr(paths, "get_profile_dir", lambda name: tmp_path / name)
    monkeypatch.setattr(status, "_pid_exists", lambda pid: True)
    monkeypatch.setattr(update, "_relaunch_verify_timeout_s", lambda *args: 1)
    monkeypatch.setattr(windows_service, "_live_gateway_pids",
                        lambda home: [101] if home.name == "a" else [102])
    monkeypatch.setattr(update, "_unmapped_ready_filter",
                        lambda entry, taken: (lambda pids: [103] if 103 not in taken else []))
    monkeypatch.setattr(update, "_poll_until_ready",
                        lambda targets, deadline, taken: {("profile", "a"): [101], ("unmapped", 0): [103]})
    attest = []
    monkeypatch.setattr(windows_service, "_write_start_attestation",
                        lambda pids, via, home=None: attest.append((pids, home)))
    token = {}
    with pytest.raises(RuntimeError, match="b"):
        update._verify_relaunched_gateways_alive(
            token, {"a": 1, "b": 2}, [{"pid": 3, "argv": ["python", "run"], "home": str(tmp_path / "u")}])
    assert token["profiles"] == {"b": 2}
    assert token["unmapped"] == []
    assert token["relaunched_profiles"] == ["a"]
    assert [x[0] for x in attest] == [[101], [103]]


def test_all_target_debts_retire_only_on_individual_proof(monkeypatch, tmp_path):
    from gateway import windows_service, status
    from profiles import paths
    monkeypatch.setattr(paths, "get_profile_dir", lambda name: tmp_path / name)
    monkeypatch.setattr(status, "_pid_exists", lambda pid: True)
    monkeypatch.setattr(update, "_relaunch_verify_timeout_s", lambda *args: 1)
    monkeypatch.setattr(update, "_poll_until_ready", lambda targets, deadline, taken: {})
    monkeypatch.setattr(windows_service, "_write_start_attestation",
                        lambda *args, **kwargs: pytest.fail("unverified gateway attested"))
    token = {}
    with pytest.raises(RuntimeError, match="alpha.*pid 5"):
        update._verify_relaunched_gateways_alive(
            token, {"alpha": 2}, [{"pid": 5, "argv": ["python", "run"]}])
    assert token["profiles"] == {"alpha": 2}
    assert [x["pid"] for x in token["unmapped"]] == [5]
    assert token["relaunched_profiles"] == []
