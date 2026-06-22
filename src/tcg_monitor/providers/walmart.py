"""Provider de Walmart (stub).

HONESTIDAD: el storefront de Walmart está protegido por Akamai y su API de
afiliados (walmart.io) requiere aprobación de programa + firma de requests. Sin
una `WALMART_API_KEY` aprobada no es viable desde infra gratis. Este provider se
declara no disponible hasta tener credenciales, y se marca en providers_health.
"""

from __future__ import annotations

from ..models import Product, RetailerListing
from .base import ProviderUnavailable, StockProvider, register_provider


@register_provider
class WalmartProvider(StockProvider):
    name = "walmart"
    viability = "requiere aprobación de afiliados (walmart.io); no viable gratis"
    requires_env = ("WALMART_API_KEY",)

    def check(self, product: Product) -> RetailerListing | None:
        raise ProviderUnavailable(
            "Walmart requiere WALMART_API_KEY aprobada (programa de afiliados)"
        )
