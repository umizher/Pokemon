"""Filtro MSRP y regla de alerta."""

from __future__ import annotations

from .models import Product, RetailerListing, StockState


def meets_msrp(
    price: float | None, msrp: float | None, tolerance: float = 0.0
) -> bool:
    """True si `price <= msrp * (1 + tolerance)`.

    Si falta el precio o el MSRP no podemos afirmar que esté a MSRP -> False.
    """
    if price is None or msrp is None:
        return False
    return price <= msrp * (1 + tolerance)


def passes_alert_rule(
    listing: RetailerListing, product: Product, tolerance: float = 0.0
) -> bool:
    """Dispara la alerta solo si está en stock Y a MSRP o por debajo."""
    if listing.stock_state != StockState.in_stock:
        return False
    return meets_msrp(listing.price, product.official_msrp, tolerance)
