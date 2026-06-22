"""Provider de Amazon (stub).

HONESTIDAD: la Product Advertising API 5.0 requiere una cuenta de Amazon
Associates ACTIVA (con ventas cualificadas) y firma AWS SigV4 de cada request.
Scrapear la página de producto está fuertemente protegido. Sin credenciales el
provider se declara no disponible.
"""

from __future__ import annotations

from ..models import Product, RetailerListing
from .base import ProviderUnavailable, StockProvider, register_provider


@register_provider
class AmazonProvider(StockProvider):
    name = "amazon"
    viability = "requiere PA-API 5.0 (cuenta de afiliado activa); no viable gratis"
    requires_env = ("AMAZON_ACCESS_KEY", "AMAZON_SECRET_KEY", "AMAZON_PARTNER_TAG")

    def check(self, product: Product) -> RetailerListing | None:
        raise ProviderUnavailable(
            "Amazon requiere credenciales PA-API 5.0 (Associates activo)"
        )
