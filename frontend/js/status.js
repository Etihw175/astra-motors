// ติดตามสถานะ (journey ขั้นตอน 5, 7, 8): stepper การจอง + ผลสินเชื่อเรียลไทม์ + นัดรับรถ + ยกเลิก
"use strict";

renderHeader("status");
renderFooter();

let reservation = null;
let loan = null;
let pollTimer = null;

const STATUS_BADGE = {
  reserved: '<span class="badge badge-accent">จองแล้ว — ล็อกราคาอยู่</span>',
  delivery_scheduled: '<span class="badge badge-ok">นัดรับรถแล้ว</span>',
  cancelled: '<span class="badge badge-bad">ยกเลิกแล้ว</span>',
};

function render() {
  const zone = document.getElementById("rsv-zone");
  if (!reservation) {
    zone.innerHTML =
      '<div class="card text-center muted">กรอกรหัสใบจองด้านบน หรือเริ่มจาก' +
      ' <a href="/pages/compare.html">เลือกรุ่นรถ</a> แล้วจองออนไลน์</div>';
    return;
  }

  const r = reservation;
  const cancelled = r.status === "cancelled";

  // ----- การ์ดสรุปใบจอง -----
  let html = `
    <div class="card">
      <div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:center">
        <div>
          <p class="eyebrow num">${r.code}</p>
          <h3>${r.car.name} <span class="muted" style="font-weight:400">สี${r.color.name}</span></h3>
        </div>
        ${STATUS_BADGE[r.status] || ""}
      </div>
      <div class="price-lines mt-2">
        <div class="price-line"><span class="lbl">ราคารวม (ล็อกถึง ${thaiDate(r.price_locked_until)})</span>
          <span class="val">${baht(r.total_price)}</span></div>
        <div class="price-line"><span class="lbl">เงินจองที่ชำระแล้ว</span><span class="val">${baht(r.booking_fee)}</span></div>
        ${r.promotion ? `<div class="price-line"><span class="lbl">โปรโมชั่นที่ล็อกไว้</span><span class="val" style="font-family:var(--font-body);font-size:13.5px">${r.promotion.title}</span></div>` : ""}
      </div>
      ${
        cancelled
          ? `<div class="promo expired mt-2"><div>
               <p class="t">ใบจองถูกยกเลิกแล้ว</p>
               <p class="exp">เงินคืน ${baht(r.refund.amount)} — ${r.refund.note}</p>
             </div></div>`
          : `<div class="mt-3"><button class="btn btn-danger" id="btn-cancel">ยกเลิกใบจอง</button></div>`
      }
    </div>`;

  // ----- Stepper -----
  if (!cancelled) {
    const hasLoan = Boolean(loan);
    const approved = hasLoan && loan.status === "approved";
    const rejected = hasLoan && loan.status === "rejected";
    const reviewing = hasLoan && loan.status === "reviewing";
    const delivered = r.status === "delivery_scheduled";

    html += `<div class="card"><div class="stepper">

      <div class="step done">
        <div class="dot" aria-hidden="true">1</div>
        <div class="content">
          <h4>จองสำเร็จ — ออกใบจองอิเล็กทรอนิกส์</h4>
          <p class="desc">วันที่จอง ${new Date(r.created_at).toLocaleDateString("th-TH", { day: "numeric", month: "short", year: "numeric" })} · ราคาถูกล็อกถึง ${thaiDate(r.price_locked_until)}</p>
        </div>
      </div>

      <div class="step ${hasLoan ? "done" : "active"}">
        <div class="dot" aria-hidden="true">2</div>
        <div class="content">
          <h4>ยื่นขอสินเชื่อ</h4>
          ${
            hasLoan
              ? `<p class="desc">${loan.plan.name} · ดาวน์ ${baht(loan.down_payment)} (${loan.down_pct}%) · ${loan.term_months} งวด · ค่างวด ~${baht(loan.monthly_payment)}/เดือน</p>`
              : `<p class="desc">ยังไม่ได้ยื่นสินเชื่อ — ยื่นออนไลน์ได้เลย หรือติดต่อชำระเงินสดที่โชว์รูม</p>
                 <p class="mt-1"><a class="btn btn-primary" href="/pages/loan.html">ยื่นขอสินเชื่อ</a></p>`
          }
        </div>
      </div>

      <div class="step ${approved ? "done" : rejected ? "failed" : reviewing ? "active" : ""}">
        <div class="dot" aria-hidden="true">3</div>
        <div class="content">
          <h4>ผลการพิจารณาสินเชื่อ</h4>
          ${reviewing ? '<p class="desc">สถาบันการเงินกำลังพิจารณา… หน้านี้จะอัปเดตผลให้อัตโนมัติ</p>' : ""}
          ${approved ? `<p class="desc" style="color:var(--ok)">อนุมัติแล้ว — ${loan.result.message}</p>` : ""}
          ${
            rejected
              ? `<p class="desc" style="color:var(--bad)">ไม่ผ่านการอนุมัติ: ${loan.result.message}
                 (ภาระผ่อน ${loan.result.ratio_pct}% ของรายได้ เกินเกณฑ์ ${loan.result.max_ratio_pct}%)</p>
                 <div class="mt-1">
                   <p class="small" style="font-weight:600">ทางเลือกที่แนะนำ:</p>
                   <ul class="small muted" style="padding-left:20px;margin-top:4px">
                     ${loan.result.alternatives.map((a) => `<li>${a}</li>`).join("")}
                   </ul>
                   <div class="mt-2" style="display:flex;gap:10px;flex-wrap:wrap">
                     <a class="btn btn-ghost" href="/pages/finance.html">ปรับแผนไฟแนนซ์</a>
                     <a class="btn btn-primary" href="/pages/loan.html">ยื่นคำขอใหม่</a>
                   </div>
                 </div>`
              : ""
          }
        </div>
      </div>

      <div class="step ${delivered ? "done" : approved ? "active" : ""}">
        <div class="dot" aria-hidden="true">4</div>
        <div class="content">
          <h4>นัดรับรถ</h4>
          ${
            delivered
              ? `<p class="desc">นัดรับรถวันที่ <strong>${thaiDate(r.delivery_date)}</strong> ที่โชว์รูมที่ระบุในอีเมลยืนยัน</p>
                 <p class="small mt-1" style="font-weight:600">เอกสารที่ต้องเตรียมในวันรับรถ:</p>
                 <ul class="small muted" style="padding-left:20px;margin-top:4px">
                   ${(r.delivery_documents || []).map((d) => `<li>${d}</li>`).join("")}
                 </ul>`
              : approved
                ? `<div class="field mt-1" style="max-width:280px;margin-bottom:0">
                     <label for="dv-date">เลือกวันรับรถ</label>
                     <input type="date" id="dv-date">
                   </div>
                   <p class="mt-1"><button class="btn btn-primary" id="btn-delivery">ยืนยันวันนัดรับรถ</button></p>`
                : '<p class="desc">รอผลอนุมัติสินเชื่อก่อน จึงจะนัดวันรับรถได้</p>'
          }
        </div>
      </div>

    </div></div>`;
  }

  zone.innerHTML = html;

  // ----- ผูก event หลัง render -----
  const btnCancel = document.getElementById("btn-cancel");
  if (btnCancel) btnCancel.addEventListener("click", () => toggleModal(true));

  const btnDelivery = document.getElementById("btn-delivery");
  if (btnDelivery) {
    const dv = document.getElementById("dv-date");
    dv.min = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    btnDelivery.addEventListener("click", async () => {
      if (!dv.value) return toast("กรุณาเลือกวันรับรถ", "error");
      try {
        reservation = await API.scheduleDelivery(reservation.code, dv.value);
        toast("นัดรับรถเรียบร้อย ระบบจะแจ้งเตือนก่อนถึงวันนัด", "ok");
        render();
      } catch (err) {
        toast(err.message, "error");
      }
    });
  }
}

// แสดงนัดทดลองขับ (ถ้ามี) — journey ขั้นตอน 5
function renderTestdrive() {
  const td = Store.load("testdrive");
  if (!td) return;
  document.getElementById("td-zone").innerHTML = `
    <div class="card">
      <p class="eyebrow num">${td.code}</p>
      <h3 style="font-size:18px">นัดทดลองขับ ${td.car.name}</h3>
      <p class="muted small">${td.showroom.name} · ${thaiDate(td.date)} เวลา ${td.time} น. —
      นำใบขับขี่ตัวจริงมาแสดงในวันนัด</p>
    </div>`;
}

/* ---------- โหลดข้อมูล + poll ผลสินเชื่อ ---------- */

async function refreshLoan() {
  if (!reservation || !reservation.loan_id) return;
  try {
    loan = await API.loan(reservation.loan_id);
    // poll ต่อเฉพาะตอนกำลังพิจารณา — ได้ผลแล้วหยุด
    if (loan.status === "reviewing" && !pollTimer) {
      pollTimer = setInterval(async () => {
        loan = await API.loan(reservation.loan_id).catch(() => loan);
        if (loan.status !== "reviewing") {
          clearInterval(pollTimer);
          pollTimer = null;
          toast(
            loan.status === "approved" ? "สินเชื่อได้รับการอนุมัติแล้ว" : "ผลสินเชื่อ: ไม่ผ่านการอนุมัติ",
            loan.status === "approved" ? "ok" : "error"
          );
        }
        render();
      }, 4000);
    }
  } catch {
    loan = null;
  }
}

async function loadReservation(code) {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  reservation = null;
  loan = null;
  try {
    reservation = await API.reservation(code);
    Store.save("reservation_code", code);
    await refreshLoan();
  } catch (err) {
    toast(err.message, "error");
  }
  render();
}

/* ---------- Modal ยกเลิก ---------- */

function toggleModal(open) {
  document.getElementById("cancel-modal").classList.toggle("open", open);
}

document.getElementById("cancel-no").addEventListener("click", () => toggleModal(false));
document.getElementById("cancel-yes").addEventListener("click", async () => {
  toggleModal(false);
  try {
    reservation = await API.cancelReservation(reservation.code);
    toast("ยกเลิกใบจองแล้ว", "ok");
    render();
  } catch (err) {
    toast(err.message, "error");
  }
});

/* ---------- เริ่มต้น ---------- */

document.getElementById("st-load").addEventListener("click", () => {
  const code = document.getElementById("st-code").value.trim();
  if (code) loadReservation(code);
});
document.getElementById("st-code").addEventListener("keydown", (e) => {
  if (e.key === "Enter") document.getElementById("st-load").click();
});

renderTestdrive();
const savedCode = qs("code") || Store.load("reservation_code");
if (savedCode) {
  document.getElementById("st-code").value = savedCode;
  loadReservation(savedCode);
} else {
  render();
}
