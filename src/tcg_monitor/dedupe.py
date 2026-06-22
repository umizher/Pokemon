"""Deduplicación de alertas, respaldada en disco.

Una alerta se identifica por (product_id, retailer, price). Si ya se envió
dentro de la ventana TTL, no se repite.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from pathlib import Path

logger = logging.getLogger(__name__)


class DedupeStore:
    def __init__(
        self,
        path: str | Path,
        ttl_hours: float = 6.0,
        now: Callable[[], float] = time.time,
    ) -> None:
        self.path = Path(path)
        self.ttl = ttl_hours * 3600.0
        self._now = now
        self._data: dict[str, float] = {}
        self._load()

    @staticmethod
    def _key(product_id: str, retailer: str, price: float | None) -> str:
        return f"{product_id}|{retailer}|{price}"

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            self._data = json.loads(self.path.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("No se pudo leer dedupe store %s: %s", self.path, exc)
            self._data = {}
        self._prune()

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._data))
        except OSError as exc:
            logger.warning("No se pudo guardar dedupe store %s: %s", self.path, exc)

    def _prune(self) -> None:
        cutoff = self._now() - self.ttl
        self._data = {k: ts for k, ts in self._data.items() if ts >= cutoff}

    def seen(self, product_id: str, retailer: str, price: float | None) -> bool:
        """True si esta alerta ya se envió dentro de la ventana TTL."""
        self._prune()
        return self._key(product_id, retailer, price) in self._data

    def mark(self, product_id: str, retailer: str, price: float | None) -> None:
        self._data[self._key(product_id, retailer, price)] = self._now()
        self._save()
