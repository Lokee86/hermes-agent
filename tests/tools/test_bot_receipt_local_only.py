"""Receipt read and sync/async waits never replay a live owner's delivery RPC."""
import asyncio
import pytest
from tools import bot_live_delivery as delivery


@pytest.mark.asyncio
async def test_reads_and_waits_do_not_reenter_owner(monkeypatch, tmp_path):
    key = "9" * 32
    calls = []
    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("reading a receipt must not deliver again")
    monkeypatch.setattr(delivery, "authority_delivery", forbidden)
    with delivery._locked(tmp_path) as root:
        delivery._write(root / f"{key}.json", {
            "delivery_id": key, "admission_id": "admit", "status": "queued", "message": "hello",
            "author": {"id": "sender"}, "notification_category": "diagnostic",
        })
    assert delivery.read_delivery_result(tmp_path, key)["status"] == "queued"
    assert delivery.await_delivery(tmp_path, key, 0)["status"] == "queued"
    assert (await delivery.await_delivery_async(tmp_path, key, 0))["status"] == "queued"
    with delivery._locked(tmp_path) as root:
        record = delivery._read(root / f"{key}.json")
        delivery._write(root / f"{key}.json", {**record, "status": "settled", "reply": "PONG"})
    assert delivery.read_delivery_result(tmp_path, key)["reply"] == "PONG"
    assert (await delivery.await_delivery_async(tmp_path, key, 0))["reply"] == "PONG"
    assert calls == []
