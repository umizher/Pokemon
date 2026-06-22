"""Providers de stock enchufables.

Importar este paquete registra todos los providers disponibles en el registro
de `base`. En Fase 1 todavía no hay implementaciones concretas.
"""

from __future__ import annotations

from . import base  # noqa: F401  (mantiene el registro accesible)

# Las fases siguientes importarán aquí cada provider para auto-registrarlo, p.ej.
# from . import bestbuy, target  # noqa: F401
