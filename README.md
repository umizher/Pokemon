# Calendario Pokémon TCG — Lanzamientos + MSRP

App open-source que te muestra, para **producto sellado de Pokémon TCG (solo cartas)**:

1. **Qué sale de nuevo** (booster boxes, ETB, bundles, blisters, tins, collections).
2. **Cuándo** (fecha de lanzamiento) y **a qué precio oficial (MSRP)**.
3. **Dónde** se venderá (tiendas), y **si hay stock a MSRP en Best Buy**.

> Solo cartas. Sin auto-checkout: solo información y aviso.

## Cómo funciona (en simple)

- **El calendario funciona sin configurar NADA.** Abres el dashboard y ves los próximos
  lanzamientos con su fecha, MSRP y tiendas. Esto sale de `config/products.yaml` (semilla)
  y se puede ampliar solo.
- **El estado de stock necesita la API gratuita de Best Buy.** No se paga: te registras en
  [developer.bestbuy.com](https://developer.bestbuy.com/) (2 min), copias tu clave en
  `BESTBUY_API_KEY`, y la app te dice cuándo hay stock **a MSRP o menos** en Best Buy.
  Esa misma clave también **amplía el calendario** automáticamente (productos en preventa
  con su fecha y precio reales).

### ¿Por qué no "todas las tiendas sin nada"?

Para saber si hay stock **ahora mismo** hay que preguntarle a la tienda, y eso requiere su
API o scraping. Best Buy tiene API gratis (por eso es la recomendada). **Target, Walmart,
Amazon y Pokémon Center** exigen aprobación de afiliados o se protegen con anti-bot
(Cloudflare/Akamai) y normalmente **se bloquean desde infraestructura gratis sin un proxy
de pago** — están incluidos como opcionales y se marcan claramente, no se finge que
funcionan.

## Arquitectura

Sistema de **providers enchufables**. Cada retailer implementa
`StockProvider.check(product) -> RetailerListing`; cada fuente de noticias implementa
`NewsProvider.discover()`; cada canal de alerta implementa `Notifier.send(alert)`. Un
orquestador central recorre los providers (**aislando fallos**: uno que rompa no afecta
al resto), normaliza resultados, aplica el filtro MSRP, persiste el estado y notifica.

```
config/            settings.yaml (qué activar) + products.yaml (calendario semilla + MSRP)
src/tcg_monitor/   models, http_client (anti-bot), store, filters, dedupe, orchestrator
  providers/       base + bestbuy (+ target/walmart/amazon/pokemoncenter opcionales)
  radar/           base + bestbuy_radar (calendario) + pokemon_official (opcional)
  notify/          base + discord/telegram/email        [alertas, opcionales]
docs/              dashboard "calendario" estático (GitHub Pages) + data/state.json
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

Actualizar el calendario (radar) y revisar stock:

```bash
python -m tcg_monitor --radar          # amplía el calendario (necesita BESTBUY_API_KEY)
python -m tcg_monitor --radar --once   # amplía calendario y revisa stock en Best Buy
```

> **Nota honesta sobre la red:** el entorno de desarrollo de este repo sale por un
> proxy con política de egreso, así que **no se puede comprobar el acceso a sitios
> externos desde ahí** (devuelve 403 a casi todo). El flujo real (API de Best Buy y
> opcionalmente pokemon.com) se valida en **GitHub Actions** (internet abierto) o
> ejecutándolo en tu máquina. La fuente `pokemon_official` queda **opcional/off por
> defecto** porque pokemon.com puede bloquear según la IP; el calendario semilla y el
> radar de Best Buy no dependen de ella.

## Notificaciones y robustez

- **Canales** (se activan solo si hay credenciales): **Discord** (webhook, default),
  **Telegram** (Bot API) y **Email** (SMTP). Habilítalos en `config/settings.yaml`.
- **Deduplicación**: una alerta `(producto, retailer, precio)` no se repite dentro de
  `dedupe_hours` (default 6h). Persistida en `docs/data/dedupe.json`.
- **Alertas de fallo sostenido**: si un provider falla N ciclos seguidos (umbral 3) se
  envía un aviso por los canales activos, una sola vez por racha; se resetea al
  recuperarse. Estado persistido en `docs/data/health.json`.
- **Aislamiento**: el fallo de un provider nunca rompe a los demás (se refleja en
  `providers_health` y en el dashboard con un badge rojo).
- **Anti-bot**: `http_client` rota User-Agent, usa headers realistas, jitter entre
  requests y backoff exponencial ante 403/429/503. Proxy opcional vía `HTTP_PROXY_URL`.

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
`main` (tras el merge) y carpeta **`/docs`**. El dashboard quedará en
`https://<usuario>.github.io/<repo>/` y leerá `data/state.json` que actualiza el workflow.

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
