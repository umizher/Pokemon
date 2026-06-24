"use strict";

const STATE_URL = "data/state.json";

const TYPE_LABELS = {
  elite_trainer_box: "Elite Trainer Box",
  booster_bundle: "Booster Bundle",
  booster_box: "Booster Box",
  blister: "Blister",
  tin: "Tin",
  collection_box: "Collection",
  other: "Otro",
};

const STATE_LABELS = {
  in_stock: "En stock",
  preorder: "Preventa",
  out_of_stock: "Agotado",
  unknown: "—",
};

let STATE = null;

function fmtPrice(p, currency) {
  if (p === null || p === undefined) return "—";
  return `$${Number(p).toFixed(2)} ${currency || "USD"}`;
}

function fmtDate(iso) {
  if (!iso) return "Fecha por confirmar";
  const d = new Date(iso + (iso.length === 10 ? "T00:00:00" : ""));
  if (isNaN(d)) return iso;
  return d.toLocaleDateString("es", { year: "numeric", month: "long", day: "numeric" });
}

function fmtDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return isNaN(d) ? iso : d.toLocaleString();
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function isDeal(listing, product) {
  return (
    listing &&
    listing.stock_state === "in_stock" &&
    listing.price != null &&
    product.official_msrp != null &&
    listing.price <= product.official_msrp
  );
}

// Devuelve el mejor listing de Best Buy para un producto (si existe).
function bestbuyListing(listings) {
  return (listings || []).find((l) => l.retailer === "bestbuy") || null;
}

function statusBadge(listing, product) {
  if (!listing) return "";
  const state = listing.stock_state || "unknown";
  if (state === "unknown") return "";
  const label = STATE_LABELS[state] || state;
  const deal = isDeal(listing, product);
  const price = fmtPrice(listing.price, listing.currency);
  const priceHtml = listing.url
    ? `<a href="${escapeHtml(listing.url)}" target="_blank" rel="noopener">${price}</a>`
    : price;
  const dealBadge = deal ? '<span class="badge-msrp">≤ MSRP</span>' : "";
  return `<div class="bestbuy">
      Best Buy: <span class="state ${state}">${label}</span>
      ${state !== "out_of_stock" ? priceHtml : ""}${dealBadge}
    </div>`;
}

function daysUntil(iso) {
  if (!iso) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const d = new Date(iso + (iso.length === 10 ? "T00:00:00" : ""));
  if (isNaN(d)) return null;
  return Math.round((d - today) / 86400000);
}

function countdownBadge(iso) {
  const n = daysUntil(iso);
  if (n === null || n < 0) return "";
  if (n === 0) return '<span class="countdown today">¡Hoy!</span>';
  if (n === 1) return '<span class="countdown">Mañana</span>';
  return `<span class="countdown">Faltan ${n} días</span>`;
}

function card(product, listings) {
  const bb = bestbuyListing(listings);
  const deal = isDeal(bb, product);
  const stores = (product.retailers || []).length
    ? `<div class="stores">Dónde: ${product.retailers.map(escapeHtml).join(" · ")}</div>`
    : "";
  const img = product.image_url
    ? `<img class="thumb" src="${escapeHtml(product.image_url)}" alt="" loading="lazy" />`
    : "";
  return `
    <div class="card ${deal ? "deal" : ""}">
      ${img}
      <div class="type">${escapeHtml(TYPE_LABELS[product.product_type] || product.product_type)} · ${escapeHtml(product.language || "EN")}</div>
      <h3>${escapeHtml(product.set_name)}</h3>
      <div class="date">📅 ${fmtDate(product.release_date)} ${countdownBadge(product.release_date)}</div>
      <div class="msrp">MSRP: <strong>${fmtPrice(product.official_msrp, product.currency)}</strong></div>
      ${stores}
      ${statusBadge(bb, product)}
    </div>`;
}

function render() {
  if (!STATE) return;
  const term = document.getElementById("search").value.trim().toLowerCase();
  const onlyDeal = document.getElementById("only-deal").checked;

  const byProduct = {};
  for (const l of STATE.listings || []) {
    (byProduct[l.product_id] = byProduct[l.product_id] || []).push(l);
  }

  let products = (STATE.products || []).slice();
  if (term) {
    products = products.filter(
      (p) =>
        p.set_name.toLowerCase().includes(term) ||
        String(p.product_type).toLowerCase().includes(term)
    );
  }
  if (onlyDeal) {
    products = products.filter((p) => isDeal(bestbuyListing(byProduct[p.id]), p));
  }

  // Orden por fecha (sin fecha al final).
  products.sort((a, b) => {
    const da = a.release_date || "9999-12-31";
    const db = b.release_date || "9999-12-31";
    return da < db ? -1 : da > db ? 1 : 0;
  });

  const today = new Date().toISOString().slice(0, 10);
  const upcoming = products.filter((p) => !p.release_date || p.release_date >= today);
  const released = products.filter((p) => p.release_date && p.release_date < today);

  const renderInto = (id, list, empty) => {
    const el = document.getElementById(id);
    el.innerHTML = list.length
      ? list.map((p) => card(p, byProduct[p.id] || [])).join("")
      : `<p class="muted">${empty}</p>`;
  };
  renderInto("upcoming", upcoming, "Sin próximos lanzamientos que coincidan.");
  renderInto("released", released, "Nada por aquí todavía.");

  document.getElementById("status").textContent =
    `${products.length} producto(s) en el calendario · ${(STATE.listings || []).length} con datos de stock`;
}

function renderHealth(health) {
  const entries = Object.values(health || {});
  const el = document.getElementById("health");
  if (!entries.length) return;
  el.textContent =
    "Fuentes: " +
    entries.map((h) => `${h.name} ${h.ok ? "✓" : "✗"}`).join(" · ");
}

async function load() {
  try {
    const resp = await fetch(STATE_URL, { cache: "no-store" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    STATE = await resp.json();
  } catch (err) {
    document.getElementById("status").textContent =
      `No se pudo cargar ${STATE_URL}: ${err.message}`;
    return;
  }
  document.getElementById("last-checked").textContent =
    `Última actualización: ${fmtDateTime(STATE.generated_at)}`;
  renderHealth(STATE.providers_health);
  render();
}

document.getElementById("search").addEventListener("input", render);
document.getElementById("only-deal").addEventListener("change", render);
load();
