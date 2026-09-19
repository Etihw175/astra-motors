// จำลองการใช้งานจริงบนถนนไทย — ส่งเงื่อนไขไปให้ POST /api/simulation คำนวณ
"use strict";

renderHeader("thai-road");
renderFooter();

const VERDICT = {
  ok: { label: "ผ่านได้", cls: "badge-ok" },
  caution: { label: "ต้องระวัง", cls: "badge-warn" },
  danger: { label: "ไม่แนะนำ", cls: "badge-bad" },
};

let cars = [];
let presets = null;
let carId = null;
let runTimer = null;

/* ---------- ฟอร์ม ---------- */

function renderCarChips() {
  document.getElementById("sim-cars").innerHTML = cars
    .map(
      (c) => `<button type="button" class="chip ${c.id === carId ? "selected" : ""}"
                 role="radio" aria-checked="${c.id === carId}" data-car="${c.id}">${c.name}</button>`
    )
    .join("");

  document.querySelectorAll("[data-car]").forEach((btn) => {
    btn.addEventListener("click", () => {
      carId = btn.dataset.car;
      renderCarChips();
      syncLiftControl();
      run();
    });
  });
}

// รุ่นที่ไม่มีระบบยกหน้ารถต้องกดไม่ได้ ไม่ใช่กดแล้วเงียบ
function syncLiftControl() {
  const car = cars.find((c) => c.id === carId);
  const lift = car && car.road ? car.road.front_lift_mm : 0;
  const box = document.getElementById("sim-lift");
  const label = document.getElementById("sim-lift-label");

  box.disabled = !lift;
  if (!lift) {
    box.checked = false;
    label.textContent = `${car ? car.name : "รุ่นนี้"} ไม่มีระบบยกหน้ารถ`;
    label.classList.add("muted");
  } else {
    label.textContent = `เปิดใช้ระบบยกหน้ารถ (+${lift} มม.) ตอนข้ามเนิน`;
    label.classList.remove("muted");
  }
}

function renderPresets(zoneId, items, key, sliderId, valueId, unit) {
  const zone = document.getElementById(zoneId);
  zone.innerHTML = items
    .map((p) => `<button type="button" class="chip" data-value="${p[key]}">${p.label}</button>`)
    .join("");

  zone.querySelectorAll("[data-value]").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.getElementById(sliderId).value = btn.dataset.value;
      document.getElementById(valueId).textContent = `${btn.dataset.value} ${unit}`;
      markPreset(zoneId, btn.dataset.value);
      run();
    });
  });
}

function markPreset(zoneId, value) {
  document.querySelectorAll(`#${zoneId} [data-value]`).forEach((b) => {
    b.classList.toggle("selected", Number(b.dataset.value) === Number(value));
  });
}

function bindSlider(sliderId, valueId, unit, zoneId) {
  const el = document.getElementById(sliderId);
  el.addEventListener("input", () => {
    document.getElementById(valueId).textContent = `${el.value}${unit === "%" ? "%" : ` ${unit}`}`;
    if (zoneId) markPreset(zoneId, el.value);
    run();
  });
}

/* ---------- ผลลัพธ์ ---------- */

function scoreRing(total, grade) {
  const hue = total >= 80 ? "var(--ok)" : total >= 50 ? "var(--warn)" : "var(--bad)";
  return `
    <div class="score-ring" style="--pct:${total};--ring:${hue}">
      <div class="dial" role="img" aria-label="คะแนนรวม ${total} เต็ม 100">
        <b class="num">${total}</b>
        <small>/ 100</small>
      </div>
      <div class="score-text">
        <p class="eyebrow">เกรด ${grade.letter}</p>
        <h3>${grade.label}</h3>
        <p class="muted small">คะแนนรวมถ่วงน้ำหนักจาก 5 สถานการณ์ด้านล่าง</p>
      </div>
    </div>`;
}

function scenarioCard(s) {
  const v = VERDICT[s.verdict];
  const numbers = s.numbers
    ? `<div class="price-lines mt-2">
         <div class="price-line"><span class="lbl">ค่าน้ำมันต่อเดือน</span>
           <span class="num">${baht(s.numbers.cost_per_month)}</span></div>
         <div class="price-line"><span class="lbl">ค่าน้ำมันต่อปี</span>
           <span class="num">${baht(s.numbers.cost_per_year)}</span></div>
         <div class="price-line"><span class="lbl">วิ่งได้ต่อการเติมหนึ่งถัง</span>
           <span class="num">${s.numbers.tank_range_km.toLocaleString("th-TH")} กม.</span></div>
       </div>`
    : "";

  return `
    <div class="card scenario ${s.verdict}">
      <div class="scenario-head">
        <h3>${s.title}</h3>
        <span class="badge ${v.cls}">${v.label} · ${s.score}/100</span>
      </div>
      <p class="lead-line">${s.headline}</p>
      <p class="muted small">${s.detail}</p>
      ${numbers}
      <ul class="advice">${s.advice.map((a) => `<li>${a}</li>`).join("")}</ul>
    </div>`;
}

function rankingTable(ranking, activeId) {
  return `
    <div class="card">
      <h3>เทียบทุกรุ่นภายใต้เงื่อนไขเดียวกัน</h3>
      <div class="table-wrap mt-2">
        <table class="user-table">
          <thead>
            <tr><th>อันดับ</th><th>รุ่น</th><th>คะแนนรวม</th><th>ระยะใต้ท้องที่ใช้จริง</th><th>อัตราสิ้นเปลืองเฉลี่ย</th></tr>
          </thead>
          <tbody>
            ${ranking
              .map(
                (r, i) => `
              <tr class="${r.car_id === activeId ? "row-active" : ""}">
                <td class="num">${i + 1}</td>
                <td>${r.name}</td>
                <td class="num">${r.total}</td>
                <td class="num">${(r.effective_clearance_mm / 10).toFixed(1)} ซม.</td>
                <td class="num">${r.blended_kmpl} กม./ลิตร</td>
              </tr>`
              )
              .join("")}
          </tbody>
        </table>
      </div>
    </div>`;
}

function render(data) {
  const clearance = data.clearance;
  const liftLine = clearance.front_lift_active
    ? `${clearance.base_mm} มม. + ยกหน้า ${clearance.lift_mm} มม.`
    : `${clearance.base_mm} มม. (ไม่ได้ยกหน้า)`;

  document.getElementById("sim-result").innerHTML = `
    <div class="card sim-summary">
      ${scoreRing(data.score.total, data.score.grade)}
      <div class="clearance-line">
        <span class="lbl">ระยะใต้ท้องที่ใช้คำนวณ</span>
        <b class="num">${(clearance.effective_mm / 10).toFixed(1)} ซม.</b>
        <span class="muted small">${liftLine}</span>
      </div>
      ${data.note ? `<p class="muted small">${data.note}</p>` : ""}
    </div>
    <div class="grid grid-2 mt-2">${data.scenarios.map(scenarioCard).join("")}</div>
    ${rankingTable(data.ranking, data.car.id)}`;

  document.getElementById("sim-disclaimer").textContent = data.disclaimer;
}

/* ---------- ยิง API (หน่วงไว้เล็กน้อย ไม่ให้ลากสไลเดอร์แล้วยิงรัว) ---------- */

function body() {
  return {
    car_id: carId,
    flood_depth_cm: Number(document.getElementById("sim-flood").value),
    bump_height_cm: Number(document.getElementById("sim-bump").value),
    road_rough: Number(document.getElementById("sim-road").value),
    front_lift: document.getElementById("sim-lift").checked,
    km_per_year: Number(document.getElementById("sim-km").value) || 12000,
    traffic_share_pct: Number(document.getElementById("sim-traffic").value),
    fuel_price: Number(document.getElementById("sim-price").value) || 41.5,
  };
}

function run() {
  clearTimeout(runTimer);
  runTimer = setTimeout(async () => {
    try {
      render(await API.simulate(body()));
    } catch (err) {
      toast(err.message, "error");
    }
  }, 220);
}

/* ---------- เริ่มทำงาน ---------- */

async function initSimulation() {
  try {
    [cars, presets] = await Promise.all([API.cars(), API.simulationConditions()]);
  } catch (err) {
    return toast(err.message, "error");
  }

  carId = qs("car") || (Store.load("config") || {}).car_id || cars[0].id;
  if (!cars.some((c) => c.id === carId)) carId = cars[0].id;

  document.getElementById("sim-road").innerHTML = presets.roads
    .map((r) => `<option value="${r.rough}">${r.label}</option>`)
    .join("");
  document.getElementById("sim-km").value = presets.defaults.km_per_year;
  document.getElementById("sim-price").value = presets.defaults.fuel_price;
  document.getElementById("sim-traffic").value = presets.defaults.traffic_share_pct;
  document.getElementById("sim-traffic-val").textContent = `${presets.defaults.traffic_share_pct}%`;

  renderCarChips();
  syncLiftControl();
  renderPresets("sim-flood-presets", presets.floods, "depth_cm", "sim-flood", "sim-flood-val", "ซม.");
  renderPresets("sim-bump-presets", presets.bumps, "height_cm", "sim-bump", "sim-bump-val", "ซม.");
  markPreset("sim-flood-presets", 0);
  markPreset("sim-bump-presets", 0);

  bindSlider("sim-flood", "sim-flood-val", "ซม.", "sim-flood-presets");
  bindSlider("sim-bump", "sim-bump-val", "ซม.", "sim-bump-presets");
  bindSlider("sim-traffic", "sim-traffic-val", "%");
  ["sim-road", "sim-lift", "sim-km", "sim-price"].forEach((id) =>
    document.getElementById(id).addEventListener("change", run)
  );

  run();
}

initSimulation();
