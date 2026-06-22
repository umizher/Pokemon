"""Interfaz de fuente de noticias para el Release Radar."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Product

_REGISTRY: dict[str, type["NewsProvider"]] = {}


def register_news(cls: type["NewsProvider"]) -> type["NewsProvider"]:
    _REGISTRY[cls.name] = cls
    return cls


def get_registry() -> dict[str, type["NewsProvider"]]:
    return dict(_REGISTRY)


class NewsProvider(ABC):
    name: str = "base"

    @abstractmethod
    def discover(self) -> list[Product]:
        """Devuelve productos TCG sellados (solo cartas) detectados en la fuente."""
        raise NotImplementedError
