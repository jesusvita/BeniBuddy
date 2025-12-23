// Benihana tip-out rates
const TEPPAN_RATE = 0.085; // 8.5%
const SUSHI_RATE  = 0.075; // 7.5%
const BAR_RATE    = 0.045; // 4.5%
const BUSSER_RATE = 0.01;  // 1% of total food sales (Teppan + Sushi)

/* =========================
   Formatting helpers
   ========================= */
function money(x) {
  if (!Number.isFinite(x)) x = 0;
  return `$${x.toFixed(2)}`;
}

/* =========================
   Multi-number input parser
   Examples:
   "beer 20 wine 10" => 30
   "20+10" => 30
   "12.50 8" => 20.5
   ========================= */
function val(id) {
  const el = document.getElementById(id);
  if (!el) return 0;

  const raw = String(el.value ?? "").trim();
  if (raw === "") return 0;

  const matches = raw.match(/[-+]?\d*\.?\d+/g);
  if (!matches) return 0;

  return matches.reduce((sum, n) => sum + Number(n), 0);
}

/* =========================
   Calculator
   ========================= */
function calculate() {
  const teppan = val("teppan");
  const sushi  = val("sushi");
  const bar    = val("bar");

  const tipEl = document.getElementById("tip");
  const tipRaw = tipEl ? String(tipEl.value ?? "").trim() : "";
  const tip = tipRaw === "" ? null : val("tip");

  const teppanOut = teppan * TEPPAN_RATE;
  const sushiOut  = sushi * SUSHI_RATE;
  const barOut    = bar * BAR_RATE;

  const foodSales = teppan + sushi;
  const busserOut = foodSales * BUSSER_RATE;

  const totalOut = teppanOut + sushiOut + barOut + busserOut;

  const setText = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  };

  setText("teppanOut", money(teppanOut));
  setText("sushiOut",  money(sushiOut));
  setText("barOut",    money(barOut));
  setText("busserOut", money(busserOut));
  setText("totalOut",  money(totalOut));

  const netWrap = document.getElementById("netWrap");
  if (tip !== null) {
  const net = tip - totalOut;
  const netEl = document.getElementById("netTips");

  if (netEl) {
    netEl.textContent = money(net);

    // color based on positive / negative
    netEl.classList.remove("text-green-400", "text-red-400");

    if (net > 0) {
      netEl.classList.add("text-green-400");
    } else if (net < 0) {
      netEl.classList.add("text-red-400");
    }
  }

  if (netWrap) netWrap.style.display = "flex";
  }
  else {
    if (netWrap) netWrap.style.display = "none";
  }
}

/* =========================
   Last 2 Saves (Cookies)
   ========================= */
const SAVE_COOKIE = "tipcalc_last2";

function getSaves() {
  const match = document.cookie.match(new RegExp("(^| )" + SAVE_COOKIE + "=([^;]+)"));
  if (!match) return [];
  try {
    return JSON.parse(decodeURIComponent(match[2]));
  } catch {
    return [];
  }
}

function setSaves(data) {
  // 30 days
  document.cookie =
    SAVE_COOKIE +
    "=" +
    encodeURIComponent(JSON.stringify(data)) +
    "; path=/; max-age=" +
    60 * 60 * 24 * 30 +
    "; SameSite=Lax";
}

function saveCalc() {
  const saves = getSaves();

  // Grab current displayed totals (already formatted like $0.00)
  const total = document.getElementById("totalOut")?.textContent ?? "$0.00";

  // Only show net if the netWrap is visible
  const netWrap = document.getElementById("netWrap");
  const netVisible = netWrap && netWrap.style.display !== "none";
  const net = netVisible ? (document.getElementById("netTips")?.textContent ?? null) : null;

  saves.unshift({
    time: new Date().toLocaleString(),
    total,
    net
  });

  setSaves(saves.slice(0, 2));
  renderSaves();
}

function renderSaves() {
  const el = document.getElementById("lastSaves");
  if (!el) return;

  const saves = getSaves();
  if (!saves.length) {
    el.innerHTML = "";
    return;
  }

  el.innerHTML = saves
    .map((s, i) => {
      const netPart = s.net ? ` • Net: <strong>${s.net}</strong>` : "";
      return `<div class="opacity-80"> Total: <strong>${s.total}</strong>${netPart}</div>`;
    })
    .join("");
}

/* =========================
   Init
   ========================= */
document.addEventListener("DOMContentLoaded", () => {
  // Auto-calc on input
  ["teppan", "sushi", "bar", "tip"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("input", calculate);
  });

  // Initial calculate + show previous saves
  calculate();
  renderSaves();
});

