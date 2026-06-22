from datetime import date
from pathlib import Path

from tcg_monitor.models import ProductType
from tcg_monitor.radar.pokemon_official import (
    DEFAULT_MSRP_BY_TYPE,
    parse_release_page,
)
from tcg_monitor.store import merge_discovered
from tcg_monitor.models import Product

FIXTURES = Path(__file__).parent / "fixtures"


def _parse():
    html = (FIXTURES / "pokemon_release_page.html").read_text()
    return parse_release_page(html, default_date=date(2026, 6, 1))


def test_extracts_sealed_tcg_only():
    products = _parse()
    types = {p.product_type for p in products}
    # Detecta los tipos sellados de cartas...
    assert ProductType.elite_trainer_box in types
    assert ProductType.booster_bundle in types
    assert ProductType.booster_box in types
    assert ProductType.tin in types
    assert ProductType.blister in types
    assert ProductType.collection_box in types
    # ...y NINGUNO es ProductType.other (excluye video game / plush / pin)
    assert ProductType.other not in types


def test_excludes_non_tcg():
    names = " ".join(p.set_name.lower() for p in _parse())
    assert "video game" not in names
    assert "plush" not in names
    assert "pin" not in names


def test_price_from_page_or_default():
    by_type = {p.product_type: p for p in _parse()}
    # ETB y bundle traen precio explícito de la página
    assert by_type[ProductType.elite_trainer_box].official_msrp == 59.99
    assert by_type[ProductType.booster_bundle].official_msrp == 26.99
    # El booster display no lista precio -> cae al MSRP de referencia
    assert by_type[ProductType.booster_box].official_msrp == DEFAULT_MSRP_BY_TYPE[
        ProductType.booster_box
    ]


def test_set_name_cleaned():
    etb = next(p for p in _parse() if p.product_type == ProductType.elite_trainer_box)
    assert "elite trainer box" not in etb.set_name.lower()
    assert "Chaos Rising" in etb.set_name


def test_release_date_defaults_to_page_month():
    assert all(p.release_date == date(2026, 6, 1) for p in _parse())


def test_merge_preserves_seed_data():
    seed = [
        Product(
            id="sv-chaos-rising-etb",
            set_name="Chaos Rising",
            product_type=ProductType.elite_trainer_box,
            official_msrp=59.99,
            skus={"target": "12345"},
        )
    ]
    merged = merge_discovered(seed, _parse())
    etb = next(p for p in merged if p.product_type == ProductType.elite_trainer_box)
    # Conserva id y skus del seed pese a venir también del radar
    assert etb.id == "sv-chaos-rising-etb"
    assert etb.skus == {"target": "12345"}
    # Y añade los productos nuevos descubiertos
    assert any(p.product_type == ProductType.tin for p in merged)
