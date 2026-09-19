// หน้าแรก (journey ขั้นตอน 1-2): hero + โปรโมชั่น + ค้นหา/กรองรุ่นรถ + รีวิวจากสมาชิก
"use strict";

renderHeader("home");
renderFooter();

const HERO_COLOR = "#C8102E"; // แดง Rosso Corsa — สีซูเปอร์คาร์ในใจทุกคน
const BUDGETS = [12_000_000, 15_000_000, 20_000_000, 25_000_000];

let filterTimer = null;

/* ---------- hero: ใช้ข้อมูลรุ่นท็อปจริงจาก API ---------- */

function renderHero(cars) {
  const top = cars.find((c) => c.id === "ferrari-488") || cars[0];
  document.getElementById("hero-ticker").innerHTML = `
    <span><b class="num"><span id="tick-hp">0</span> <i>HP</i></b>กำลังสูงสุด</span>
    <span><b class="num"><span id="tick-tq">0</span> <i>Nm</i></b>แรงบิด</span>
    <span><b class="num"><span id="tick-ac">0</span> <i>วิ</i></b>0–100 กม./ชม.</span>
    <span><b class="num"><span id="tick-md">0</span> <i>รุ่น</i></b>ให้เลือกเปรียบเทียบ</span>`;
  if (window.FX) {
    FX.countUp(document.getElementById("tick-hp"), top.power_hp);
    FX.countUp(document.getElementById("tick-tq"), top.torque_nm);
    FX.countUp(document.getElementById("tick-ac"), top.accel);
    FX.countUp(document.getElementById("tick-md"), cars.length);
  }

  // HUD สเปคลอยรอบตัวรถ + แถบรายชื่อรุ่นวิ่ง (marquee) ขอบล่าง hero
  document.getElementById("hud-1").innerHTML = `${top.power_hp} <i>HP</i>`;
  document.getElementById("hud-2").innerHTML = `${top.torque_nm} <i>Nm</i>`;
  document.getElementById("hud-3").innerHTML = `${top.accel} <i>วิ · 0–100</i>`;
  const seq = cars
    .map((c) => `<b>${c.name}</b><span class="sl">//</span><span>${c.power_hp} HP · เริ่มต้น ${baht(c.price)}</span>`)
    .join('<span class="sl">///</span>');
  document.getElementById("marquee-track").innerHTML =
    `<span class="seq">${seq}</span><span class="seq">${seq}</span>`;
}

/* ---------- ขั้นตอน 1: โปรโมชั่น ---------- */

async function renderPromotions() {
  const zone = document.getElementById("promo-grid");
  try {
    const promos = await API.promotions();
    if (!promos.length) {
      document.getElementById("promo-section").classList.add("hidden");
      return;
    }
    zone.innerHTML = promos
      .map(
        (p) => `
        <a class="promo-card" href="/pages/model.html?id=${p.car_id}">
          <span class="car">${esc(p.car_name)}</span>
          <b>${esc(p.title)}</b>
          <span class="left">เหลืออีก ${p.days_left} วัน · ถึง ${thaiDate(p.expires)}</span>
        </a>`
      )
      .join("");
  } catch (err) {
    zone.innerHTML = `<p class="muted">${esc(err.message)}</p>`;
  }
}

/* ---------- ขั้นตอน 2: ค้นหา / กรอง ---------- */

function currentFilters() {
  return {
    q: document.getElementById("f-q").value.trim(),
    brand: document.getElementById("f-brand").value,
    drive: document.getElementById("f-drive").value,
    max_price: document.getElementById("f-max").value,
    sort: document.getElementById("f-sort").value,
  };
}

function skeleton(grid) {
  grid.innerHTML = Array.from({ length: 4 })
    .map(
      () => `
      <div class="skel-card" aria-hidden="true">
        <div class="skel-visual shimmer-overlay"></div>
        <div class="skel-line shimmer-overlay w60"></div>
        <div class="skel-line shimmer-overlay"></div>
        <div class="skel-line shimmer-overlay w40"></div>
      </div>`
    )
    .join("");
}

function renderCars(cars) {
  const grid = document.getElementById("car-grid");
  grid.setAttribute("aria-busy", "false");
  if (!cars.length) {
    grid.innerHTML = `<div class="card text-center muted" style="grid-column:1/-1">
      ไม่พบรุ่นที่ตรงกับเงื่อนไข ลองขยายงบประมาณหรือล้างตัวกรอง</div>`;
    return;
  }
  grid.innerHTML = cars
    .map((car, i) => {
      const defaultColor = car.colors.find((c) => c.extra === 0) || car.colors[0];
      return `
      <article class="car-card rise" style="animation-delay:${i * 90}ms">
        <div class="visual">${carVisual3D(car.id, defaultColor.hex)}</div>
        <div class="body">
          ${stars(car.rating.avg, car.rating.count)}
          <h3>${car.name}</h3>
          <p class="tagline">${car.tagline}</p>
          <p class="price">${baht(car.price)} <small>ราคาเริ่มต้น</small></p>
          <div class="actions">
            <a class="btn btn-primary" href="/pages/model.html?id=${car.id}">ดูรายละเอียด</a>
            <a class="btn btn-ghost" href="/pages/test-drive.html?car=${car.id}">ทดลองขับ</a>
          </div>
        </div>
      </article>`;
    })
    .join("");
  initCarVisuals();
  if (window.FX) FX.bindCardFX(grid);
}

async function searchCars() {
  const grid = document.getElementById("car-grid");
  const filters = currentFilters();
  const active = Boolean(filters.q || filters.brand || filters.drive || filters.max_price);
  document.getElementById("filter-reset").classList.toggle("hidden", !active);
  grid.setAttribute("aria-busy", "true");
  try {
    const cars = await API.cars(filters);
    document.getElementById("filter-count").textContent = active
      ? `พบ ${cars.length} รุ่นที่ตรงเงื่อนไข`
      : `ทั้งหมด ${cars.length} รุ่น`;
    renderCars(cars);
  } catch (err) {
    grid.innerHTML = `<p class="muted">${esc(err.message)}</p>`;
  }
}

async function initFilters() {
  const facets = await API.carFacets();
  const brand = document.getElementById("f-brand");
  brand.innerHTML += facets.brands.map((b) => `<option value="${esc(b)}">${esc(b)}</option>`).join("");
  document.getElementById("f-drive").innerHTML += facets.drives
    .map((d) => `<option value="${d.id}">${d.label}</option>`)
    .join("");
  document.getElementById("f-max").innerHTML += BUDGETS.filter((b) => b >= facets.price.min)
    .map((b) => `<option value="${b}">ไม่เกิน ${(b / 1_000_000).toLocaleString("th-TH")} ล้านบาท</option>`)
    .join("");
  document.getElementById("f-sort").innerHTML = facets.sorts
    .map((s) => `<option value="${s.id}">${s.label}</option>`)
    .join("");

  const form = document.getElementById("filter-form");
  form.addEventListener("submit", (e) => e.preventDefault());
  form.addEventListener("change", searchCars);
  // พิมพ์ค้นหา: รอให้หยุดพิมพ์ 300ms ค่อยยิง API (ไม่ยิงทุกตัวอักษร)
  document.getElementById("f-q").addEventListener("input", () => {
    clearTimeout(filterTimer);
    filterTimer = setTimeout(searchCars, 300);
  });
  document.getElementById("filter-reset").addEventListener("click", () => {
    form.reset();
    searchCars();
  });
}

/* ---------- รีวิวล่าสุด ---------- */

async function renderReviews() {
  const zone = document.getElementById("review-grid");
  try {
    const reviews = await API.reviews(null, 6);
    zone.innerHTML = reviews.length
      ? reviews.map((r) => reviewCardHTML(r)).join("")
      : `<div class="card muted" style="grid-column:1/-1">ยังไม่มีรีวิว —
         เป็นคนแรกที่รีวิวได้ที่หน้า <a href="/pages/after-sales.html">หลังการขาย</a> (รับ 200 คะแนน)</div>`;
  } catch (err) {
    zone.innerHTML = `<p class="muted">${esc(err.message)}</p>`;
  }
}

async function initHome() {
  // hero ใช้โมเดล 3D ของ Ferrari 488 หมุนโชว์ (ลากหมุนได้)
  document.getElementById("hero-visual").innerHTML =
    carVisual3D("ferrari-488", HERO_COLOR, { height: 380, controls: true });
  initCarVisuals();
  skeleton(document.getElementById("car-grid"));

  try {
    const cars = await API.cars();
    renderHero(cars);
    renderCars(cars);
    document.getElementById("filter-count").textContent = `ทั้งหมด ${cars.length} รุ่น`;
  } catch (err) {
    document.getElementById("car-grid").innerHTML = `<p class="muted">${esc(err.message)}</p>`;
  }
  renderPromotions();
  renderReviews();
  initFilters().catch(() => null);
}

initHome();
