"""Moved fingerprint readers preserve liveness and reject recycled process IDs."""
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("offset,expected", [(100, True), (5000, False)])
def test_host_and_local_recovery_read_runtime_fingerprint(monkeypatch, offset, expected):
    from gateway import host_rendezvous
    from hermes_cli.local_runtime import recovery
    from runtime import process_identity

    monkeypatch.setattr(process_identity, "get_process_start_time", lambda pid: 1000 + offset)
    monkeypatch.setattr(host_rendezvous, "_pid_incarnation_matches", lambda *args: True)
    record = SimpleNamespace(pid=123, start_time=1000, create_time=1)
    assert host_rendezvous._record_incarnation_matches(record) is expected
    assert recovery._same_birth(SimpleNamespace(pid=123), {"start_time": 1000}) is expected
