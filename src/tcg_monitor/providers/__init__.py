"""Providers de stock enchufables.

Importar este paquete registra todos los providers disponibles en el registro
de `base`. En Fase 1 todavía no hay implementaciones concretas.
"""

from __future__ import annotations

from . import base  # noqa: F401  (mantiene el registro accesible)
from . import bestbuy, target  # noqa: F401  (auto-registro)

# Fase 6: from . import walmart, amazon, pokemoncenter  # noqa: F401
