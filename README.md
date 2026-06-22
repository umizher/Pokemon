# Monitor de Lanzamientos Pokémon TCG — Stock + MSRP

App open-source que detecta producto **sellado de Pokémon TCG (solo cartas)** próximo
o recién anunciado, vigila **qué retailers lo tienen en stock a MSRP o por debajo**, y
**alerta** apenas se cumple — para comprar antes de que se agote.

> Solo cartas (booster boxes, ETB, bundles, blisters, tins, collection boxes).
> Sin auto-checkout: solo detección y alerta.

## Estado del proyecto (por fases)

- [x] **Fase 1 — Scaffolding**: modelos, interfaz de provider/notifier/radar, config,
  seed de MSRP, store de estado, filtro MSRP, dedupe, orquestador y CLI.
- [ ] **Fase 2** — Providers Best Buy + Target end-to-end + Discord.
- [ ] **Fase 3** — Release Radar (pokemon.com).
- [ ] **Fase 4** — Dashboard en GitHub Pages.
- [ ] **Fase 5** — GitHub Actions cron + secrets.
- [ ] **Fase 6** — Más providers + anti-bot + alertas de fallo + Telegram/Email.

## Arquitectura

Sistema de **providers enchufables**. Cada retailer implementa
`StockProvider.check(product) -> RetailerListing`; cada fuente de noticias implementa
`NewsProvider.discover()`; cada canal de alerta implementa `Notifier.send(alert)`. Un
orquestador central recorre los providers (**aislando fallos**: uno que rompa no afecta
al resto), normaliza resultados, aplica el filtro MSRP, persiste el estado y notifica.

```
config/            settings.yaml (tolerancia, dedupe, providers) + products.yaml (seed/MSRP)
src/tcg_monitor/   models, http_client (anti-bot), store, filters, dedupe, orchestrator
  providers/       base + (bestbuy, target, ...)        [retailers]
  radar/           base + pokemon_official              [noticias]
  notify/          base + discord/telegram/email        [alertas]
docs/              dashboard estático (GitHub Pages) + data/state.json
tests/             parsers con fixtures, filtros, dedupe
```

## Setup local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env        # rellena tus claves/webhooks (NUNCA subas .env)

python -m tcg_monitor --once    # un ciclo -> escribe docs/data/state.json
pytest                          # tests
```

Modo backend (loop continuo, intervalos más cortos):

```bash
python -m tcg_monitor --loop --interval 600
```

## Realidades / honestidad técnica

- **Latencia**: con infra gratis (GitHub Actions cron) lo realista es revisar cada
  **~10–15 min**, con retrasos posibles. No sirve para drops que se agotan en segundos.
- **Viabilidad por retailer**:
  - **Best Buy** — API oficial gratuita, fiable. ✅
  - **Target** — endpoint RedSky público, pero **bloquea IPs tras pocos requests**
    (backoff obligatorio). Riesgo medio.
  - **Walmart / Amazon** — requieren aprobación de programa de afiliados.
  - **Pokémon Center** — Cloudflare; **best-effort, requiere proxy** (no viable gratis).
- **ToS**: scrapear puede violar los términos de cada tienda. Se prefieren APIs
  oficiales; el riesgo queda documentado.
- **Secrets**: webhooks y API keys van como GitHub Actions Secrets / `.env`.
  **Nunca** en el repositorio. Ver `.env.example`.

## Licencia

MIT.
