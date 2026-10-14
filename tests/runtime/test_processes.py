"""Tests for shared process-containment primitives."""

import pytest

from runtime import processes


@pytest.mark.platforms("posix")
def test_attach_self_is_noop_off_windows(monkeypatch):
    monkeypatch.setattr(processes, "_JOB_HANDLE", None)
    assert processes.attach_self_to_kill_on_close_job() is False


def test_attach_self_is_idempotent_once_job_is_owned(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(processes, "_JOB_HANDLE", sentinel)
    assert processes.attach_self_to_kill_on_close_job() is True
    assert processes._JOB_HANDLE is sentinel
