"""Interfaz de provider de stock + registro enchufable.

Cada retailer se implementa como una subclase de `StockProvider` decorada con
`@register_provider`. El orquestador instancia los providers habilitados y
disponibles, y llama a `check(product)` para cada producto del catálogo.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Product, RetailerListing


class ProviderError(Exception):
    """Error recuperable durante un check (red, parsing, status)."""


class ProviderUnavailable(ProviderError):
    """El provider no puede ejecutarse (falta credencial, requiere proxy...)."""


# Registro nombre -> clase de provider.
_REGISTRY: dict[str, type["StockProvider"]] = {}


def register_provider(cls: type["StockProvider"]) -> type["StockProvider"]:
    _REGISTRY[cls.name] = cls
    return cls


def get_registry() -> dict[str, type["StockProvider"]]:
    return dict(_REGISTRY)


class StockProvider(ABC):
    #: nombre estable usado en config y en providers_health
    name: str = "base"
    #: nota honesta de viabilidad en infra gratis
    viability: str = "unknown"
    #: variables de entorno requeridas para operar
    requires_env: tuple[str, ...] = ()

    def __init__(self, settings: dict | None = None) -> None:
        self.settings = settings or {}

    def available(self) -> bool:
        """¿Puede ejecutarse? Por defecto, exige sus variables de entorno.

        Las subclases con requisitos extra (proxy, etc.) deben sobreescribir.
        """
        import os

        return all(os.getenv(var) for var in self.requires_env)

    @abstractmethod
    def check(self, product: Product) -> RetailerListing | None:
        """Consulta el estado del producto. Devuelve None si no aplica
        (p.ej. no hay SKU para este retailer). Lanza ProviderError ante fallo.
        """
        raise NotImplementedError
