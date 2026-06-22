"""Cliente HTTP compartido: headers realistas, rotación de User-Agent,
jitter entre requests y backoff exponencial ante 403/429/503.

Diseñado para aislar la lógica anti-bot en un solo sitio para que todos los
providers la reutilicen.
"""

from __future__ import annotations

import logging
import os
import random
import time
from collections.abc import Callable

import httpx

logger = logging.getLogger(__name__)

# Pool pequeño de User-Agents de navegadores reales y recientes.
USER_AGENTS: tuple[str, ...] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
)

# Códigos que indican rate-limit / bloqueo y justifican reintento con backoff.
RETRY_STATUS: frozenset[int] = frozenset({403, 429, 500, 502, 503})


class HttpError(Exception):
    """Fallo de red o de status agotados los reintentos."""


def random_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/html, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
    }
    if extra:
        headers.update(extra)
    return headers


def build_client(timeout: float = 20.0, **kwargs) -> httpx.Client:
    """Crea un httpx.Client con headers realistas y proxy opcional (env)."""
    proxy = os.getenv("HTTP_PROXY_URL") or None
    if proxy:
        kwargs.setdefault("proxy", proxy)
    return httpx.Client(
        timeout=timeout,
        headers=random_headers(),
        follow_redirects=True,
        **kwargs,
    )


def get_with_retry(
    client: httpx.Client,
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
    max_retries: int = 4,
    base_delay: float = 2.0,
    jitter: float = 0.75,
    sleep: Callable[[float], None] = time.sleep,
) -> httpx.Response:
    """GET con backoff exponencial + jitter ante errores transitorios/bloqueo.

    Lanza HttpError si se agotan los reintentos.
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            response = client.get(url, params=params, headers=headers)
        except httpx.HTTPError as exc:  # red caída, timeout, DNS, etc.
            last_exc = exc
            logger.warning("GET %s falló (intento %d): %s", url, attempt + 1, exc)
        else:
            if response.status_code not in RETRY_STATUS:
                return response
            last_exc = HttpError(f"status {response.status_code} en {url}")
            logger.warning(
                "GET %s -> %d (intento %d), reintentando",
                url,
                response.status_code,
                attempt + 1,
            )

        if attempt < max_retries - 1:
            delay = base_delay * (2**attempt) + random.uniform(0, jitter)
            sleep(delay)

    raise HttpError(f"agotados {max_retries} reintentos para {url}") from last_exc
