"""Notificador de Discord vía webhook."""

from __future__ import annotations

import logging
import os

import httpx

from ..models import Alert
from .base import Notifier, register_notifier

logger = logging.getLogger(__name__)


def build_payload(alert: Alert) -> dict:
    """Construye el payload de webhook (embed) para una alerta."""
    price = f"${alert.price:.2f}" if alert.price is not None else "?"
    msrp = f"${alert.msrp:.2f}" if alert.msrp is not None else "?"
    fields = [
        {"name": "Retailer", "value": alert.retailer, "inline": True},
        {"name": "Precio", "value": f"{price} {alert.currency}", "inline": True},
        {"name": "MSRP", "value": msrp, "inline": True},
    ]
    embed = {
        "title": f"🟢 En stock a MSRP: {alert.set_name}",
        "description": "Producto sellado de Pokémon TCG disponible al precio oficial.",
        "url": alert.url,
        "color": 0x2ECC71,
        "fields": fields,
    }
    return {"username": "TCG Monitor", "embeds": [embed]}


@register_notifier
class DiscordNotifier(Notifier):
    name = "discord"
    requires_env = ("DISCORD_WEBHOOK_URL",)

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client

    def send(self, alert: Alert) -> bool:
        webhook = os.getenv("DISCORD_WEBHOOK_URL")
        if not webhook:
            logger.warning("Discord: falta DISCORD_WEBHOOK_URL")
            return False
        client = self._client or httpx.Client(timeout=15.0)
        try:
            resp = client.post(webhook, json=build_payload(alert))
        finally:
            if self._client is None:
                client.close()
        ok = 200 <= resp.status_code < 300
        if not ok:
            logger.warning("Discord webhook -> %d", resp.status_code)
        return ok
