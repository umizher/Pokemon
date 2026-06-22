"""Release Radar: páginas mensuales de pokemon.com.

Fuente: "Check Out Every Pokémon TCG Product Release in <Month> <Year>".

HONESTIDAD: pokemon.com está protegido por Akamai y devuelve 403 desde
infra gratis (GitHub Actions / contenedores sin proxy residencial). Por eso
`discover()` degrada a lista vacía cuando lo bloquean, sin romper el ciclo.
El parser (`parse_release_page`) es una función pura, tolerante a cambios de
markup (trabaja sobre el texto de bloques: headings, items de lista, celdas),
y se valida con un fixture HTML guardado.
"""

from __future__ import annotations

import logging
import re
from datetime import date

from bs4 import BeautifulSoup

from ..http_client import HttpError, build_client, get_with_retry
from ..models import SEALED_TCG_TYPES, Product, ProductType
from .base import NewsProvider, register_news

logger = logging.getLogger(__name__)

BASE_URL = "https://www.pokemon.com/us/pokemon-news"
_PAGE_SLUG = "check-out-every-pokemon-tcg-product-release-in-{month}-{year}"

# Detección de tipo (orden importa: lo más específico primero).
_TYPE_PATTERNS: list[tuple[ProductType, re.Pattern]] = [
    (ProductType.elite_trainer_box, re.compile(r"elite trainer box|\betb\b", re.I)),
    (ProductType.booster_bundle, re.compile(r"booster bundle", re.I)),
    (ProductType.booster_box, re.compile(r"booster (box|display)", re.I)),
    (ProductType.blister, re.compile(r"blister|sleeved booster|checklane", re.I)),
    (ProductType.tin, re.compile(r"\btin\b", re.I)),
    (
        ProductType.collection_box,
        re.compile(r"collection|premium collection|binder|surprise box|box set", re.I),
    ),
]

# Señales de NO-TCG: se excluyen explícitamente (solo cartas).
_EXCLUDE = re.compile(
    r"video game|nintendo switch|plush|figure|pin\b|app\b|pokemon go|"
    r"trading figure|amiibo|jigsaw|puzzle|apparel|t-shirt|backpack",
    re.I,
)

_PRICE = re.compile(r"\$ ?(\d{1,4}(?:\.\d{2})?)")

# MSRP de referencia aproximado (USD) por tipo, usado solo si la página no
# publica precio. Documentado como aproximado; el filtro usa esto como base.
DEFAULT_MSRP_BY_TYPE: dict[ProductType, float] = {
    ProductType.elite_trainer_box: 59.99,
    ProductType.booster_bundle: 26.99,
    ProductType.blister: 12.99,
    ProductType.tin: 24.99,
    ProductType.collection_box: 49.99,
    ProductType.booster_box: 161.64,
}

_MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _detect_type(text: str) -> ProductType | None:
    """Devuelve el tipo de producto sellado, o None si no aplica/excluido."""
    if _EXCLUDE.search(text):
        return None
    for ptype, pat in _TYPE_PATTERNS:
        if pat.search(text):
            return ptype
    return None


def _extract_price(text: str) -> float | None:
    m = _PRICE.search(text)
    return float(m.group(1)) if m else None


def _clean_set_name(name: str, ptype: ProductType) -> str:
    """Quita prefijos, el tipo detectado, precios y residuos del nombre."""
    name = _PRICE.sub("", name)
    name = re.sub(r"pok[ée]mon tcg:?", "", name, flags=re.I)
    # Quita solo el patrón del tipo detectado (no todos) para no borrar
    # palabras legítimas del set como "Collection".
    for pt, pat in _TYPE_PATTERNS:
        if pt is ptype:
            name = pat.sub("", name)
            break
    # Residuos genéricos tras quitar "booster display"/"three-pack", etc.
    name = re.sub(r"\b(box|display|pack|three-pack|six-pack)\b", "", name, flags=re.I)
    name = re.sub(r"\(\s*\)", "", name)  # paréntesis vacíos
    name = re.sub(r"\s+", " ", name).strip(" -–—:•")
    return name


def parse_release_page(
    html: str, *, default_date: date | None = None, source: str = "pokemon.com"
) -> list[Product]:
    """Extrae productos TCG sellados (solo cartas) del HTML (función pura)."""
    soup = BeautifulSoup(html, "html.parser")

    # Bloques candidatos: headings, items de lista, celdas, negritas.
    blocks: list[str] = []
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "li", "td", "strong", "p"]):
        text = tag.get_text(" ", strip=True)
        if text and len(text) < 200:
            blocks.append(text)

    seen: dict[str, Product] = {}
    for text in blocks:
        ptype = _detect_type(text)
        if ptype is None or ptype not in SEALED_TCG_TYPES:
            continue
        set_name = _clean_set_name(text, ptype)
        if not set_name:
            continue
        pid = _slugify(f"{set_name}-{ptype.value}")
        if pid in seen:
            continue
        price = _extract_price(text)
        seen[pid] = Product(
            id=pid,
            set_name=set_name,
            product_type=ptype,
            language="EN",
            release_date=default_date,
            official_msrp=price if price is not None else DEFAULT_MSRP_BY_TYPE.get(ptype),
            currency="USD",
            source=source,
        )
    return list(seen.values())


@register_news
class PokemonOfficialRadar(NewsProvider):
    name = "pokemon_official"

    def __init__(self, months_ahead: int = 2, today: date | None = None) -> None:
        self.months_ahead = months_ahead
        self.today = today or date.today()

    def _month_urls(self) -> list[tuple[str, date]]:
        urls: list[tuple[str, date]] = []
        year, month = self.today.year, self.today.month
        for _ in range(self.months_ahead + 1):
            slug = _PAGE_SLUG.format(month=_MONTHS[month - 1], year=year)
            urls.append((f"{BASE_URL}/{slug}", date(year, month, 1)))
            month += 1
            if month > 12:
                month, year = 1, year + 1
        return urls

    def discover(self) -> list[Product]:
        found: dict[str, Product] = {}
        for url, page_date in self._month_urls():
            try:
                with build_client() as client:
                    resp = get_with_retry(client, url, max_retries=2)
            except HttpError as exc:
                # Akamai 403 esperado desde infra gratis -> degradar.
                logger.warning("Radar pokemon.com bloqueado/inaccesible (%s): %s", url, exc)
                continue
            if resp.status_code != 200:
                logger.warning("Radar %s -> %d", url, resp.status_code)
                continue
            for product in parse_release_page(resp.text, default_date=page_date):
                found.setdefault(product.id, product)
        logger.info("Radar pokemon.com: %d productos descubiertos", len(found))
        return list(found.values())
