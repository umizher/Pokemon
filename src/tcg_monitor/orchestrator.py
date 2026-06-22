"""Orquestador central: recorre providers, normaliza, filtra MSRP,
persiste estado y dispara notificaciones. Aísla fallos por provider.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from .config import Settings
from .dedupe import DedupeStore
from .filters import passes_alert_rule
from .health import HealthTracker
from .models import (
    Alert,
    Product,
    ProviderHealth,
    RetailerListing,
    State,
)
from .notify.base import Notifier
from .providers.base import ProviderError, StockProvider
from .store import write_state

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(
        self,
        settings: Settings,
        products: list[Product],
        providers: list[StockProvider],
        notifiers: list[Notifier],
        dedupe: DedupeStore,
        health: HealthTracker | None = None,
    ) -> None:
        self.settings = settings
        self.products = products
        self.providers = providers
        self.notifiers = notifiers
        self.dedupe = dedupe
        self.health = health

    def run_once(self) -> State:
        listings: list[RetailerListing] = []
        health: dict[str, ProviderHealth] = {}

        for provider in self.providers:
            ph = ProviderHealth(name=provider.name, ok=True, last_checked=_now())
            try:
                for product in self.products:
                    listing = provider.check(product)
                    if listing is not None:
                        listings.append(listing)
            except ProviderError as exc:
                ph.ok = False
                ph.last_error = str(exc)
                logger.warning("Provider %s falló: %s", provider.name, exc)
            except Exception as exc:  # aislamiento total: un provider no rompe al resto
                ph.ok = False
                ph.last_error = f"inesperado: {exc}"
                logger.exception("Provider %s lanzó excepción inesperada", provider.name)
            health[provider.name] = ph
            self._track_health(provider.name, ph.ok, ph.last_error)

        self._dispatch_alerts(listings)

        state = State(
            generated_at=_now(),
            providers_health=health,
            products=self.products,
            listings=listings,
        )
        write_state(state)
        return state

    def run_loop(self, interval: float = 600.0) -> None:
        logger.info("Iniciando loop continuo (intervalo %.0fs)", interval)
        while True:
            try:
                self.run_once()
            except Exception:  # nunca matar el loop
                logger.exception("run_once falló; continuando")
            time.sleep(interval)

    def _track_health(self, name: str, ok: bool, last_error: str | None) -> None:
        if self.health is None:
            return
        count = self.health.update(name, ok)
        if self.health.should_alert(count):
            subject = f"⚠️ Provider '{name}' caído"
            body = f"Falló {count} ciclos seguidos. Último error: {last_error or 'desconocido'}"
            for notifier in self.notifiers:
                try:
                    notifier.send_text(subject, body)
                except Exception:
                    logger.exception("Notificador %s falló al alertar salud", notifier.name)

    def _dispatch_alerts(self, listings: list[RetailerListing]) -> None:
        by_id = {p.id: p for p in self.products}
        for listing in listings:
            product = by_id.get(listing.product_id)
            if product is None:
                continue
            if not passes_alert_rule(listing, product, self.settings.msrp_tolerance):
                continue
            if self.dedupe.seen(listing.product_id, listing.retailer, listing.price):
                logger.info(
                    "Alerta deduplicada: %s @ %s (%s)",
                    product.set_name,
                    listing.retailer,
                    listing.price,
                )
                continue

            alert = Alert(
                product_id=product.id,
                set_name=product.set_name,
                retailer=listing.retailer,
                price=listing.price,
                currency=listing.currency,
                url=listing.url,
                msrp=product.official_msrp,
                stock_state=listing.stock_state,
            )
            sent_any = False
            for notifier in self.notifiers:
                try:
                    if notifier.send(alert):
                        sent_any = True
                except Exception:
                    logger.exception("Notificador %s falló", notifier.name)
            if sent_any:
                self.dedupe.mark(listing.product_id, listing.retailer, listing.price)


def _now() -> datetime:
    return datetime.now(timezone.utc)
