import httpx

from tcg_monitor.models import Alert, StockState
from tcg_monitor.notify.discord import DiscordNotifier, build_payload


def _alert():
    return Alert(
        product_id="p1",
        set_name="Perfect Order",
        retailer="bestbuy",
        price=59.99,
        msrp=59.99,
        url="https://example.com/p",
        stock_state=StockState.in_stock,
    )


def test_build_payload_has_embed():
    payload = build_payload(_alert())
    assert payload["embeds"][0]["title"].startswith("🟢")
    assert payload["embeds"][0]["url"] == "https://example.com/p"
    field_names = {f["name"] for f in payload["embeds"][0]["fields"]}
    assert {"Retailer", "Precio", "MSRP"} <= field_names


def test_send_posts_to_webhook(monkeypatch):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = request.content
        return httpx.Response(204)

    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.test/webhook/abc")
    client = httpx.Client(transport=httpx.MockTransport(handler))
    notifier = DiscordNotifier(client=client)

    assert notifier.send(_alert()) is True
    assert captured["url"] == "https://discord.test/webhook/abc"
    assert b"Perfect Order" in captured["body"]


def test_send_without_webhook_returns_false(monkeypatch):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    assert DiscordNotifier().send(_alert()) is False
