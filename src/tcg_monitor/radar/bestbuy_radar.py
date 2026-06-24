"""Release Radar vía la API gratuita de Best Buy.

Una sola clave gratuita (BESTBUY_API_KEY) sirve para DOS cosas:
  1. Calendario: descubre producto sellado de Pokémon TCG con su fecha de
     lanzamiento (`releaseDate`) y MSRP de lanzamiento (`salePrice`).
  2. Stock: el `BestBuyProvider` (providers/bestbuy.py) revisa disponibilidad.

Si no hay clave, el radar degrada a lista vacía y la app sigue mostrando el
calendario semilla de `config/products.yaml`.
"""

from __future__ import annotations

import logging
import os
from datetime import date

from ..http_client import HttpError, build_client, get_with_retry
from ..models import SEALED_TCG_TYPES, Product
from ..providers.bestbuy import API_BASE, SHOW_FIELDS
from .base import NewsProvider, register_news
from .pokemon_official import DEFAULT_MSRP_BY_TYPE, _detect_type, _slugify

logger = logging.getLogger(__name__)

# Categoría "Trading Cards" / búsqueda de producto sellado de Pokémon.
# Usamos búsqueda por nombre + filtro por tipo detectado del propio nombre.
SEARCH_URL = f"{API_BASE}/products(search=pokemon&search=cards)"


def _parse_release_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def parse_catalog(items: list[dict]) -> list[Product]:
    """Convierte productos de la API de Best Buy en Products de calendario.

    Función pura: clasifica por tipo (solo sellado de cartas), toma fecha y MSRP.
    """
    out: dict[str, Product] = {}
    for item in items:
        name = item.get("name") or ""
        ptype = _detect_type(name)
        if ptype is None or ptype not in SEALED_TCG_TYPES:
            continue
        pid = _slugify(name)[:80]
        if not pid or pid in out:
            continue
        price = item.get("salePrice")
        out[pid] = Product(
            id=pid,
            set_name=name,
            product_type=ptype,
            language="EN",
            release_date=_parse_release_date(item.get("releaseDate")),
            official_msrp=price if price is not None else DEFAULT_MSRP_BY_TYPE.get(ptype),
            currency="USD",
            image_url=item.get("image"),
            source="bestbuy",
            skus={"bestbuy": str(item["sku"])} if item.get("sku") is not None else {},
        )
    return list(out.values())


@register_news
class BestBuyRadar(NewsProvider):
    name = "bestbuy_radar"

    def discover(self) -> list[Product]:
        api_key = os.getenv("BESTBUY_API_KEY")
        if not api_key:
            logger.info("Best Buy radar: sin BESTBUY_API_KEY; se omite (calendario semilla)")
            return []
        params = {
            "apiKey": api_key,
            "format": "json",
            "show": SHOW_FIELDS,
            "pageSize": "100",
            "sort": "releaseDate.dsc",
        }
        try:
            with build_client() as client:
                resp = get_with_retry(client, SEARCH_URL, params=params)
        except HttpError as exc:
            logger.warning("Best Buy radar inaccesible: %s", exc)
            return []
        if resp.status_code != 200:
            logger.warning("Best Buy radar -> %d", resp.status_code)
            return []
        products = parse_catalog(resp.json().get("products", []))
        logger.info("Best Buy radar: %d productos de calendario", len(products))
        return products
