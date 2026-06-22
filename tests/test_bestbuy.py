import json
from pathlib import Path

from tcg_monitor.models import Product, ProductType, StockState
from tcg_monitor.providers.bestbuy import parse_product

FIXTURES = Path(__file__).parent / "fixtures"


def _product():
    return Product(
        id="sv-perfect-order-etb",
        set_name="Perfect Order",
        product_type=ProductType.elite_trainer_box,
        official_msrp=59.99,
    )


def _first(name):
    return json.loads((FIXTURES / name).read_text())["products"][0]


def test_parse_in_stock():
    listing = parse_product(_first("bestbuy_in_stock.json"), _product())
    assert listing.retailer == "bestbuy"
    assert listing.price == 59.99
    assert listing.stock_state == StockState.in_stock
    assert listing.sku == "6588543"
    assert listing.url.endswith("6588543.p")
    assert listing.response_hash


def test_parse_sold_out():
    listing = parse_product(_first("bestbuy_sold_out.json"), _product())
    assert listing.stock_state == StockState.out_of_stock


def test_hash_changes_with_availability():
    a = parse_product(_first("bestbuy_in_stock.json"), _product())
    b = parse_product(_first("bestbuy_sold_out.json"), _product())
    assert a.response_hash != b.response_hash
