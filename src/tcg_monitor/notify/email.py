"""Notificador por email vía SMTP."""

from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage

from ..models import Alert
from .base import Notifier, register_notifier

logger = logging.getLogger(__name__)


def build_email(alert: Alert) -> EmailMessage:
    price = f"${alert.price:.2f}" if alert.price is not None else "?"
    msrp = f"${alert.msrp:.2f}" if alert.msrp is not None else "?"
    msg = EmailMessage()
    msg["Subject"] = f"[TCG Monitor] En stock a MSRP: {alert.set_name}"
    msg["From"] = os.getenv("SMTP_FROM", os.getenv("SMTP_USER", ""))
    msg["To"] = os.getenv("SMTP_TO", "")
    body = (
        f"Producto: {alert.set_name}\n"
        f"Retailer: {alert.retailer}\n"
        f"Precio: {price} {alert.currency} (MSRP {msrp})\n"
        f"Estado: {alert.stock_state.value}\n"
    )
    if alert.url:
        body += f"URL: {alert.url}\n"
    msg.set_content(body)
    return msg


@register_notifier
class EmailNotifier(Notifier):
    name = "email"
    requires_env = ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "SMTP_TO")

    def _send(self, msg: EmailMessage) -> bool:
        host = os.getenv("SMTP_HOST")
        port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER")
        password = os.getenv("SMTP_PASSWORD")
        if not host or not user or not password:
            logger.warning("Email: faltan credenciales SMTP")
            return False
        try:
            with smtplib.SMTP(host, port, timeout=20) as server:
                server.starttls()
                server.login(user, password)
                server.send_message(msg)
        except (smtplib.SMTPException, OSError) as exc:
            logger.warning("Email SMTP falló: %s", exc)
            return False
        return True

    def send(self, alert: Alert) -> bool:
        return self._send(build_email(alert))

    def send_text(self, subject: str, body: str) -> bool:
        msg = EmailMessage()
        msg["Subject"] = f"[TCG Monitor] {subject}"
        msg["From"] = os.getenv("SMTP_FROM", os.getenv("SMTP_USER", ""))
        msg["To"] = os.getenv("SMTP_TO", "")
        msg.set_content(body)
        return self._send(msg)
