"use strict";

const STATE_URL = "data/state.json";

const STATE_LABELS = {
  in_stock: "En stock",
  preorder: "Preorder",
  out_of_stock: "Agotado",
  unknown: "Desconocido",
};

let STATE = null; // estado cargado

function fmtPrice(p, currency) {
  if (p === null || p === undefined) return "—";
  return `$${Number(p).toFixed(2)} ${currency || "USD"}`;
}

function fmtDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return isNaN(d) ? iso : d.toLocaleString();
}

function fmtDate(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  return isNaN(d) ? iso : d.toLocaleDateString();
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

function renderHealth(health) {
  const el = document.getElementById("health");
  const entries = Object.values(health || {});
  if (!entries.length) {
    el.innerHTML = '<span class="muted">Sin providers activos.</span>';
    return;
  }
  el.innerHTML = entries
    .map((h) => {
      const cls = h.ok ? "ok" : "bad";
      const title = h.last_error ? ` title="${escapeHtml(h.last_error)}"` : "";
      return `<span class="pill"${title}><span class="dot ${cls}"></span>${escapeHtml(
        h.name
      )}</span>`;
    })
    .join("");
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function listingRow(listing, product) {
  const state = listing.stock_state || "unknown";
  const label = STATE_LABELS[state] || state;
  const deal = isDeal(listing, product);
  const dealBadge = deal ? '<span class="badge-msrp">≤MSRP</span>' : "";
  const price = fmtPrice(listing.price, listing.currency);
  const priceHtml = listing.url
    ? `<a href="${escapeHtml(listing.url)}" target="_blank" rel="noopener">${price}</a>`
    : price;
  return `
    <div class="listing">
      <span class="retailer">${escapeHtml(listing.retailer)}</span>
      <span>
        <span class="price">${priceHtml}</span>${dealBadge}
        <span class="state ${state}">${label}</span>
      </span>
    </div>`;
}

function productCard(product, listings) {
  const hasDeal = listings.some((l) => isDeal(l, product));
  const release = product.release_date
    ? `<div class="release">Lanzamiento: ${fmtDate(product.release_date)}</div>`
    : "";
  const rows = listings.length
    ? listings.map((l) => listingRow(l, product)).join("")
    : '<div class="listing"><span class="muted">Sin listings aún</span></div>';
  return `
    <div class="card ${hasDeal ? "deal" : ""}">
      <div class="type">${escapeHtml(product.product_type)} · ${escapeHtml(product.language)}</div>
      <h3>${escapeHtml(product.set_name)}</h3>
      ${release}
      <div class="msrp">MSRP: <strong>${fmtPrice(product.official_msrp, product.currency)}</strong></div>
      ${rows}
    </div>`;
}

function render() {
  if (!STATE) return;
  const term = document.getElementById("search").value.trim().toLowerCase();
  const onlyMsrp = document.getElementById("only-msrp").checked;

  const byProduct = {};
  for (const l of STATE.listings || []) {
    (byProduct[l.product_id] = byProduct[l.product_id] || []).push(l);
  }

  let products = STATE.products || [];
  if (term) {
    products = products.filter(
      (p) =>
        p.set_name.toLowerCase().includes(term) ||
        String(p.product_type).toLowerCase().includes(term)
    );
  }
  if (onlyMsrp) {
    products = products.filter((p) =>
      (byProduct[p.id] || []).some((l) => isDeal(l, p))
    );
  }

  const cards = document.getElementById("cards");
  if (!products.length) {
    cards.innerHTML = '<p class="muted">No hay productos que coincidan.</p>';
  } else {
    cards.innerHTML = products
      .map((p) => productCard(p, byProduct[p.id] || []))
      .join("");
  }
  document.getElementById("status").textContent =
    `${products.length} producto(s) · ${(STATE.listings || []).length} listing(s)`;
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
    `Última revisión: ${fmtDateTime(STATE.generated_at)}`;
  renderHealth(STATE.providers_health);
  render();
}

document.getElementById("search").addEventListener("input", render);
document.getElementById("only-msrp").addEventListener("change", render);
load();
