// จองทดลองขับ (journey ขั้นตอน 4): รุ่น → โชว์รูม → วัน-เวลา (คิวว่างจริง) → ยืนยัน
"use strict";

renderHeader("testdrive");
renderFooter();

let cars = [];
let showrooms = [];
let carId = null;
let showroomId = null;
let selectedTime = null;

function renderCarChips() {
  const zone = document.getElementById("car-chips");
  zone.innerHTML = cars
    .map(
      (c) => `
      <button type="button" class="chip ${c.id === carId ? "selected" : ""}" data-id="${c.id}"
              role="radio" aria-checked="${c.id === carId}">${c.name}</button>`
    )
    .join("");
  zone.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      carId = chip.dataset.id;
      renderCarChips();
    });
  });
}

function renderShowrooms() {
  const zone = document.getElementById("showroom-list");
  zone.innerHTML = showrooms
    .map(
      (s) => `
      <div class="showroom-card ${s.id === showroomId ? "selected" : ""}" data-id="${s.id}"
           role="button" tabindex="0" aria-pressed="${s.id === showroomId}">
        <h4>${s.name}</h4>
        <p>${s.address}</p>
        <p class="num">${s.hours} · โทร ${s.phone}</p>
      </div>`
    )
    .join("");
  zone.querySelectorAll(".showroom-card").forEach((cardEl) => {
    const pick = () => {
      showroomId = cardEl.dataset.id;
      renderShowrooms();
      loadSlots();
    };
    cardEl.addEventListener("click", pick);
    cardEl.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(); }
    });
  });
}

async function loadSlots() {
  const date = document.getElementById("td-date").value;
  const zone = document.getElementById("slot-chips");
  selectedTime = null;
  if (!showroomId || !date) return;

  zone.innerHTML = '<p class="muted small">กำลังเช็คคิวว่าง…</p>';
  try {
    const data = await API.slots(showroomId, date);
    zone.innerHTML = data.slots
      .map(
        (s) => `
        <button type="button" class="chip" data-time="${s.time}" ${s.available ? "" : "disabled"}
                aria-label="${s.time} ${s.available ? "ว่าง" : "ถูกจองแล้ว"}">${s.time}</button>`
      )
      .join("");
    zone.querySelectorAll(".chip:not(:disabled)").forEach((chip) => {
      chip.addEventListener("click", () => {
        selectedTime = chip.dataset.time;
        zone.querySelectorAll(".chip").forEach((c) => c.classList.remove("selected"));
        chip.classList.add("selected");
      });
    });
  } catch (err) {
    zone.innerHTML = `<p class="muted small">${err.message}</p>`;
  }
}

function setInvalid(fieldId, invalid) {
  document.getElementById(fieldId).closest(".field").classList.toggle("invalid", invalid);
}

async function submit(e) {
  e.preventDefault();
  const name = document.getElementById("td-name").value.trim();
  const phone = document.getElementById("td-phone").value.trim();
  const date = document.getElementById("td-date").value;

  // validate ฝั่งหน้าเว็บก่อน แล้ว backend จะ validate ซ้ำอีกชั้น
  setInvalid("td-name", name.length < 2);
  setInvalid("td-phone", phone.replace(/\D/g, "").length < 9);
  if (!carId) return toast("กรุณาเลือกรุ่นรถ", "error");
  if (!showroomId) return toast("กรุณาเลือกโชว์รูม", "error");
  if (!date) return toast("กรุณาเลือกวันที่นัด", "error");
  if (!selectedTime) return toast("กรุณาเลือกช่วงเวลา", "error");
  if (name.length < 2 || phone.replace(/\D/g, "").length < 9) return;
  if (!document.getElementById("td-license").checked)
    return toast("ผู้ทดลองขับต้องมีใบขับขี่", "error");

  const btn = document.getElementById("td-submit");
  btn.disabled = true;
  btn.textContent = "กำลังยืนยัน…";
  try {
    const record = await API.createTestdrive({
      car_id: carId,
      showroom_id: showroomId,
      date,
      time: selectedTime,
      name,
      phone,
      has_license: true,
      contact_message_only: document.getElementById("td-msg-only").checked,
    });
    Store.save("testdrive", record);

    document.getElementById("td-form").classList.add("hidden");
    const panel = document.getElementById("td-confirm");
    panel.classList.remove("hidden");
    panel.innerHTML = `
      <div class="icon-big">${ICONS.check}</div>
      <h2>จองทดลองขับสำเร็จ</h2>
      <p class="code">${record.code}</p>
      <p><strong>${record.car.name}</strong> ที่ ${record.showroom.name}</p>
      <p class="muted">${thaiDate(record.date)} เวลา ${record.time} น.</p>
      <p class="muted small mt-2">โชว์รูมได้รับแจ้งอัตโนมัติแล้ว และระบบจะแจ้งเตือนคุณก่อนถึงวันนัด<br>
      กรุณานำใบขับขี่ตัวจริงมาในวันทดลองขับ</p>
      <div class="cta-row mt-3" style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap">
        <a class="btn btn-primary" href="/pages/status.html">ดูการจองของฉัน</a>
        <a class="btn btn-ghost" href="/">กลับหน้าแรก</a>
      </div>`;
    panel.scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    toast(err.message, "error");
    if (err.message.includes("ถูกจอง")) loadSlots(); // slot ชนกัน — โหลดคิวใหม่
  } finally {
    btn.disabled = false;
    btn.textContent = "ยืนยันการจองทดลองขับ";
  }
}

async function initTestDrive() {
  try {
    [cars, showrooms] = await Promise.all([API.cars(), API.showrooms()]);
  } catch (err) {
    return toast(err.message, "error");
  }

  carId = qs("car") || (Store.load("config") || {}).car_id || cars[0].id;
  if (!cars.some((c) => c.id === carId)) carId = cars[0].id;

  // เปิดให้เลือกได้ตั้งแต่พรุ่งนี้เป็นต้นไป (บล็อกวันในอดีต)
  const dateInput = document.getElementById("td-date");
  const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000);
  dateInput.min = tomorrow.toISOString().slice(0, 10);
  dateInput.addEventListener("change", loadSlots);

  renderCarChips();
  renderShowrooms();
  document.getElementById("td-form").addEventListener("submit", submit);
}

initTestDrive();
