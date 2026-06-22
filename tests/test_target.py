import json
from pathlib import Path

from tcg_monitor.models import Product, ProductType, StockState
from tcg_monitor.providers.target import parse_summary

FIXTURES = Path(__file__).parent / "fixtures"


def _product():
    return Product(
        id="sv-pitch-black-booster-bundle",
        set_name="Pitch Black",
        product_type=ProductType.booster_bundle,
        official_msrp=26.99,
        skus={"target": "89542109"},
    )


def _payload(name):
    return json.loads((FIXTURES / name).read_text())


def test_parse_in_stock():
    listing = parse_summary(_payload("target_in_stock.json"), _product(), "89542109")
    assert listing.retailer == "target"
    assert listing.price == 26.99
    assert listing.stock_state == StockState.in_stock
    assert listing.sku == "89542109"
    assert "A-89542109" in listing.url


def test_parse_out_of_stock():
    listing = parse_summary(_payload("target_out_of_stock.json"), _product(), "89542109")
    assert listing.stock_state == StockState.out_of_stock


def test_parse_empty_payload_is_unknown():
    listing = parse_summary({"data": {}}, _product(), "89542109")
    assert listing.stock_state == StockState.unknown
    assert listing.price is None
