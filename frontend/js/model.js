// หน้ารายละเอียดรุ่น (journey ขั้นตอน 2): เลือกสี/ออปชัน ราคาอัปเดต real-time
"use strict";

renderHeader("home");
renderFooter();

let car = null;
let colorId = null;
let optionIds = new Set();

function currentColor() {
  return car.colors.find((c) => c.id === colorId);
}

function totalPrice() {
  const opts = car.options.filter((o) => optionIds.has(o.id));
  return car.price + currentColor().extra + opts.reduce((sum, o) => sum + o.price, 0);
}

// เก็บ config ปัจจุบันไว้ให้หน้า "จองรถ" และ "ไฟแนนซ์" ใช้ต่อ
function saveConfig() {
  Store.save("config", {
    car_id: car.id,
    color_id: colorId,
    option_ids: [...optionIds],
    total: totalPrice(),
  });
}

/* ---------- ภาพรถ: โมเดล 3D (มี SVG เป็น placeholder/fallback ในตัวจาก ui.js) ---------- */

let paintWarned = false;

function renderVisual() {
  const zone = document.getElementById("car-visual");
  const hex = currentColor().hex;

  // ครั้งแรก: สร้าง placeholder แล้วปล่อยให้ ui.js อัปเกรดเป็นโมเดล 3D
  if (!zone.dataset.init) {
    zone.dataset.init = "1";
    zone.innerHTML =
      carVisual3D(car.id, hex, { height: 400, controls: true }) +
      '<p class="muted small mt-1">ลากเพื่อหมุนดูรอบคัน 360°</p>';
    initCarVisuals();
    return;
  }

  // ผู้ใช้เปลี่ยนสี: อัปเดตโมเดล 3D ถ้าโหลดแล้ว / อัปเดต SVG ถ้ายังไม่โหลด
  const wrap = zone.querySelector(".car-3d-wrap");
  if (!wrap) return;
  wrap.dataset.color = hex; // เผื่อโมเดลยังโหลดอยู่ — สีล่าสุดจะถูกทาตอนโหลดเสร็จ
  const viewer = wrap.querySelector("model-viewer");
  if (viewer && viewer.model) {
    const hit = recolorViewer(viewer, hex);
    if (hit === 0 && !paintWarned) {
      paintWarned = true;
      toast("โมเดล 3D นี้ไม่รองรับการเปลี่ยนสี — สีที่เลือกมีผลกับราคาเท่านั้น");
    }
  } else if (!viewer) {
    wrap.innerHTML = carSVG(hex); // ยังเป็น SVG placeholder อยู่
  }
}

function renderSwatches() {
  const zone = document.getElementById("swatches");
  zone.innerHTML = car.colors
    .map(
      (c) => `
      <button type="button" class="swatch ${c.id === colorId ? "selected" : ""}"
              style="background:${c.hex}" data-id="${c.id}" role="radio"
              aria-checked="${c.id === colorId}" aria-label="${c.name}"></button>`
    )
    .join("");
  zone.querySelectorAll(".swatch").forEach((btn) => {
    btn.addEventListener("click", () => {
      colorId = btn.dataset.id;
      renderSwatches();
      renderVisual();
      renderColorInfo();
      renderPrice();
    });
  });
}

function renderColorInfo() {
  const c = currentColor();
  // Edge case: สีที่เลือกไม่มีในสต็อก — แจ้งระยะเวลารอผลิตชัดเจน
  document.getElementById("color-info").innerHTML =
    `<strong>${c.name}</strong>` +
    (c.extra > 0 ? ` <span class="muted small">(+${baht(c.extra)})</span>` : "") +
    ` &nbsp;${stockBadge(c.stock)}`;
}

function renderOptions() {
  const zone = document.getElementById("options");
  zone.innerHTML = car.options
    .map(
      (o) => `
      <label class="option-row">
        <input type="checkbox" data-id="${o.id}" ${optionIds.has(o.id) ? "checked" : ""}>
        <span class="name">${o.name}</span>
        <span class="price num">+${baht(o.price)}</span>
      </label>`
    )
    .join("");
  zone.querySelectorAll("input").forEach((cb) => {
    cb.addEventListener("change", () => {
      cb.checked ? optionIds.add(cb.dataset.id) : optionIds.delete(cb.dataset.id);
      renderPrice();
    });
  });
}

function renderPrice() {
  const c = currentColor();
  const opts = car.options.filter((o) => optionIds.has(o.id));
  const lines = [
    `<div class="price-line"><span class="lbl">ราคาเริ่มต้น</span><span class="val">${baht(car.price)}</span></div>`,
    `<div class="price-line"><span class="lbl">สี ${c.name}</span><span class="val">${c.extra > 0 ? "+" + baht(c.extra) : "รวมในราคา"}</span></div>`,
    ...opts.map(
      (o) =>
        `<div class="price-line"><span class="lbl">${o.name}</span><span class="val">+${baht(o.price)}</span></div>`
    ),
    `<div class="price-line total"><span class="lbl">ราคารวม</span><span class="val">${baht(totalPrice())}</span></div>`,
  ];
  document.getElementById("price-lines").innerHTML = lines.join("");
  saveConfig();
}

function renderPromo() {
  if (!car.promotion) return;
  const expired = new Date(`${car.promotion.expires}T23:59:59`) < new Date();
  // Edge case: โปรโมชั่นหมดอายุ — แสดงสถานะชัดเจน ไม่หลอกให้เข้าใจผิด
  document.getElementById("promo-zone").innerHTML = `
    <div class="promo ${expired ? "expired" : ""}">
      <div>
        <p class="t">${car.promotion.title}</p>
        <p class="exp">${
          expired
            ? "โปรโมชั่นนี้หมดอายุแล้ว — ราคาจองจะไม่รวมโปรโมชั่นนี้"
            : "ถึงวันที่ " + thaiDate(car.promotion.expires) + " — ล็อกโปรฯ นี้ได้ทันทีเมื่อวางเงินจอง"
        }</p>
      </div>
      ${expired ? "" : '<span class="badge badge-accent">โปรโมชั่น</span>'}
    </div>`;
}

function renderSpecs() {
  const cells = [
    ["เครื่องยนต์", car.engine],
    ["กำลังสูงสุด", `${car.power_hp} HP`],
    ["แรงบิด", `${car.torque_nm} Nm`],
    ["0–100 กม./ชม.", `${car.accel} วิ`],
    ["ขับเคลื่อน", car.drive],
    ["ที่นั่ง", `${car.seats}`],
    ["สิ้นเปลือง/ระยะทาง", car.fuel],
    ["ความปลอดภัย", car.safety],
    ["รับประกัน", car.warranty],
  ];
  document.getElementById("spec-grid").innerHTML = cells
    .map((c) => `<div class="cell"><p class="k">${c[0]}</p><p class="v">${c[1]}</p></div>`)
    .join("");
}

async function initModel() {
  const id = qs("id");
  try {
    car = await API.car(id || "");
  } catch (err) {
    document.getElementById("loading").textContent = err.message + " — กลับไปเลือกจากหน้าแรกได้เลย";
    return;
  }

  // ถ้ามี config เดิมของรุ่นเดียวกัน ให้จำสี/ออปชันที่เคยเลือกไว้
  const saved = Store.load("config");
  if (saved && saved.car_id === car.id) {
    colorId = car.colors.some((c) => c.id === saved.color_id) ? saved.color_id : car.colors[0].id;
    optionIds = new Set(saved.option_ids.filter((oid) => car.options.some((o) => o.id === oid)));
  } else {
    colorId = (car.colors.find((c) => c.extra === 0) || car.colors[0]).id;
  }

  document.title = `${car.name} — ASTRA Motors`;
  document.getElementById("car-body-type").textContent = car.body;
  document.getElementById("car-name").textContent = car.name;
  document.getElementById("car-tagline").textContent = car.tagline;
  document.getElementById("btn-testdrive").href = `/pages/test-drive.html?car=${car.id}`;
  document.getElementById("btn-finance").href = `/pages/finance.html?car=${car.id}`;
  document.getElementById("btn-reserve").addEventListener("click", () => {
    saveConfig();
    location.href = "/pages/reserve.html";
  });

  renderVisual();
  renderSwatches();
  renderColorInfo();
  renderOptions();
  renderPrice();
  renderPromo();
  renderSpecs();

  document.getElementById("loading").classList.add("hidden");
  document.getElementById("detail").classList.remove("hidden");
}

initModel();
