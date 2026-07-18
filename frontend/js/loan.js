// ยื่นขอสินเชื่อ (journey ขั้นตอน 7): เลือกแผน → กรอกข้อมูล/แนบเอกสาร → ส่งเรื่อง
"use strict";

renderHeader("home");
renderFooter();

let plans = [];
let reservation = null;

function currentPlan() {
  return plans.find((p) => p.id === document.getElementById("ln-plan").value);
}

function renderTermOptions() {
  const plan = currentPlan();
  document.getElementById("ln-term").innerHTML = plan.terms
    .map((t) => `<option value="${t}" ${t === 60 ? "selected" : ""}>${t} งวด (${t / 12} ปี)</option>`)
    .join("");
  document.getElementById("plan-hint").textContent =
    `ดอกเบี้ยคงที่ ${plan.flat_rate}% ต่อปี · ดาวน์ขั้นต่ำ ${plan.min_down_pct}% · ${plan.note}`;
}

function renderPreview() {
  const zone = document.getElementById("ln-preview");
  if (!reservation) return (zone.innerHTML = "");
  const plan = currentPlan();
  const down = Number(document.getElementById("ln-down").value) || 0;
  const term = Number(document.getElementById("ln-term").value) || plan.terms[0];
  const principal = Math.max(reservation.total_price - down, 0);
  const monthly = monthlyPayment(principal, plan.flat_rate, term);
  zone.innerHTML = `
    <div class="price-line mt-2"><span class="lbl">ราคารถตามใบจอง</span><span class="val">${baht(reservation.total_price)}</span></div>
    <div class="price-line"><span class="lbl">ยอดจัดไฟแนนซ์</span><span class="val">${baht(principal)}</span></div>
    <div class="price-line total"><span class="lbl">ค่างวดโดยประมาณ</span><span class="val">${baht(monthly)}/เดือน</span></div>`;
}

async function loadReservation() {
  const code = document.getElementById("ln-code").value.trim();
  const summaryZone = document.getElementById("rsv-summary");
  reservation = null;
  if (!code) return;
  try {
    reservation = await API.reservation(code);
    document.getElementById("ln-code").closest(".field").classList.remove("invalid");
    summaryZone.innerHTML =
      `ใบจอง: <strong>${reservation.car.name}</strong> สี${reservation.color.name} · ` +
      `ราคารวม <span class="num">${baht(reservation.total_price)}</span> · ` +
      `ล็อกราคาถึง ${thaiDate(reservation.price_locked_until)}`;
    // ตั้งต้นเงินดาวน์ 25% ของราคารถ
    const downInput = document.getElementById("ln-down");
    if (!downInput.value) downInput.value = Math.round(reservation.total_price * 0.25);
    document.getElementById("down-hint").textContent =
      `แนะนำ 25% = ${baht(Math.round(reservation.total_price * 0.25))}`;
    renderPreview();
  } catch (err) {
    summaryZone.textContent = "";
    document.getElementById("ln-code").closest(".field").classList.add("invalid");
  }
}

function setInvalid(id, invalid) {
  document.getElementById(id).closest(".field").classList.toggle("invalid", invalid);
}

async function submit(e) {
  e.preventDefault();
  if (!reservation) {
    setInvalid("ln-code", true);
    return toast("กรุณากรอกรหัสใบจองที่ถูกต้องก่อน", "error");
  }
  const name = document.getElementById("ln-name").value.trim();
  const phone = document.getElementById("ln-phone").value.trim();
  const income = Number(document.getElementById("ln-income").value);
  const down = Number(document.getElementById("ln-down").value);

  setInvalid("ln-name", name.length < 2);
  setInvalid("ln-phone", phone.replace(/\D/g, "").length < 9);
  setInvalid("ln-income", !(income > 0));
  setInvalid("ln-down", !(down >= 0 && down < reservation.total_price));
  if (document.querySelector(".field.invalid")) return;
  if (!document.getElementById("ln-consent").checked)
    return toast("กรุณายินยอมการใช้ข้อมูล (PDPA) ก่อนส่งคำขอ", "error");

  // เก็บเฉพาะ "ชื่อไฟล์" เอกสารที่เลือก (การอัปโหลดเป็นการจำลอง)
  const documents = ["doc-id", "doc-income"]
    .map((id) => document.getElementById(id).files[0])
    .filter(Boolean)
    .map((f) => f.name);

  const btn = document.getElementById("ln-submit");
  btn.disabled = true;
  btn.textContent = "กำลังส่งคำขอ…";
  try {
    const record = await API.createLoan({
      reservation_code: reservation.code,
      plan_id: document.getElementById("ln-plan").value,
      down_payment: down,
      term_months: Number(document.getElementById("ln-term").value),
      name,
      phone,
      occupation: document.getElementById("ln-occupation").value,
      monthly_income: income,
      documents,
      consent_pdpa: true,
    });
    Store.save("loan_id", record.id);
    toast("ส่งคำขอสินเชื่อแล้ว กำลังพาไปหน้าติดตามผล…", "ok");
    setTimeout(() => (location.href = "/pages/status.html"), 900);
  } catch (err) {
    toast(err.message, "error");
    btn.disabled = false;
    btn.textContent = "ส่งคำขอสินเชื่อ";
  }
}

async function initLoan() {
  try {
    plans = await API.financePlans();
  } catch (err) {
    return toast(err.message, "error");
  }

  document.getElementById("ln-plan").innerHTML = plans
    .map((p) => `<option value="${p.id}">${p.name} — ${p.flat_rate}%${p.promo ? " (โปรฯ)" : ""}</option>`)
    .join("");

  renderTermOptions();

  document.getElementById("ln-plan").addEventListener("change", () => {
    renderTermOptions();
    renderPreview();
  });
  document.getElementById("ln-term").addEventListener("change", renderPreview);
  document.getElementById("ln-down").addEventListener("input", renderPreview);
  document.getElementById("ln-code").addEventListener("change", loadReservation);
  document.getElementById("ln-form").addEventListener("submit", submit);

  // เติมรหัสใบจองล่าสุดของผู้ใช้ให้อัตโนมัติ
  const savedCode = Store.load("reservation_code");
  if (savedCode) {
    document.getElementById("ln-code").value = savedCode;
    loadReservation();
  }
}

initLoan();
