// เครื่องคำนวณไฟแนนซ์ (journey ขั้นตอน 3): เงินดาวน์/งวดผ่อน → ยอดผ่อนต่อเดือนหลายสถาบัน
"use strict";

renderHeader("finance");
renderFooter();

let cars = [];
let plans = [];
let carId = null;
let downPct = 25;
let term = 60;

const ALL_TERMS = [48, 60, 72, 84];

function currentCar() {
  return cars.find((c) => c.id === carId);
}

// ใช้ราคารวมจาก config ที่ผู้ใช้จัดสเปคไว้ (ถ้าเป็นรุ่นเดียวกัน) ไม่งั้นใช้ราคาเริ่มต้น
function carPrice() {
  const saved = Store.load("config");
  if (saved && saved.car_id === carId) return saved.total;
  return currentCar().price;
}

function renderTermChips() {
  const zone = document.getElementById("term-chips");
  zone.innerHTML = ALL_TERMS.map(
    (t) => `
    <button type="button" class="chip ${t === term ? "selected" : ""}" data-term="${t}"
            role="radio" aria-checked="${t === term}">${t} งวด</button>`
  ).join("");
  zone.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      term = Number(chip.dataset.term);
      renderTermChips();
      renderResults();
    });
  });
}

function renderResults() {
  const price = carPrice();
  const down = Math.round((price * downPct) / 100);
  const principal = price - down;

  document.getElementById("price-hint").textContent =
    `ราคารถ (ตามสเปคที่เลือกไว้): ${baht(price)}`;
  document.getElementById("down-label").textContent =
    ` ${downPct}% = ${baht(down)}`;

  document.getElementById("loan-summary").innerHTML = `
    <div class="price-line"><span class="lbl">ราคารถ</span><span class="val">${baht(price)}</span></div>
    <div class="price-line"><span class="lbl">เงินดาวน์ (${downPct}%)</span><span class="val">-${baht(down)}</span></div>
    <div class="price-line total"><span class="lbl">ยอดจัดไฟแนนซ์</span><span class="val">${baht(principal)}</span></div>`;

  document.getElementById("plan-list").innerHTML = plans
    .map((p) => {
      const termOk = p.terms.includes(term);
      const downOk = downPct >= p.min_down_pct;
      const eligible = termOk && downOk;
      const monthly = monthlyPayment(principal, p.flat_rate, term);
      const effective = (p.flat_rate * 1.8).toFixed(2); // อัตราที่แท้จริงโดยประมาณ

      let reason = "";
      if (!downOk) reason = `ต้องดาวน์ขั้นต่ำ ${p.min_down_pct}%`;
      else if (!termOk) reason = `รองรับเฉพาะ ${p.terms.join("/")} งวด`;

      return `
      <div class="card" style="${eligible ? "" : "opacity:.55"}">
        <div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:center">
          <div>
            <h3 style="font-size:18px">${p.name}
              ${p.promo ? '<span class="badge badge-accent">โปรโมชั่น</span>' : ""}
            </h3>
            <p class="muted small">${p.note}</p>
          </div>
          <div style="text-align:right">
            ${
              eligible
                ? `<p class="num" style="font-size:24px;color:var(--accent-strong)">${baht(monthly)}<span class="muted" style="font-size:13px;font-family:var(--font-body)">/เดือน</span></p>
                   <p class="muted small num">ดอกเบี้ย ${p.flat_rate}% (แท้จริง ~${effective}%)</p>`
                : `<span class="badge badge-warn">${reason}</span>`
            }
          </div>
        </div>
      </div>`;
    })
    .join("");
}

async function initFinance() {
  try {
    [cars, plans] = await Promise.all([API.cars(), API.financePlans()]);
  } catch (err) {
    document.getElementById("plan-list").innerHTML = `<p class="muted">${err.message}</p>`;
    return;
  }

  const saved = Store.load("config");
  carId = qs("car") || (saved && saved.car_id) || cars[0].id;
  if (!cars.some((c) => c.id === carId)) carId = cars[0].id;

  const select = document.getElementById("car-select");
  select.innerHTML = cars
    .map((c) => `<option value="${c.id}" ${c.id === carId ? "selected" : ""}>${c.name}</option>`)
    .join("");
  select.addEventListener("change", () => {
    carId = select.value;
    renderResults();
  });

  const range = document.getElementById("down-range");
  range.addEventListener("input", () => {
    downPct = Number(range.value);
    renderResults();
  });

  renderTermChips();
  renderResults();
}

initFinance();
