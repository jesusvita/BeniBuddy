// Benihana tip-out rates
const TEPPAN_RATE = 0.085; // 8.5%
const SUSHI_RATE  = 0.075; // 7.5%
const BAR_RATE    = 0.045; // 4.5%
const BUSSER_RATE = 0.01;  // 1% of total food sales (Teppan + Sushi)

function money(x) {
  if (!Number.isFinite(x)) x = 0;
  return `$${x.toFixed(2)}`;
}

function val(id) {
  const el = document.getElementById(id);
  if (!el) return 0;
  const v = parseFloat(el.value);
  return Number.isFinite(v) ? v : 0;
}

function calculate() {
  const teppan = val("teppan");
  const sushi  = val("sushi");
  const bar    = val("bar");

  const tipEl = document.getElementById("tip");
  const tipRaw = tipEl ? tipEl.value.trim() : "";
  const tip = tipRaw === "" ? null : val("tip");

  const teppanOut = teppan * TEPPAN_RATE;
  const sushiOut  = sushi * SUSHI_RATE;
  const barOut    = bar * BAR_RATE;

  const foodSales = teppan + sushi;
  const busserOut = foodSales * BUSSER_RATE;

  const totalOut = teppanOut + sushiOut + barOut + busserOut;

  // Write values into the new template IDs
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
    setText("netTips", money(tip - totalOut));
    if (netWrap) netWrap.style.display = "flex";
  } else {
    if (netWrap) netWrap.style.display = "none";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  ["teppan","sushi","bar","tip"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("input", calculate);
  });
  calculate();
});

