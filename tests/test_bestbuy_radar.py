import json
from datetime import date
from pathlib import Path

from tcg_monitor.models import ProductType
from tcg_monitor.radar.bestbuy_radar import parse_catalog

FIXTURES = Path(__file__).parent / "fixtures"


def _items():
    return json.loads((FIXTURES / "bestbuy_radar.json").read_text())["products"]


def test_extracts_only_sealed_tcg():
    products = parse_catalog(_items())
    # Excluye el videojuego de Switch y el peluche
    assert len(products) == 2
    types = {p.product_type for p in products}
    assert types == {ProductType.elite_trainer_box, ProductType.booster_bundle}


def test_captures_date_price_sku_image():
    by_type = {p.product_type: p for p in parse_catalog(_items())}
    etb = by_type[ProductType.elite_trainer_box]
    assert etb.release_date == date(2026, 5, 22)
    assert etb.official_msrp == 59.99
    assert etb.skus == {"bestbuy": "6588543"}
    assert etb.image_url.endswith("etb.jpg")
    assert etb.source == "bestbuy"


def test_no_videogame_or_plush_leak():
    names = " ".join(p.set_name.lower() for p in parse_catalog(_items()))
    assert "switch" not in names
    assert "plush" not in names
