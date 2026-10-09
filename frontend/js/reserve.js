// จองรถออนไลน์ (journey ขั้นตอน 5): สรุปสเปค → ชำระเงินจอง (จำลอง) → ใบจองอิเล็กทรอนิกส์
// ต้องล็อกอินก่อน — ใบจองผูกกับบัญชี ดู/ยกเลิกได้เฉพาะเจ้าของ และได้คะแนนสะสม 2,000 คะแนน
//
// ลำดับที่หน้านี้เดิน (ตรงกับของจริง): POST /api/payments สร้างรายการรอจ่าย → แสดง QR/แผงบัตร
// → เงินเข้า → ใบจองออก ใบจองจึงไม่เกิดถ้าลูกค้าไม่จ่าย (เส้นทาง POST /api/reservations เดิม
// ที่ออกใบจองทันทีถูกเก็บไว้เป็น legacy สำหรับเทสต์/เดโมเร็วเท่านั้น)
"use strict";

requireLogin("/pages/reserve.html");
renderHeader("home");
renderFooter();

let car = null;
let config = null;
let payMethod = "promptpay";
let payment = null;        // รายการชำระเงินที่กำลังรออยู่
let pollTimer = null;      // รอบถามสถานะจากเซิร์ฟเวอร์
let tickTimer = null;      // นาฬิกานับถอยหลังบนหน้าจอ

const POLL_MS = 3000;      // ถามสถานะทุก 3 วินาที

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

// setFieldInvalid (ui.js) ผูก aria-invalid + aria-describedby ให้ด้วย ไม่ให้เหลือแค่สีแดง
const setInvalid = setFieldInvalid;

/* ---------- แผงชำระเงินจอง ---------- */

function stopTimers() {
  clearInterval(pollTimer);
  clearInterval(tickTimer);
  pollTimer = null;
  tickTimer = null;
}

function setPayStatus(text, type = "muted") {
  const el = document.getElementById("pay-status");
  el.className = type === "bad" ? "mt-2 badge badge-bad" : type === "ok" ? "mt-2 badge badge-ok" : "mt-2 muted";
  el.textContent = text;   // textContent = escape ให้เองอยู่แล้ว
}

function paintCountdown(seconds) {
  const left = Math.max(0, seconds);
  const mm = String(Math.floor(left / 60)).padStart(2, "0");
  document.getElementById("pay-countdown").textContent = `${mm}:${String(left % 60).padStart(2, "0")}`;
}

// หมดเวลา/ยกเลิก → ซ่อนปุ่มจ่าย เหลือแต่ปุ่มเริ่มใหม่ (กดด้วยคีย์บอร์ดได้ เพราะเป็น <button> จริง)
function showRestart(message) {
  stopTimers();
  setPayStatus(message, "bad");
  document.getElementById("pay-simulate").classList.add("hidden");
  document.getElementById("pay-cancel").classList.add("hidden");
  const restart = document.getElementById("pay-restart");
  restart.classList.remove("hidden");
  restart.focus();
}

function renderPayPanel() {
  const panel = document.getElementById("pay-panel");
  document.getElementById("reserve-layout").classList.add("hidden");
  panel.classList.remove("hidden");

  document.getElementById("pay-head").innerHTML =
    `ชำระเงินจอง <span class="num" style="color:var(--accent-strong)">${baht(payment.amount)}</span>`;
  document.getElementById("pay-note").textContent = payment.simulation_note || "";

  if (payment.method === "promptpay") {
    document.getElementById("pay-qr-zone").classList.remove("hidden");
    // qr_svg มาจากเซิร์ฟเวอร์ (สร้างจาก payload ที่ระบบเองคำนวณ) ไม่ใช่ข้อความที่ผู้ใช้พิมพ์
    // จึงฝังเป็น HTML ได้ ส่วนค่าที่ผู้ใช้/ข้อมูลร้านส่งมาด้านล่างยัง esc() ตามปกติ
    document.getElementById("pay-qr").innerHTML = payment.qr_svg || "";
    const pp = payment.promptpay || {};
    document.getElementById("pay-payee").textContent =
      `ผู้รับเงิน (สมมติ): ${pp.name || "-"} · ${pp.phone || "-"}`;
  } else {
    document.getElementById("pay-card-zone").classList.remove("hidden");
    document.getElementById("pay-card-mask").textContent =
      payment.card_last4 ? `•••• •••• •••• ${payment.card_last4}` : "•••• •••• •••• ••••";
  }

  setPayStatus("รอรับเงิน — ระบบจะตรวจสอบสถานะให้อัตโนมัติ");
  paintCountdown(payment.expires_in);
  panel.scrollIntoView({ behavior: "smooth" });

  tickTimer = setInterval(() => {
    payment.expires_in -= 1;
    paintCountdown(payment.expires_in);
    if (payment.expires_in <= 0) refreshPayment();   // ให้เซิร์ฟเวอร์เป็นคนชี้ขาดว่าหมดอายุจริง
  }, 1000);
  // ในระบบจริงเซิร์ฟเวอร์รู้ผลจาก webhook ของ payment gateway แล้ว push มาให้
  // เดโมนี้ยังไม่มี gateway จริง จึงให้เบราว์เซอร์ถามสถานะเป็นรอบ ๆ แทน
  pollTimer = setInterval(refreshPayment, POLL_MS);
}

async function refreshPayment() {
  if (!payment) return;
  let fresh;
  try {
    fresh = await API.payment(payment.id);
  } catch {
    return;   // เน็ตสะดุดรอบเดียวไม่ต้องตกใจ รอบถัดไปถามใหม่
  }
  payment = { ...payment, ...fresh };
  paintCountdown(payment.expires_in);

  if (payment.status === "paid") return finishPayment();
  if (payment.status === "expired")
    return showRestart("หมดเวลาชำระเงินแล้ว รายการนี้ถูกยกเลิกอัตโนมัติ กรุณาเริ่มรายการใหม่");
  if (payment.status === "failed")
    return showRestart("รายการชำระเงินถูกยกเลิก กรุณาเริ่มรายการใหม่");
}

async function finishPayment() {
  stopTimers();
  setPayStatus("ได้รับเงินจองแล้ว กำลังออกใบจอง…", "ok");
  try {
    const record = await API.reservation(payment.reservation_code);
    document.getElementById("pay-panel").classList.add("hidden");
    renderConfirm(record);
  } catch (err) {
    toast(err.message, "error");
  }
}

async function simulatePaid() {
  const btn = document.getElementById("pay-simulate");
  btn.disabled = true;
  setPayStatus("กำลังยืนยันกับธนาคาร (จำลอง)…");
  try {
    payment = { ...payment, ...(await API.confirmPayment(payment.id)) };
    await finishPayment();
  } catch (err) {
    btn.disabled = false;
    toast(err.message, "error");
    refreshPayment();   // 400 เพราะหมดอายุ -> ให้แผงเปลี่ยนเป็นปุ่มเริ่มใหม่
  }
}

async function cancelPayment() {
  try {
    await API.cancelPayment(payment.id);
  } catch (err) {
    toast(err.message, "error");
  }
  showRestart("ยกเลิกการชำระเงินแล้ว ยังไม่มีการออกใบจอง");
}

function restart() {
  stopTimers();
  payment = null;
  document.getElementById("pay-panel").classList.add("hidden");
  document.getElementById("pay-qr-zone").classList.add("hidden");
  document.getElementById("pay-card-zone").classList.add("hidden");
  document.getElementById("pay-simulate").classList.remove("hidden");
  document.getElementById("pay-simulate").disabled = false;
  document.getElementById("pay-cancel").classList.remove("hidden");
  document.getElementById("pay-restart").classList.add("hidden");
  document.getElementById("reserve-layout").classList.remove("hidden");
  document.getElementById("rs-submit").focus();
}

/* ---------- ใบจองอิเล็กทรอนิกส์ (ใช้ร่วมกันทุกเส้นทางที่ออกใบจองสำเร็จ) ---------- */

function renderConfirm(record) {
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
      <p class="muted small mt-2">สำเนาใบจองถูกส่งไปที่อีเมลของคุณแล้ว (จำลอง) · ได้รับ 2,000 คะแนนสะสม<br>
      ขั้นตอนถัดไป: ยื่นขอสินเชื่อ หรือติดต่อรับรถด้วยเงินสดที่โชว์รูม</p>
      <div class="cta-row mt-3" style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap">
        <a class="btn btn-primary" href="/pages/loan.html">ยื่นขอสินเชื่อต่อเลย</a>
        <a class="btn btn-ghost" href="/pages/status.html?code=${record.code}">ดูสถานะการจอง</a>
      </div>`;
  panel.scrollIntoView({ behavior: "smooth" });
}

/* ---------- เริ่มรายการชำระเงิน (กดจากฟอร์ม) ---------- */

async function submit(e) {
  e.preventDefault();
  const name = document.getElementById("rs-name").value.trim();
  const phone = document.getElementById("rs-phone").value.trim();
  const email = document.getElementById("rs-email").value.trim();
  const last4 = document.getElementById("rs-last4").value.trim();

  setInvalid("rs-name", name.length < 2);
  setInvalid("rs-phone", phone.replace(/\D/g, "").length < 9);
  setInvalid("rs-email", !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email));
  setInvalid("rs-last4", payMethod === "card" && last4 !== "" && !/^\d{4}$/.test(last4));
  if (document.querySelector(".field.invalid")) return;
  if (!document.getElementById("rs-agree").checked)
    return toast("กรุณายอมรับเงื่อนไขการจองก่อนชำระเงิน", "error");

  const btn = document.getElementById("rs-submit");
  btn.disabled = true;
  btn.textContent = "กำลังสร้างรายการชำระเงิน…";
  try {
    payment = await API.createPayment({
      car_id: config.car_id,
      color_id: config.color_id,
      option_ids: config.option_ids,
      name,
      phone,
      email,
      method: payMethod,
      contact_message_only: document.getElementById("rs-msg-only").checked,
      // ส่งแค่ 4 ตัวท้ายเพื่อแสดงผล — ไม่มีช่องกรอกเลขบัตรเต็มในหน้านี้โดยเจตนา
      card_last4: payMethod === "card" && last4 ? last4 : null,
    });
    renderPayPanel();
  } catch (err) {
    toast(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "ไปหน้าชำระเงินจอง";
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
  prefillFromUser({ "rs-name": "full_name", "rs-phone": "phone", "rs-email": "email" });
  document.getElementById("reserve-layout").classList.remove("hidden");
  renderSummary();

  bindRadioGroup(document.getElementById("pay-chips"));
  document.querySelectorAll("#pay-chips .chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      payMethod = chip.dataset.pay;
      document.querySelectorAll("#pay-chips .chip").forEach((c) => {
        c.classList.toggle("selected", c === chip);
        c.setAttribute("aria-checked", c === chip ? "true" : "false");
      });
      // ช่อง 4 ตัวท้ายมีความหมายเฉพาะช่องทางบัตร
      document.getElementById("rs-card-field").classList.toggle("hidden", payMethod !== "card");
      setInvalid("rs-last4", false);
    });
  });
  document.getElementById("rs-form").addEventListener("submit", submit);
  document.getElementById("pay-simulate").addEventListener("click", simulatePaid);
  document.getElementById("pay-cancel").addEventListener("click", cancelPayment);
  document.getElementById("pay-restart").addEventListener("click", restart);
}

initReserve();
