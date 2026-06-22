"""Seguimiento de fallos sostenidos por provider, respaldado en disco.

Cuenta fallos consecutivos por provider. Cuando un provider alcanza el umbral
exacto se dispara una alerta de salud (una sola vez por racha); al recuperarse
el contador se resetea.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class HealthTracker:
    def __init__(self, path: str | Path, threshold: int = 3) -> None:
        self.path = Path(path)
        self.threshold = threshold
        self._counts: dict[str, int] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            self._counts = json.loads(self.path.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("No se pudo leer health store %s: %s", self.path, exc)
            self._counts = {}

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._counts))
        except OSError as exc:
            logger.warning("No se pudo guardar health store %s: %s", self.path, exc)

    def update(self, name: str, ok: bool) -> int:
        """Actualiza el contador y devuelve los fallos consecutivos actuales."""
        count = 0 if ok else self._counts.get(name, 0) + 1
        self._counts[name] = count
        self._save()
        return count

    def should_alert(self, count: int) -> bool:
        """True solo al cruzar el umbral exacto (alerta única por racha)."""
        return count == self.threshold
