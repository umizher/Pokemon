"""Provider de Pokémon Center (stub best-effort).

HONESTIDAD: Pokémon Center no tiene API pública y está protegido por Cloudflare
(JS challenge / detección de bots). Requiere un navegador headless con técnicas
de stealth y, casi con seguridad, un proxy residencial — no es viable desde
infra gratis. Se declara disponible SOLO si hay `HTTP_PROXY_URL`, y aun así es
best-effort.
"""

from __future__ import annotations

import os

from ..models import Product, RetailerListing
from .base import ProviderUnavailable, StockProvider, register_provider


@register_provider
class PokemonCenterProvider(StockProvider):
    name = "pokemoncenter"
    viability = "Cloudflare; best-effort, requiere proxy residencial + headless"
    requires_env = ()

    def available(self) -> bool:
        # Sin proxy ni soporte headless instalado, no intentamos siquiera.
        return bool(os.getenv("HTTP_PROXY_URL"))

    def check(self, product: Product) -> RetailerListing | None:
        raise ProviderUnavailable(
            "Pokémon Center requiere headless+stealth y proxy residencial (best-effort)"
        )
