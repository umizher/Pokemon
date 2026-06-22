"""Provider de Target vía el endpoint público RedSky.

HONESTIDAD: RedSky es público pero Target bloquea IPs tras relativamente pocos
requests. El backoff de http_client mitiga, pero desde infra gratis el riesgo de
bloqueo es medio. Requiere TCIN (Target product id) por producto; sin TCIN el
estado queda en `unknown` (la búsqueda por keyword en RedSky es frágil).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os

from ..http_client import build_client, get_with_retry
from ..models import Product, RetailerListing, StockState
from .base import ProviderError, StockProvider, register_provider

logger = logging.getLogger(__name__)

REDSKY_URL = (
    "https://redsky.target.com/redsky_aggregations/v1/web/"
    "product_summary_with_fulfillment_v1"
)
# Key público estático que usa el storefront de Target.
DEFAULT_KEY = "ff457966e64d5e877fdbad070f276d18ecec4a01"

_STATUS_MAP = {
    "IN_STOCK": StockState.in_stock,
    "OUT_OF_STOCK": StockState.out_of_stock,
    "PRE_ORDER_SELLABLE": StockState.preorder,
    "PRE_ORDER_UNSELLABLE": StockState.preorder,
}


def _map_status(status: str | None) -> StockState:
    if not status:
        return StockState.unknown
    if status in _STATUS_MAP:
        return _STATUS_MAP[status]
    if status.startswith("PRE_ORDER"):
        return StockState.preorder
    return StockState.unknown


def _hash(summary: dict) -> str:
    return hashlib.sha256(json.dumps(summary, sort_keys=True).encode()).hexdigest()[:16]


def parse_summary(payload: dict, product: Product, tcin: str) -> RetailerListing:
    """Extrae precio y disponibilidad de la respuesta RedSky (función pura)."""
    summaries = (payload.get("data") or {}).get("product_summaries") or []
    summary = summaries[0] if summaries else {}

    price = (summary.get("price") or {}).get("current_retail")
    fulfillment = summary.get("fulfillment") or {}
    shipping = fulfillment.get("shipping_options") or {}
    state = _map_status(shipping.get("availability_status"))

    # Refuerzo: si está agotado en todas las tiendas y no hay envío disponible.
    if state == StockState.unknown and fulfillment.get(
        "is_out_of_stock_in_all_store_locations"
    ):
        state = StockState.out_of_stock

    return RetailerListing(
        product_id=product.id,
        retailer="target",
        url=f"https://www.target.com/p/-/A-{tcin}",
        sku=tcin,
        price=price,
        currency="USD",
        stock_state=state,
        response_hash=_hash(summary),
    )


@register_provider
class TargetProvider(StockProvider):
    name = "target"
    viability = "RedSky público; riesgo medio de bloqueo de IP en infra gratis"
    requires_env = ()  # usa key público por defecto

    def available(self) -> bool:  # siempre disponible; degrada si bloquea
        return True

    def _key(self) -> str:
        return os.getenv("TARGET_API_KEY") or DEFAULT_KEY

    def check(self, product: Product) -> RetailerListing | None:
        tcin = product.skus.get("target")
        if not tcin:
            logger.info("Target: sin TCIN para %s; estado unknown", product.set_name)
            return RetailerListing(
                product_id=product.id, retailer="target", stock_state=StockState.unknown
            )

        store_id = str(self.settings.get("store_id", "1357"))
        zip_code = str(self.settings.get("zip", "10001"))
        params = {
            "key": self._key(),
            "tcins": tcin,
            "store_id": store_id,
            "pricing_store_id": store_id,
            "zip": zip_code,
            "is_bot": "false",
        }
        with build_client() as client:
            resp = get_with_retry(client, REDSKY_URL, params=params)
        if resp.status_code != 200:
            raise ProviderError(f"Target RedSky status {resp.status_code}")
        return parse_summary(resp.json(), product, tcin)
