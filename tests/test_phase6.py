import httpx
import pytest

from tcg_monitor.health import HealthTracker
from tcg_monitor.models import Alert, Product, StockState
from tcg_monitor.notify.telegram import TelegramNotifier, build_message
from tcg_monitor.providers.amazon import AmazonProvider
from tcg_monitor.providers.base import ProviderUnavailable
from tcg_monitor.providers.pokemoncenter import PokemonCenterProvider
from tcg_monitor.providers.walmart import WalmartProvider


def _product():
    return Product(id="p1", set_name="Chaos Rising", official_msrp=59.99)


def _alert():
    return Alert(
        product_id="p1",
        set_name="Chaos Rising",
        retailer="bestbuy",
        price=54.99,
        msrp=59.99,
        url="https://example.com/p",
        stock_state=StockState.in_stock,
    )


# --- Stubs de providers protegidos -------------------------------------

def test_protected_stubs_raise_unavailable():
    for cls in (WalmartProvider, AmazonProvider, PokemonCenterProvider):
        with pytest.raises(ProviderUnavailable):
            cls().check(_product())


def test_walmart_amazon_unavailable_without_keys(monkeypatch):
    for var in ("WALMART_API_KEY", "AMAZON_ACCESS_KEY", "AMAZON_SECRET_KEY", "AMAZON_PARTNER_TAG"):
        monkeypatch.delenv(var, raising=False)
    assert WalmartProvider().available() is False
    assert AmazonProvider().available() is False


def test_pokemoncenter_available_only_with_proxy(monkeypatch):
    monkeypatch.delenv("HTTP_PROXY_URL", raising=False)
    assert PokemonCenterProvider().available() is False
    monkeypatch.setenv("HTTP_PROXY_URL", "http://proxy:8080")
    assert PokemonCenterProvider().available() is True


# --- Telegram ----------------------------------------------------------

def test_telegram_build_message():
    msg = build_message(_alert())
    assert "Chaos Rising" in msg
    assert "$54.99" in msg


def test_telegram_send_posts(monkeypatch):
    captured = {}

    def handler(request):
        captured["url"] = str(request.url)
        captured["body"] = request.content
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "999")
    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert TelegramNotifier(client=client).send(_alert()) is True
    assert "bottok123/sendMessage" in captured["url"]
    assert b"Chaos Rising" in captured["body"]


def test_telegram_send_text(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "999")
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    assert TelegramNotifier(client=client).send_text("Caído", "detalle") is True


# --- HealthTracker -----------------------------------------------------

def test_health_alerts_once_at_threshold(tmp_path):
    h = HealthTracker(tmp_path / "h.json", threshold=3)
    assert h.update("target", ok=False) == 1
    assert h.should_alert(1) is False
    assert h.update("target", ok=False) == 2
    count = h.update("target", ok=False)
    assert count == 3
    assert h.should_alert(count) is True
    # Sigue fallando: no vuelve a alertar (count > threshold)
    assert h.should_alert(h.update("target", ok=False)) is False


def test_health_resets_on_recovery(tmp_path):
    h = HealthTracker(tmp_path / "h.json", threshold=2)
    h.update("bestbuy", ok=False)
    assert h.update("bestbuy", ok=True) == 0


def test_health_persists(tmp_path):
    path = tmp_path / "h.json"
    HealthTracker(path, threshold=3).update("target", ok=False)
    assert HealthTracker(path, threshold=3).update("target", ok=False) == 2
