# Monitor de Lanzamientos Pokémon TCG — Stock + MSRP

App open-source que detecta producto **sellado de Pokémon TCG (solo cartas)** próximo
o recién anunciado, vigila **qué retailers lo tienen en stock a MSRP o por debajo**, y
**alerta** apenas se cumple — para comprar antes de que se agote.

> Solo cartas (booster boxes, ETB, bundles, blisters, tins, collection boxes).
> Sin auto-checkout: solo detección y alerta.

## Estado del proyecto (por fases)

- [x] **Fase 1 — Scaffolding**: modelos, interfaz de provider/notifier/radar, config,
  seed de MSRP, store de estado, filtro MSRP, dedupe, orquestador y CLI.
- [x] **Fase 2** — Providers Best Buy + Target end-to-end + Discord.
- [x] **Fase 3** — Release Radar (pokemon.com).
- [x] **Fase 4** — Dashboard en GitHub Pages.
- [x] **Fase 5** — GitHub Actions cron + secrets.
- [x] **Fase 6** — Más providers + anti-bot + alertas de fallo + Telegram/Email.

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

Ver el dashboard localmente:

```bash
python -m http.server -d docs 8099   # http://localhost:8099
```

Release Radar (descubre productos sellados nuevos y actualiza `docs/data/catalog.json`):

```bash
python -m tcg_monitor --radar          # solo descubrir + actualizar catálogo
python -m tcg_monitor --radar --once   # descubrir y luego revisar stock
```

> **Nota honesta:** pokemon.com está protegido por Akamai y devuelve **403 desde
> infra gratis** (GitHub Actions / contenedores sin proxy residencial). El radar
> degrada a "0 descubiertos" sin romper el ciclo; el catálogo sigue funcionando con
> el seed de `config/products.yaml`. El parser está testeado con un fixture y se
> activa en cuanto haya acceso (IP no bloqueada o proxy).

## Despliegue (GitHub Actions + Pages)

### 1. Configurar Secrets

En el repo: **Settings → Secrets and variables → Actions → New repository secret**.
Añade los que vayas a usar (todos son opcionales salvo el que habilite cada provider/canal):

| Secret | Para qué |
| --- | --- |
| `BESTBUY_API_KEY` | Provider Best Buy (gratis en developer.bestbuy.com) |
| `TARGET_API_KEY` | Override del key público de Target (opcional) |
| `DISCORD_WEBHOOK_URL` | Alertas a Discord |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Alertas a Telegram |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_TO` | Alertas por email |
| `HTTP_PROXY_URL` | Proxy residencial opcional (Target/Pokémon Center) |

### 2. Activar el scheduler

El workflow [`.github/workflows/monitor.yml`](.github/workflows/monitor.yml) corre
`python -m tcg_monitor --radar --once` cada **10 min** (`cron: '*/10 * * * *'`) y
también con **Run workflow** manual (`workflow_dispatch`). Hace commit de
`docs/data/state.json` y `catalog.json` cuando cambian, y cachea `dedupe.json`
entre ejecuciones para no repetir alertas.

> El cron de Actions es *best-effort*: puede retrasarse varios minutos. La
> granularidad mínima realista es ~5 min. Para drops que se agotan en segundos no
> es suficiente — considera un backend con `--loop` (Render/Railway/Fly).

Necesitas dar permiso de escritura al workflow: **Settings → Actions → General →
Workflow permissions → Read and write permissions** (el workflow ya declara
`permissions: contents: write`).

### 3. Activar GitHub Pages

**Settings → Pages → Build and deployment → Source: Deploy from a branch**, rama
`claude/pokemon-tcg-stock-monitor-qkatz4` (o `main` tras el merge) y carpeta
**`/docs`**. El dashboard quedará en `https://<usuario>.github.io/<repo>/` y leerá
`data/state.json` que actualiza el workflow.

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
