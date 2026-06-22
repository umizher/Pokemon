from datetime import datetime, timezone

from tcg_monitor.filters import meets_msrp, passes_alert_rule
from tcg_monitor.models import Product, RetailerListing, StockState


def _listing(price, state):
    return RetailerListing(
        product_id="p1",
        retailer="bestbuy",
        price=price,
        stock_state=state,
        last_checked=datetime.now(timezone.utc),
    )


def _product(msrp=59.99):
    return Product(id="p1", set_name="Test", official_msrp=msrp)


def test_meets_msrp_at_or_below():
    assert meets_msrp(59.99, 59.99) is True
    assert meets_msrp(49.99, 59.99) is True


def test_meets_msrp_above_fails_without_tolerance():
    assert meets_msrp(64.99, 59.99) is False


def test_meets_msrp_with_tolerance():
    # 5% de tolerancia: 59.99 * 1.05 = 62.99
    assert meets_msrp(62.00, 59.99, tolerance=0.05) is True
    assert meets_msrp(63.00, 59.99, tolerance=0.05) is False


def test_meets_msrp_missing_data_is_false():
    assert meets_msrp(None, 59.99) is False
    assert meets_msrp(59.99, None) is False


def test_alert_rule_requires_in_stock_and_msrp():
    p = _product()
    assert passes_alert_rule(_listing(49.99, StockState.in_stock), p) is True
    assert passes_alert_rule(_listing(49.99, StockState.preorder), p) is False
    assert passes_alert_rule(_listing(49.99, StockState.out_of_stock), p) is False
    assert passes_alert_rule(_listing(99.99, StockState.in_stock), p) is False
