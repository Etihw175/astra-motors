// ติดตามสถานะ (journey ขั้นตอน 6): รวมการจองทั้งหมดของบัญชี (GET /api/me/bookings)
// + stepper ใบจอง + ผลสินเชื่อเรียลไทม์ + นัดรับรถ + ยกเลิก + นัดทดลองขับ/เข้าศูนย์
"use strict";

renderHeader("status");
renderFooter();

let reservation = null;
let loan = null;
let pollTimer = null;
let mine = null;

const TD_BADGE = {
  confirmed: '<span class="badge badge-ok">ยืนยันแล้ว</span>',
  cancelled: '<span class="badge badge-bad">ยกเลิกแล้ว</span>',
};

const STATUS_BADGE = {
  reserved: '<span class="badge badge-accent">จองแล้ว — ล็อกราคาอยู่</span>',
  delivery_scheduled: '<span class="badge badge-ok">นัดรับรถแล้ว</span>',
  cancelled: '<span class="badge badge-bad">ยกเลิกแล้ว</span>',
};

function render() {
  const zone = document.getElementById("rsv-zone");
  if (!reservation) {
    zone.innerHTML = "";
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

      <div class="step done rise">
        <div class="dot" aria-hidden="true">${ICONS.checkSmall}</div>
        <div class="content">
          <h4>จองสำเร็จ — ออกใบจองอิเล็กทรอนิกส์</h4>
          <p class="desc">วันที่จอง ${new Date(r.created_at).toLocaleDateString("th-TH", { day: "numeric", month: "short", year: "numeric" })} · ราคาถูกล็อกถึง ${thaiDate(r.price_locked_until)}</p>
        </div>
      </div>

      <div class="step ${hasLoan ? "done" : "active"} rise" style="animation-delay:80ms">
        <div class="dot" aria-hidden="true">${hasLoan ? ICONS.checkSmall : "2"}</div>
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

      <div class="step ${approved ? "done" : rejected ? "failed" : reviewing ? "active" : ""} rise" style="animation-delay:160ms">
        <div class="dot" aria-hidden="true">${approved ? ICONS.checkSmall : "3"}</div>
        <div class="content">
          <h4>ผลการพิจารณาสินเชื่อ</h4>
          ${reviewing ? '<span class="status-flow">ยื่นเอกสารแล้ว <span class="arr">→</span> กำลังพิจารณา…</span><p class="desc mt-1">สถาบันการเงินกำลังพิจารณา… หน้านี้จะอัปเดตผลให้อัตโนมัติ</p>' : ""}
          ${approved ? '<span class="status-flow ok">กำลังพิจารณา <span class="arr">→</span> อนุมัติแล้ว</span>' : ""}
          ${rejected ? '<span class="status-flow bad">กำลังพิจารณา <span class="arr">→</span> ไม่ผ่านการอนุมัติ</span>' : ""}
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

      <div class="step ${delivered ? "done" : approved ? "active" : ""} rise" style="animation-delay:240ms">
        <div class="dot" aria-hidden="true">${delivered ? ICONS.checkSmall : "4"}</div>
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
        refreshMine();
      } catch (err) {
        toast(err.message, "error");
      }
    });
  }
}

/* ---------- รายการในบัญชี ---------- */

function rsvLabel(r) {
  if (r.status === "cancelled") return STATUS_BADGE.cancelled;
  if (r.status === "delivery_scheduled") return STATUS_BADGE.delivery_scheduled;
  if (r.loan && r.loan.status === "reviewing") return '<span class="badge badge-warn">สินเชื่อกำลังพิจารณา</span>';
  if (r.loan && r.loan.status === "approved") return '<span class="badge badge-ok">สินเชื่ออนุมัติ — รอนัดรับรถ</span>';
  if (r.loan && r.loan.status === "rejected") return '<span class="badge badge-bad">สินเชื่อไม่ผ่าน</span>';
  return STATUS_BADGE.reserved;
}

function renderReservationList() {
  const zone = document.getElementById("rsv-list");
  if (!mine.reservations.length) {
    zone.innerHTML = `<div class="card muted">ยังไม่มีใบจองในบัญชีนี้ —
      <a href="/">เลือกรุ่นรถ</a> แล้วจองออนไลน์ได้เลย</div>`;
    return;
  }
  zone.innerHTML = mine.reservations
    .map(
      (r) => `
      <div class="card booking-pick ${reservation && reservation.code === r.code ? "selected" : ""}"
           data-code="${r.code}" role="button" tabindex="0" aria-label="ดูใบจอง ${r.code}">
        <div class="list-row" style="padding:0;border:none">
          <div class="main">
            <b>${esc(r.car.name)} <span class="muted" style="font-weight:400">สี${esc(r.color.name)}</span></b>
            <span class="num">${r.code} · ${baht(r.total_price)}</span>
          </div>
          ${rsvLabel(r)}
        </div>
      </div>`
    )
    .join("");
  zone.querySelectorAll(".booking-pick").forEach((el) => {
    const open = () => {
      loadReservation(el.dataset.code);
      document.getElementById("rsv-zone").scrollIntoView({ behavior: "smooth", block: "start" });
    };
    el.addEventListener("click", open);
    el.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); }
    });
  });
}

function testdriveRow(td) {
  const future = td.date > new Date().toISOString().slice(0, 10);
  return `
    <div class="list-row">
      <div class="main">
        <b>${esc(td.car.name)}</b>
        <span>${esc(td.showroom.name)} · ${thaiDate(td.date)} เวลา ${td.time} น.</span>
        <span class="num">${td.code}</span>
      </div>
      <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
        ${TD_BADGE[td.status] || ""}
        ${td.status === "confirmed" && future
          ? `<button class="btn btn-danger btn-sm" data-cancel-td="${td.code}" type="button">ยกเลิกนัด</button>`
          : ""}
      </div>
    </div>`;
}

function bindTestdriveCancel(root, after) {
  root.querySelectorAll("[data-cancel-td]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      try {
        const td = await API.cancelTestdrive(btn.dataset.cancelTd);
        toast("ยกเลิกนัดทดลองขับแล้ว คิวนี้เปิดให้คนอื่นจองต่อได้", "ok");
        after(td);
      } catch (err) {
        toast(err.message, "error");
        btn.disabled = false;
      }
    });
  });
}

function renderTestdrives() {
  const zone = document.getElementById("td-zone");
  zone.innerHTML = mine.testdrives.length
    ? `<div class="card list-rows">${mine.testdrives.map(testdriveRow).join("")}</div>`
    : `<div class="card muted">ยังไม่มีนัดทดลองขับ — <a href="/pages/test-drive.html">จองทดลองขับ</a></div>`;
  bindTestdriveCancel(zone, refreshMine);
}

function renderServices() {
  const zone = document.getElementById("sv-zone");
  const active = mine.service_appointments.filter((s) => s.status === "booked");
  zone.innerHTML = active.length
    ? `<div class="card list-rows">${active
        .map(
          (s) => `
          <div class="list-row">
            <div class="main">
              <b>${esc(s.service_type.name)} · ${esc(s.car.name)}</b>
              <span>${esc(s.showroom.name)} · ${thaiDate(s.date)} เวลา ${s.time} น.</span>
            </div>
            <a class="btn btn-ghost btn-sm" href="/pages/after-sales.html">จัดการนัด</a>
          </div>`
        )
        .join("")}</div>`
    : `<div class="card muted">ยังไม่มีนัดเข้าศูนย์ — <a href="/pages/after-sales.html">นัดเช็กระยะออนไลน์</a> รับ 100 คะแนน</div>`;
}

async function refreshMine() {
  try {
    mine = await API.myBookings();
  } catch (err) {
    return toast(err.message, "error");
  }
  renderReservationList();
  renderTestdrives();
  renderServices();
}

// ผู้ที่ยังไม่ล็อกอิน: แสดงนัดทดลองขับที่จองจากเครื่องนี้ (guest) + ชวนเข้าสู่ระบบ
function renderGuest() {
  const zone = document.getElementById("guest-zone");
  const td = Store.load("testdrive");
  zone.innerHTML = `
    <div class="card">
      <h3>เข้าสู่ระบบเพื่อดูการจองทั้งหมด</h3>
      <p class="muted mt-1">ใบจองรถ สถานะสินเชื่อ และแจ้งเตือนผูกกับบัญชีของคุณ เพื่อความปลอดภัยของข้อมูลส่วนตัว</p>
      <div class="mt-2" style="display:flex;gap:12px;flex-wrap:wrap">
        <a class="btn btn-primary" href="/pages/login.html?next=${encodeURIComponent(location.pathname + location.search)}">เข้าสู่ระบบ</a>
        <a class="btn btn-ghost" href="/pages/register.html">สมัครสมาชิก</a>
      </div>
    </div>
    ${td ? `<h3 class="mt-3 mb-2">นัดทดลองขับที่จองจากเครื่องนี้</h3><div class="card list-rows" id="guest-td">${testdriveRow(td)}</div>` : ""}`;
  const box = document.getElementById("guest-td");
  if (box) {
    bindTestdriveCancel(box, (updated) => {
      Store.save("testdrive", updated);
      renderGuest();
    });
  }
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
          refreshMine();   // ป้ายสถานะในรายการใบจองต้องเปลี่ยนตามผลด้วย
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
  if (mine) renderReservationList();
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
    refreshMine();
  } catch (err) {
    toast(err.message, "error");
  }
});

/* ---------- เริ่มต้น ---------- */

async function initStatus() {
  if (!Auth.isLoggedIn()) {
    renderGuest();
    return;
  }
  document.getElementById("member-zone").classList.remove("hidden");

  document.getElementById("st-load").addEventListener("click", () => {
    const code = document.getElementById("st-code").value.trim();
    if (code) loadReservation(code);
  });
  document.getElementById("st-code").addEventListener("keydown", (e) => {
    if (e.key === "Enter") document.getElementById("st-load").click();
  });

  await refreshMine();
  if (!mine) return;
  const wanted = qs("code") || Store.load("reservation_code");
  const pick = mine.reservations.find((r) => r.code === wanted) || mine.reservations[0];
  if (pick) loadReservation(pick.code);
}

initStatus();
