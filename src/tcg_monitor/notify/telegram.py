"""Notificador de Telegram vía Bot API."""

from __future__ import annotations

import logging
import os

import httpx

from ..models import Alert
from .base import Notifier, register_notifier

logger = logging.getLogger(__name__)


def build_message(alert: Alert) -> str:
    """Mensaje en HTML para Telegram."""
    price = f"${alert.price:.2f}" if alert.price is not None else "?"
    msrp = f"${alert.msrp:.2f}" if alert.msrp is not None else "?"
    lines = [
        f"🟢 <b>En stock a MSRP: {alert.set_name}</b>",
        f"Retailer: <b>{alert.retailer}</b>",
        f"Precio: <b>{price} {alert.currency}</b> (MSRP {msrp})",
    ]
    if alert.url:
        lines.append(f'<a href="{alert.url}">Ver listado</a>')
    return "\n".join(lines)


@register_notifier
class TelegramNotifier(Notifier):
    name = "telegram"
    requires_env = ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client

    def _send_text(self, text: str) -> bool:
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not token or not chat_id:
            logger.warning("Telegram: faltan credenciales")
            return False
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        client = self._client or httpx.Client(timeout=15.0)
        try:
            resp = client.post(url, json=payload)
        finally:
            if self._client is None:
                client.close()
        ok = 200 <= resp.status_code < 300
        if not ok:
            logger.warning("Telegram sendMessage -> %d", resp.status_code)
        return ok

    def send(self, alert: Alert) -> bool:
        return self._send_text(build_message(alert))

    def send_text(self, subject: str, body: str) -> bool:
        return self._send_text(f"<b>{subject}</b>\n{body}")
