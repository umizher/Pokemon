"""Interfaz de notificador + registro enchufable."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Alert

_REGISTRY: dict[str, type["Notifier"]] = {}


def register_notifier(cls: type["Notifier"]) -> type["Notifier"]:
    _REGISTRY[cls.name] = cls
    return cls


def get_registry() -> dict[str, type["Notifier"]]:
    return dict(_REGISTRY)


class Notifier(ABC):
    name: str = "base"
    requires_env: tuple[str, ...] = ()

    def available(self) -> bool:
        import os

        return all(os.getenv(var) for var in self.requires_env)

    @abstractmethod
    def send(self, alert: Alert) -> bool:
        """Envía la alerta. Devuelve True si tuvo éxito."""
        raise NotImplementedError
