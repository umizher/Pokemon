"""Provider de Best Buy usando la API oficial de desarrollador.

API gratuita y estable (https://developer.bestbuy.com/). Resuelve el SKU por
config o por búsqueda de keyword para no hardcodear productos.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os

from ..http_client import build_client, get_with_retry
from ..models import Product, ProductType, RetailerListing, StockState
from .base import ProviderError, StockProvider, register_provider

logger = logging.getLogger(__name__)

API_BASE = "https://api.bestbuy.com/v1"
SHOW_FIELDS = "sku,name,salePrice,regularPrice,onlineAvailability,orderable,url,image"

# Texto de búsqueda por tipo de producto (en inglés, mercado US).
_TYPE_KEYWORDS: dict[ProductType, str] = {
    ProductType.booster_box: "booster box",
    ProductType.elite_trainer_box: "elite trainer box",
    ProductType.booster_bundle: "booster bundle",
    ProductType.blister: "blister",
    ProductType.tin: "tin",
    ProductType.collection_box: "collection",
}


def _map_stock(orderable: str | None, online: bool | None) -> StockState:
    o = (orderable or "").lower()
    if o == "available" and online:
        return StockState.in_stock
    if o in ("comingsoon", "backorder"):
        return StockState.preorder
    if o == "soldout":
        return StockState.out_of_stock
    return StockState.unknown


def _hash(item: dict) -> str:
    relevant = {
        k: item.get(k)
        for k in ("sku", "salePrice", "onlineAvailability", "orderable")
    }
    return hashlib.sha256(json.dumps(relevant, sort_keys=True).encode()).hexdigest()[:16]


def parse_product(item: dict, product: Product) -> RetailerListing:
    """Convierte un objeto product de la API en RetailerListing (función pura)."""
    return RetailerListing(
        product_id=product.id,
        retailer="bestbuy",
        url=item.get("url"),
        sku=str(item.get("sku")) if item.get("sku") is not None else None,
        price=item.get("salePrice"),
        currency="USD",
        stock_state=_map_stock(item.get("orderable"), item.get("onlineAvailability")),
        response_hash=_hash(item),
    )


@register_provider
class BestBuyProvider(StockProvider):
    name = "bestbuy"
    viability = "API oficial gratuita, fiable en infra gratis"
    requires_env = ("BESTBUY_API_KEY",)

    def _api_key(self) -> str:
        key = os.getenv("BESTBUY_API_KEY")
        if not key:
            raise ProviderError("falta BESTBUY_API_KEY")
        return key

    def _search_terms(self, product: Product) -> str:
        parts = ["pokemon", product.set_name, _TYPE_KEYWORDS.get(product.product_type, "")]
        return "&".join(f"search={p.strip()}" for p in parts if p.strip())

    def resolve_sku(self, client, product: Product) -> dict | None:
        """Devuelve el objeto product de la API por SKU configurado o búsqueda."""
        api_key = self._api_key()
        configured = product.skus.get("bestbuy")
        if configured:
            url = f"{API_BASE}/products(sku={configured})"
        else:
            url = f"{API_BASE}/products({self._search_terms(product)})"
        resp = get_with_retry(
            client,
            url,
            params={"apiKey": api_key, "format": "json", "show": SHOW_FIELDS, "pageSize": "1"},
        )
        if resp.status_code != 200:
            raise ProviderError(f"Best Buy status {resp.status_code}")
        products = resp.json().get("products", [])
        return products[0] if products else None

    def check(self, product: Product) -> RetailerListing | None:
        with build_client() as client:
            item = self.resolve_sku(client, product)
        if item is None:
            logger.info("Best Buy: sin match para %s", product.set_name)
            return None
        return parse_product(item, product)
