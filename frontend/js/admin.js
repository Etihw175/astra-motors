// หลังบ้านโชว์รูม: ตัวเลขสรุป + ตารางนัดทดลองขับ / ใบจอง / สินเชื่อ / นัดเข้าศูนย์ + ปิดงานหน้าเคาน์เตอร์
// หน้านี้แตะเฉพาะ /api/admin/* ซึ่งปิดด้วย require_admin ทั้งหมด — การ์ด "เฉพาะผู้ดูแลระบบ" เป็นเพียง UX
"use strict";

renderHeader("admin");
renderFooter();

const TODAY = new Date().toISOString().slice(0, 10);

const TD_STATUS = {
  confirmed: ['badge-accent', 'ยืนยันแล้ว'],
  completed: ['badge-ok', 'มาแล้ว'],
  no_show: ['badge-bad', 'ไม่มาตามนัด'],
  cancelled: ['badge-warn', 'ยกเลิก'],
};
const RS_STATUS = {
  reserved: ['badge-accent', 'วางเงินจองแล้ว'],
  delivery_scheduled: ['badge-ok', 'นัดรับรถแล้ว'],
  cancelled: ['badge-warn', 'ยกเลิก'],
};
const LN_STATUS = {
  reviewing: ['badge-accent', 'กำลังพิจารณา'],
  approved: ['badge-ok', 'อนุมัติ'],
  rejected: ['badge-bad', 'ไม่อนุมัติ'],
};
const SV_STATUS = {
  booked: ['badge-accent', 'รอเข้าศูนย์'],
  completed: ['badge-ok', 'ปิดงานแล้ว'],
  cancelled: ['badge-warn', 'ยกเลิก'],
};

function badge(map, status) {
  const [cls, label] = map[status] || ['badge-warn', status];
  return `<span class="badge ${cls}">${esc(label)}</span>`;
}

/* ---------- แท็บ ---------- */

// initTabs (ui.js) ดูแล aria-selected / aria-controls / roving tabindex / ลูกศรซ้าย-ขวาให้
initTabs(document.querySelector(".tabs"), (name) => TABLES[name].load());

/* ---------- ตัวเลขสรุป ---------- */

function tile(label, value, hint) {
  return `<div class="card stat-tile">
    <p class="label">${esc(label)}</p>
    <p class="value">${esc(value)}</p>
    <p class="hint">${esc(hint || "")}</p>
  </div>`;
}

function count(byStatus, status) {
  return (byStatus || {})[status] || 0;
}

async function renderOverview() {
  const zone = document.getElementById("ad-tiles");
  let data;
  try {
    data = await API.adminOverview();
  } catch (err) {
    zone.innerHTML = `<p class="muted small">${esc(err.message)}</p>`;
    return;
  }
  const num = (n) => Number(n).toLocaleString("th-TH");
  zone.innerHTML = [
    tile("สมาชิกทั้งหมด", num(data.members.total), `ลูกค้า ${num(data.members.customers)} คน`),
    tile("ทดลองขับวันนี้", num(data.testdrives.today), `ที่จะถึง ${num(data.testdrives.upcoming)} นัด`),
    tile("มาแล้ว / ไม่มาตามนัด",
      `${num(count(data.testdrives.by_status, "completed"))} / ${num(count(data.testdrives.by_status, "no_show"))}`,
      "สถิติสะสมทุกสาขา"),
    tile("ใบจองที่ยังไม่ยกเลิก",
      num(count(data.reservations.by_status, "reserved") + count(data.reservations.by_status, "delivery_scheduled")),
      `นัดรับรถแล้ว ${num(count(data.reservations.by_status, "delivery_scheduled"))} ใบ`),
    tile("มูลค่าใบจองรวม", baht(data.reservations.active_value), "เฉพาะใบที่ยังไม่ยกเลิก"),
    tile("เงินจองที่รับแล้ว", baht(data.reservations.booking_fee_received), "ยอดสะสมจากใบจองที่ยังมีผล"),
    tile("สินเชื่อรอพิจารณา", num(count(data.loans.by_status, "reviewing")),
      `อนุมัติ ${num(count(data.loans.by_status, "approved"))} · ไม่อนุมัติ ${num(count(data.loans.by_status, "rejected"))}`),
    tile("นัดเข้าศูนย์ที่จะถึง", num(data.service_appointments.upcoming),
      `ปิดงานแล้ว ${num(count(data.service_appointments.by_status, "completed"))} นัด`),
  ].join("");
}

/* ---------- โครงร่วมของทุกตาราง (กรอง + แบ่งหน้า + ปุ่มในแถว) ---------- */

function makeTable({ prefix, colspan, unit, fetcher, filters, row, bind }) {
  const view = { page: 1, per_page: 8 };

  async function load() {
    const tbody = document.getElementById(`${prefix}-rows`);
    tbody.setAttribute("aria-busy", "true");
    tbody.innerHTML = `<tr><td colspan="${colspan}" class="muted">กำลังโหลด…</td></tr>`;
    let data;
    try {
      data = await fetcher({ ...filters(), page: view.page, per_page: view.per_page });
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="${colspan}" class="muted">${esc(err.message)}</td></tr>`;
      tbody.setAttribute("aria-busy", "false");
      return;
    }
    tbody.setAttribute("aria-busy", "false");

    tbody.innerHTML = data.items.length
      ? data.items.map(row).join("")
      : `<tr><td colspan="${colspan}" class="muted">ไม่พบรายการตามเงื่อนไขที่เลือก</td></tr>`;

    const from = data.total ? (data.page - 1) * data.per_page + 1 : 0;
    document.getElementById(`${prefix}-summary`).textContent =
      `แสดง ${from}-${Math.min(data.page * data.per_page, data.total)} จากทั้งหมด ${data.total} ${unit} ` +
      `(หน้า ${data.page}/${data.total_pages})`;

    const pages = document.getElementById(`${prefix}-pages`);
    let html = `<button type="button" ${data.page <= 1 ? "disabled" : ""} data-page="${data.page - 1}">ก่อนหน้า</button>`;
    for (let p = 1; p <= data.total_pages; p++) {
      const on = p === data.page;
      html += `<button type="button" class="${on ? "active" : ""}" data-page="${p}"
        aria-label="หน้า ${p}" ${on ? 'aria-current="page"' : ""}>${p}</button>`;
    }
    html += `<button type="button" ${data.page >= data.total_pages ? "disabled" : ""} data-page="${data.page + 1}">ถัดไป</button>`;
    pages.innerHTML = html;
    pages.querySelectorAll("[data-page]").forEach((btn) =>
      btn.addEventListener("click", () => {
        view.page = Number(btn.dataset.page);
        load();
      })
    );

    if (bind) bind(load);
  }

  // เปลี่ยนตัวกรองแล้วต้องกลับหน้า 1 ไม่งั้นค้างอยู่หน้าที่ไม่มีข้อมูล
  function reset() {
    view.page = 1;
    load();
  }

  return { load, reset };
}

// ช่องค้นหาพิมพ์ติดกันเร็ว ๆ — หน่วงไว้ไม่ให้ยิง API ทุกตัวอักษร
function bindFilters(ids, reset) {
  ids.forEach((id) => {
    const el = document.getElementById(id);
    if (el.type === "search") {
      let timer = null;
      el.addEventListener("input", () => {
        clearTimeout(timer);
        timer = setTimeout(reset, 350);
      });
    } else {
      el.addEventListener("change", reset);
    }
  });
}

const val = (id) => document.getElementById(id).value;

/* ---------- ตาราง: นัดทดลองขับ ---------- */

const TABLES = {};

TABLES.testdrives = makeTable({
  prefix: "td",
  colspan: 7,
  unit: "นัด",
  fetcher: API.adminTestdrives,
  filters: () => ({
    q: val("td-q").trim(), status: val("td-status"), showroom_id: val("td-showroom"),
    date_from: val("td-from"), date_to: val("td-to"),
  }),
  row: (t) => `
    <tr>
      <td class="num">${esc(t.code)}</td>
      <td>${thaiDate(t.date)}<br><span class="muted small">${esc(t.time)} น.</span></td>
      <td>${esc(t.name)}<br><span class="muted small">${esc(t.phone)}</span>
        ${t.contact_message_only ? '<br><span class="badge badge-warn">ติดต่อทางข้อความ</span>' : ""}</td>
      <td>${esc(t.car.name)}</td>
      <td>${esc(t.showroom.name)}</td>
      <td>${badge(TD_STATUS, t.status)}</td>
      <td>
        <div class="row-actions">
          ${
            t.status !== "confirmed"
              ? '<span class="muted small">ปิดงานแล้ว</span>'
              : t.date > TODAY
                ? '<span class="muted small">ยังไม่ถึงวันนัด</span>'
                : `<button class="btn btn-primary btn-sm" data-done="${esc(t.code)}">มาแล้ว</button>
                   <button class="btn btn-ghost btn-sm" data-noshow="${esc(t.code)}">ไม่มาตามนัด</button>`
          }
        </div>
      </td>
    </tr>`,
  bind: (reload) => {
    document.querySelectorAll("[data-done], [data-noshow]").forEach((btn) =>
      btn.addEventListener("click", async () => {
        const noShow = btn.hasAttribute("data-noshow");
        btn.disabled = true;
        try {
          await API.adminCompleteTestdrive(
            noShow ? btn.dataset.noshow : btn.dataset.done,
            noShow ? "no_show" : "completed"
          );
          toast(noShow ? "บันทึกว่าไม่มาตามนัดแล้ว" : "ปิดนัดแล้ว ลูกค้าได้รับคำเชิญเขียนรีวิว", "ok");
          reload();
          renderOverview();
        } catch (err) {
          toast(err.message, "error");
          btn.disabled = false;
        }
      })
    );
  },
});

/* ---------- ตาราง: ใบจอง ---------- */

TABLES.reservations = makeTable({
  prefix: "rs",
  colspan: 7,
  unit: "ใบ",
  fetcher: API.adminReservations,
  filters: () => ({ q: val("rs-q").trim(), status: val("rs-status") }),
  row: (r) => `
    <tr>
      <td class="num">${esc(r.code)}</td>
      <td>${esc(r.customer.name)}<br><span class="muted small">${esc(r.customer.phone)}</span></td>
      <td>${esc(r.car.name)}<br><span class="muted small">${esc(r.color.name)}</span></td>
      <td class="num">${baht(r.total_price)}</td>
      <td>${r.loan_status ? badge(LN_STATUS, r.loan_status) : '<span class="muted small">ไม่ยื่นสินเชื่อ</span>'}</td>
      <td>${badge(RS_STATUS, r.status)}</td>
      <td class="muted small">${esc(r.created_at.slice(0, 10))}</td>
    </tr>`,
});

/* ---------- ตาราง: สินเชื่อ ---------- */

TABLES.loans = makeTable({
  prefix: "ln",
  colspan: 7,
  unit: "คำขอ",
  fetcher: API.adminLoans,
  filters: () => ({ q: val("ln-q").trim(), status: val("ln-status") }),
  row: (l) => `
    <tr>
      <td class="num">${esc(l.id)}</td>
      <td class="num">${esc(l.reservation_code)}</td>
      <td>${esc(l.applicant.name)}<br><span class="muted small">${esc(l.applicant.phone)}</span></td>
      <td>${esc(l.plan.name)}<br><span class="muted small">${esc(l.term_months)} เดือน</span></td>
      <td class="num">${baht(l.down_payment)}<br><span class="muted small">${esc(l.down_pct)}%</span></td>
      <td class="num">${baht(l.monthly_payment)}</td>
      <td>${badge(LN_STATUS, l.status)}</td>
    </tr>`,
});

/* ---------- ตาราง: นัดเข้าศูนย์บริการ ---------- */

TABLES.services = makeTable({
  prefix: "sv",
  colspan: 7,
  unit: "นัด",
  fetcher: API.adminServices,
  filters: () => ({
    status: val("sv-status"), showroom_id: val("sv-showroom"),
    date_from: val("sv-from"), date_to: val("sv-to"),
  }),
  row: (s) => `
    <tr>
      <td class="num">${esc(s.code)}</td>
      <td>${thaiDate(s.date)}<br><span class="muted small">${esc(s.time)} น.</span></td>
      <td>${esc(s.car.name)}</td>
      <td>${esc(s.showroom.name)}</td>
      <td>${esc(s.service_type.name)}<br><span class="muted small">${Number(s.mileage_km).toLocaleString("th-TH")} กม.</span></td>
      <td>${badge(SV_STATUS, s.status)}</td>
      <td>
        <div class="row-actions">
          ${
            s.status === "booked"
              ? `<button class="btn btn-primary btn-sm" data-close="${esc(s.code)}">ปิดงานบริการ</button>`
              : '<span class="muted small">ปิดงานแล้ว</span>'
          }
        </div>
      </td>
    </tr>`,
  bind: (reload) => {
    document.querySelectorAll("[data-close]").forEach((btn) =>
      btn.addEventListener("click", async () => {
        btn.disabled = true;
        try {
          await API.adminCompleteService(btn.dataset.close);
          toast("ปิดงานบริการแล้ว ลูกค้าได้รับแจ้งเตือน", "ok");
          reload();
          renderOverview();
        } catch (err) {
          toast(err.message, "error");
          btn.disabled = false;
        }
      })
    );
  },
});

/* ---------- เริ่มทำงาน ---------- */

async function fillShowrooms() {
  let rooms = [];
  try {
    rooms = await API.showrooms();
  } catch {
    return;   // เลือกสาขาไม่ได้ก็ยังดูรายการทั้งหมดได้
  }
  document.getElementById("td-showroom").insertAdjacentHTML(
    "beforeend",
    rooms.map((s) => `<option value="${esc(s.id)}">${esc(s.name)}</option>`).join("")
  );
  document.getElementById("sv-showroom").insertAdjacentHTML(
    "beforeend",
    rooms
      .filter((s) => s.service_center)
      .map((s) => `<option value="${esc(s.id)}">${esc(s.name)}</option>`)
      .join("")
  );
}

function initAdmin() {
  if (!requireLogin("/pages/admin.html")) return;
  const user = Auth.user();
  if (!user || user.role !== "admin") {
    document.getElementById("ad-denied").classList.remove("hidden");
    return;
  }
  document.getElementById("ad-body").classList.remove("hidden");

  bindFilters(["td-q", "td-status", "td-showroom", "td-from", "td-to"], TABLES.testdrives.reset);
  bindFilters(["rs-q", "rs-status"], TABLES.reservations.reset);
  bindFilters(["ln-q", "ln-status"], TABLES.loans.reset);
  bindFilters(["sv-status", "sv-showroom", "sv-from", "sv-to"], TABLES.services.reset);

  fillShowrooms();
  renderOverview();
  TABLES.testdrives.load();
}

initAdmin();
