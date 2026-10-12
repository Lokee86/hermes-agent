"""Systemd user service paths are owned by the OS account, not profile HOME."""
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from gateway import systemd_identity


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX pwd account lookup")
def test_pinned_profile_home_does_not_redirect_user_unit(tmp_path, monkeypatch):
    account = tmp_path / "account"
    profile = tmp_path / "profile"
    monkeypatch.setenv("HOME", str(profile))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    with patch("pwd.getpwuid", return_value=SimpleNamespace(pw_dir=str(account))):
        assert systemd_identity.user_unit_dir() == account / ".config/systemd/user"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX pwd account lookup")
def test_relative_xdg_config_home_does_not_redirect_user_unit(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", "profile-relative")
    with patch("pwd.getpwuid", return_value=SimpleNamespace(pw_dir=str(tmp_path))):
        assert systemd_identity.user_unit_dir() == tmp_path / ".config/systemd/user"


def test_absolute_xdg_config_home_is_respected(tmp_path, monkeypatch):
    config = tmp_path / "xdg"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config))
    assert systemd_identity.user_unit_dir() == config / "systemd/user"
