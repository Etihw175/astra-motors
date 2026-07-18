// จองรถออนไลน์ (journey ขั้นตอน 6): สรุปสเปค → ชำระเงินจอง (จำลอง) → ใบจองอิเล็กทรอนิกส์
"use strict";

renderHeader("home");
renderFooter();

let car = null;
let config = null;
let payMethod = "promptpay";

function selectedColor() {
  return car.colors.find((c) => c.id === config.color_id) || car.colors[0];
}

function renderSummary() {
  const color = selectedColor();
  const opts = car.options.filter((o) => config.option_ids.includes(o.id));
  const total = car.price + color.extra + opts.reduce((s, o) => s + o.price, 0);
  config.total = total;

  document.getElementById("car-visual").innerHTML =
    carVisual3D(car.id, color.hex, { height: 260, controls: true });
  initCarVisuals();
  document.getElementById("sum-name").textContent = car.name;
  document.getElementById("sum-color").textContent =
    `สี${color.name}` + (opts.length ? ` + ออปชัน ${opts.length} รายการ` : "");
  // Edge case: สีที่เลือกต้องรอผลิต — เตือนก่อนวางเงินจอง
  document.getElementById("sum-stock").innerHTML =
    stockBadge(color.stock) +
    (color.stock !== "in_stock"
      ? '<p class="muted small mt-1">สีนี้ต้องรอผลิต ระยะเวลารอโดยประมาณจะระบุในใบจอง และแจ้งอัปเดตทุกสัปดาห์</p>'
      : "");

  document.getElementById("sum-lines").innerHTML = [
    `<div class="price-line"><span class="lbl">ราคาเริ่มต้น</span><span class="val">${baht(car.price)}</span></div>`,
    color.extra > 0
      ? `<div class="price-line"><span class="lbl">สี ${color.name}</span><span class="val">+${baht(color.extra)}</span></div>`
      : "",
    ...opts.map(
      (o) => `<div class="price-line"><span class="lbl">${o.name}</span><span class="val">+${baht(o.price)}</span></div>`
    ),
    `<div class="price-line total"><span class="lbl">ราคารวม</span><span class="val">${baht(total)}</span></div>`,
    `<div class="price-line"><span class="lbl">เงินจองวันนี้</span><span class="val">${baht(200000)}</span></div>`,
  ].join("");

  if (car.promotion) {
    const expired = new Date(`${car.promotion.expires}T23:59:59`) < new Date();
    document.getElementById("promo-zone").innerHTML = `
      <div class="promo ${expired ? "expired" : ""}">
        <div>
          <p class="t">${car.promotion.title}</p>
          <p class="exp">${
            expired
              ? "หมดอายุแล้ว — ใบจองนี้จะไม่รวมโปรโมชั่นดังกล่าว"
              : "โปรฯ นี้จะถูกล็อกในใบจองของคุณ (ถึง " + thaiDate(car.promotion.expires) + ")"
          }</p>
        </div>
      </div>`;
  }
}

function setInvalid(id, invalid) {
  document.getElementById(id).closest(".field").classList.toggle("invalid", invalid);
}

async function submit(e) {
  e.preventDefault();
  const name = document.getElementById("rs-name").value.trim();
  const phone = document.getElementById("rs-phone").value.trim();
  const email = document.getElementById("rs-email").value.trim();

  setInvalid("rs-name", name.length < 2);
  setInvalid("rs-phone", phone.replace(/\D/g, "").length < 9);
  setInvalid("rs-email", !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email));
  if (document.querySelector(".field.invalid")) return;
  if (!document.getElementById("rs-agree").checked)
    return toast("กรุณายอมรับเงื่อนไขการจองก่อนชำระเงิน", "error");

  const btn = document.getElementById("rs-submit");
  btn.disabled = true;
  btn.textContent = "กำลังออกใบจอง…";
  try {
    const record = await API.createReservation({
      car_id: config.car_id,
      color_id: config.color_id,
      option_ids: config.option_ids,
      name,
      phone,
      email,
      payment_method: payMethod,
      contact_message_only: document.getElementById("rs-msg-only").checked,
    });
    Store.save("reservation_code", record.code);

    document.getElementById("reserve-layout").classList.add("hidden");
    const panel = document.getElementById("rs-confirm");
    panel.classList.remove("hidden");
    panel.innerHTML = `
      <div class="icon-big">${ICONS.check}</div>
      <h2>ออกใบจองอิเล็กทรอนิกส์แล้ว</h2>
      <p class="code">${record.code}</p>
      <p><strong>${record.car.name}</strong> สี${record.color.name} — ราคารวม <span class="num">${baht(record.total_price)}</span></p>
      <p class="muted mt-1">ราคาและโปรโมชั่นถูกล็อกถึงวันที่ <strong>${thaiDate(record.price_locked_until)}</strong></p>
      ${
        record.promotion
          ? `<p class="badge badge-accent mt-1">ล็อกโปรฯ: ${record.promotion.title}</p>`
          : record.promotion_expired
            ? '<p class="badge badge-warn mt-1">โปรโมชั่นหมดอายุก่อนวันจอง จึงไม่ถูกรวมในใบจองนี้</p>'
            : ""
      }
      <p class="muted small mt-2">สำเนาใบจองถูกส่งไปที่อีเมลของคุณแล้ว (จำลอง)<br>
      ขั้นตอนถัดไป: ยื่นขอสินเชื่อ หรือติดต่อรับรถด้วยเงินสดที่โชว์รูม</p>
      <div class="cta-row mt-3" style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap">
        <a class="btn btn-primary" href="/pages/loan.html">ยื่นขอสินเชื่อต่อเลย</a>
        <a class="btn btn-ghost" href="/pages/status.html">ดูสถานะการจอง</a>
      </div>`;
    panel.scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    toast(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "ชำระเงินจองและออกใบจอง";
  }
}

async function initReserve() {
  config = Store.load("config");
  if (!config) {
    document.getElementById("no-config").classList.remove("hidden");
    return;
  }
  try {
    car = await API.car(config.car_id);
  } catch (err) {
    document.getElementById("no-config").classList.remove("hidden");
    return toast(err.message, "error");
  }

  document.getElementById("edit-link").href = `/pages/model.html?id=${car.id}`;
  document.getElementById("reserve-layout").classList.remove("hidden");
  renderSummary();

  document.querySelectorAll("#pay-chips .chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      payMethod = chip.dataset.pay;
      document.querySelectorAll("#pay-chips .chip").forEach((c) => {
        c.classList.toggle("selected", c === chip);
        c.setAttribute("aria-checked", c === chip ? "true" : "false");
      });
    });
  });
  document.getElementById("rs-form").addEventListener("submit", submit);
}

initReserve();
