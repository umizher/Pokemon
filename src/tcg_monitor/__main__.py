"""CLI del monitor.

  python -m tcg_monitor --once             # un solo ciclo (GitHub Actions)
  python -m tcg_monitor --loop --interval 600   # loop continuo (backend)
"""

from __future__ import annotations

import argparse
import logging

from . import notify, providers, radar  # noqa: F401  (registra implementaciones)
from .config import Settings, load_settings
from .dedupe import DedupeStore
from .health import HealthTracker
from .models import Product
from .notify.base import Notifier, get_registry as notifier_registry
from .orchestrator import Orchestrator
from .providers.base import StockProvider, get_registry as provider_registry
from .radar.base import NewsProvider, get_registry as news_registry
from .store import (
    CATALOG_PATH,
    load_seed_products,
    merge_discovered,
    read_catalog,
    write_catalog,
)


def _merge_products(seed: list[Product], catalog: list[Product]) -> list[Product]:
    """Combina seed + catálogo descubierto; el catálogo gana por id."""
    merged: dict[str, Product] = {p.id: p for p in seed}
    for p in catalog:
        merged[p.id] = p
    return list(merged.values())


def build_stock_providers(settings: Settings) -> list[StockProvider]:
    registry = provider_registry()
    result: list[StockProvider] = []
    for name, enabled in settings.stock_providers.items():
        if not enabled:
            continue
        cls = registry.get(name)
        if cls is None:
            logging.warning("Provider '%s' habilitado pero no implementado aún", name)
            continue
        instance = cls(settings.__dict__)
        if not instance.available():
            logging.warning(
                "Provider '%s' habilitado pero no disponible (faltan %s o requiere proxy)",
                name,
                ", ".join(instance.requires_env) or "credenciales",
            )
            continue
        result.append(instance)
    return result


def build_notifiers(settings: Settings) -> list[Notifier]:
    registry = notifier_registry()
    result: list[Notifier] = []
    for name, enabled in settings.notifiers.items():
        if not enabled:
            continue
        cls = registry.get(name)
        if cls is None:
            logging.warning("Notificador '%s' habilitado pero no implementado aún", name)
            continue
        instance = cls()
        if not instance.available():
            logging.warning("Notificador '%s' sin credenciales; se omite", name)
            continue
        result.append(instance)
    return result


def build_news_providers(settings: Settings) -> list[NewsProvider]:
    registry = news_registry()
    result: list[NewsProvider] = []
    for name, enabled in settings.radar.items():
        if not enabled:
            continue
        cls = registry.get(name)
        if cls is None:
            logging.warning("Fuente de radar '%s' habilitada pero no implementada", name)
            continue
        result.append(cls())
    return result


def run_radar(settings: Settings, products: list[Product]) -> list[Product]:
    """Descubre productos nuevos y los fusiona con el catálogo (persistido)."""
    discovered: list[Product] = []
    for source in build_news_providers(settings):
        try:
            discovered.extend(source.discover())
        except Exception:
            logging.exception("Fuente de radar '%s' falló", source.name)
    merged = merge_discovered(products, discovered)
    write_catalog(merged)
    logging.info(
        "Radar: %d descubiertos, catálogo con %d productos", len(discovered), len(merged)
    )
    return merged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tcg-monitor")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="ejecuta un solo ciclo")
    mode.add_argument("--loop", action="store_true", help="ejecuta en loop continuo")
    parser.add_argument("--radar", action="store_true", help="ejecuta el Release Radar y actualiza el catálogo")
    parser.add_argument("--interval", type=float, default=600.0, help="segundos entre ciclos (--loop)")
    parser.add_argument("--config", default="config/settings.yaml")
    parser.add_argument("--products", default="config/products.yaml")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    settings = load_settings(args.config)
    products = _merge_products(load_seed_products(args.products), read_catalog(CATALOG_PATH))

    if args.radar:
        products = run_radar(settings, products)
    # Sin modo de ciclo, --radar es una acción autónoma.
    if args.radar and not (args.once or args.loop):
        return 0

    stock_providers = build_stock_providers(settings)
    notifiers = build_notifiers(settings)
    dedupe = DedupeStore("docs/data/dedupe.json", ttl_hours=settings.dedupe_hours)
    health = HealthTracker("docs/data/health.json")

    logging.info(
        "Catálogo: %d productos | providers activos: %s | notificadores: %s",
        len(products),
        [p.name for p in stock_providers] or "ninguno",
        [n.name for n in notifiers] or "ninguno",
    )

    orch = Orchestrator(settings, products, stock_providers, notifiers, dedupe, health)
    if args.loop:
        orch.run_loop(args.interval)
    else:
        orch.run_once()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
