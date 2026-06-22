"""Persistencia del estado y del catálogo en JSON (escritura atómica).

El estado canónico vive en `docs/data/` para que GitHub Pages lo sirva
directamente y el dashboard haga `fetch('data/state.json')`.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

import yaml

from .models import Product, State

logger = logging.getLogger(__name__)

DATA_DIR = Path("docs/data")
STATE_PATH = DATA_DIR / "state.json"
CATALOG_PATH = DATA_DIR / "catalog.json"


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def write_state(state: State, path: Path = STATE_PATH) -> None:
    _atomic_write(path, state.model_dump_json(indent=2))
    logger.info("Estado escrito en %s (%d listings)", path, len(state.listings))


def read_state(path: Path = STATE_PATH) -> State | None:
    if not path.exists():
        return None
    return State.model_validate_json(path.read_text())


def write_catalog(products: list[Product], path: Path = CATALOG_PATH) -> None:
    payload = [p.model_dump(mode="json") for p in products]
    _atomic_write(path, json.dumps(payload, indent=2, ensure_ascii=False))
    logger.info("Catálogo escrito en %s (%d productos)", path, len(products))


def read_catalog(path: Path = CATALOG_PATH) -> list[Product]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text())
    return [Product.model_validate(item) for item in payload]


def load_seed_products(path: str | Path = "config/products.yaml") -> list[Product]:
    """Carga el seed de productos/MSRP desde YAML."""
    data = yaml.safe_load(Path(path).read_text()) or {}
    return [Product.model_validate(item) for item in data.get("products", [])]
