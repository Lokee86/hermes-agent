"""Focused regressions for P4 ancillary plugin-runtime boundaries."""

from __future__ import annotations

import io
from types import SimpleNamespace


def test_activation_notification_brackets_ipv6_authority(monkeypatch, tmp_path):
    import urllib.request

    from gateway import host_rendezvous as hr
    from hermes_cli import plugins_activation

    record = SimpleNamespace(role=hr.ROLE_SERVE, port=9231)
    monkeypatch.setattr(plugins_activation, "_serve_backend_record", lambda: record)
    monkeypatch.setattr(hr, "read_token", lambda _role: "fixture-token")
    monkeypatch.setattr(hr, "dial_host", lambda _record: "::1")
    dialed: list[str] = []

    class Reply(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

    def fake_urlopen(request, timeout=None):
        dialed.append(request.full_url)
        return Reply(b'{"ok": true}')

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    assert plugins_activation.notify_serve_backend("demo", tmp_path) == {"ok": True}
    assert dialed == ["http://[::1]:9231/api/dashboard/agent-plugins/activate"]


def test_runtime_version_bridge_uses_canonical_version_info(monkeypatch):
    from hermes_cli import version_info
    from plugin_runtime.config_bridge import read_running_hermes_version

    monkeypatch.setattr(
        version_info,
        "get_version_info",
        lambda: SimpleNamespace(base_version="9.8.7"),
    )

    assert read_running_hermes_version() == "9.8.7"


def test_request_middleware_fallback_clones_copyable_siblings_around_uncopyable_leaf():
    from plugin_runtime.dispatch import LLM_REQUEST_MIDDLEWARE
    from plugin_runtime.manager import PluginManager

    class Uncopyable:
        def __deepcopy__(self, _memo):
            raise TypeError("fixture refuses deepcopy")

    opaque = Uncopyable()
    original = {
        "copyable": {"items": ["original"]},
        "opaque": opaque,
    }
    seen: list[list[str]] = []

    def meddler(request, **_kwargs):
        assert request["opaque"] is opaque
        request["copyable"]["items"].append("mutated")

    def observer(request, **_kwargs):
        assert request["opaque"] is opaque
        seen.append(list(request["copyable"]["items"]))

    manager = PluginManager()
    manager._middleware[LLM_REQUEST_MIDDLEWARE] = [meddler, observer]

    manager.invoke_middleware(
        LLM_REQUEST_MIDDLEWARE,
        request=original,
        original_request=original,
        _payload_key="request",
    )

    assert seen == [["original"]]
    assert original["copyable"]["items"] == ["original"]
