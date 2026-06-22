"""Carga de configuración (YAML) y variables de entorno."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

try:  # carga .env si python-dotenv está disponible (opcional en runtime)
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass


@dataclass
class Settings:
    msrp_tolerance: float = 0.0
    dedupe_hours: float = 6.0
    store_id: str = "1357"
    zip: str = "10001"
    stock_providers: dict[str, bool] = field(default_factory=dict)
    notifiers: dict[str, bool] = field(default_factory=dict)
    radar: dict[str, bool] = field(default_factory=dict)


def load_settings(path: str | Path = "config/settings.yaml") -> Settings:
    data = yaml.safe_load(Path(path).read_text()) or {}
    return Settings(
        msrp_tolerance=float(data.get("msrp_tolerance", 0.0)),
        dedupe_hours=float(data.get("dedupe_hours", 6.0)),
        store_id=str(data.get("store_id", "1357")),
        zip=str(data.get("zip", "10001")),
        stock_providers=dict(data.get("stock_providers", {})),
        notifiers=dict(data.get("notifiers", {})),
        radar=dict(data.get("radar", {})),
    )


def env(name: str, default: str | None = None) -> str | None:
    """Lee una variable de entorno, devolviendo None si está vacía."""
    value = os.getenv(name, default)
    return value or None
