"""Modelos de datos (pydantic v2) compartidos por todo el sistema."""

from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StockState(str, Enum):
    in_stock = "in_stock"
    out_of_stock = "out_of_stock"
    preorder = "preorder"
    unknown = "unknown"


class ProductType(str, Enum):
    """Tipos de producto sellado de cartas. `other` se filtra del catálogo."""

    booster_box = "booster_box"
    elite_trainer_box = "elite_trainer_box"
    booster_bundle = "booster_bundle"
    blister = "blister"
    tin = "tin"
    collection_box = "collection_box"
    other = "other"


# Tipos que cuentan como "producto sellado de cartas" para el Release Radar.
SEALED_TCG_TYPES: frozenset[ProductType] = frozenset(
    {
        ProductType.booster_box,
        ProductType.elite_trainer_box,
        ProductType.booster_bundle,
        ProductType.blister,
        ProductType.tin,
        ProductType.collection_box,
    }
)


class Product(BaseModel):
    id: str
    set_name: str
    product_type: ProductType = ProductType.other
    language: str = "EN"
    release_date: date | None = None
    official_msrp: float | None = None
    currency: str = "USD"
    image_url: str | None = None
    source: str | None = None
    # tiendas donde típicamente se vende (informativo para el calendario)
    retailers: list[str] = Field(default_factory=list)
    # retailer -> identificador en esa tienda (Best Buy SKU, Target TCIN, ...)
    skus: dict[str, str] = Field(default_factory=dict)


class RetailerListing(BaseModel):
    product_id: str
    retailer: str
    url: str | None = None
    sku: str | None = None
    price: float | None = None
    currency: str = "USD"
    stock_state: StockState = StockState.unknown
    last_checked: datetime = Field(default_factory=_utcnow)
    response_hash: str | None = None


class Alert(BaseModel):
    product_id: str
    set_name: str
    retailer: str
    price: float | None = None
    currency: str = "USD"
    url: str | None = None
    msrp: float | None = None
    stock_state: StockState = StockState.in_stock
    created_at: datetime = Field(default_factory=_utcnow)


class ProviderHealth(BaseModel):
    name: str
    ok: bool = True
    last_error: str | None = None
    last_checked: datetime | None = None


class State(BaseModel):
    """Estado canónico que consume el dashboard (docs/data/state.json)."""

    generated_at: datetime = Field(default_factory=_utcnow)
    providers_health: dict[str, ProviderHealth] = Field(default_factory=dict)
    products: list[Product] = Field(default_factory=list)
    listings: list[RetailerListing] = Field(default_factory=list)
