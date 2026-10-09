// ส่วนกลางของทุกหน้า: header/footer, รูปรถ SVG, ตัวช่วยจัดรูปแบบ, toast, localStorage
"use strict";

/* ---------- Header / Footer ---------- */

// โลโก้ ASTRA/MOTORS พากลับหน้าแรกอยู่แล้ว จึงไม่ต้องมีเมนู "หน้าแรก" ซ้ำ
const NAV_ITEMS = [
  { key: "compare", label: "เปรียบเทียบ", href: "/pages/compare.html" },
  { key: "finance", label: "ไฟแนนซ์", href: "/pages/finance.html" },
  { key: "thai-road", label: "ถนนไทย", href: "/pages/thai-road.html" },
  { key: "testdrive", label: "จองทดลองขับ", href: "/pages/test-drive.html" },
  { key: "status", label: "การจองของฉัน", href: "/pages/status.html" },
  { key: "after-sales", label: "หลังการขาย", href: "/pages/after-sales.html" },
  // หลังบ้านเป็นเมนูเดียวที่ขึ้นกับสิทธิ์ — renderHeader คัดออกให้ลูกค้าไม่เห็นลิงก์เลย
  { key: "admin", label: "หลังบ้าน", href: "/pages/admin.html", adminOnly: true },
];

function renderHeader(activeKey) {
  // ซ่อนเมนูเฉพาะ admin ตั้งแต่ตอน render (ฝั่ง backend กันซ้ำอีกชั้นด้วย require_admin)
  const isAdmin = typeof Auth !== "undefined" && Auth.user() && Auth.user().role === "admin";
  const nav = NAV_ITEMS.filter((i) => !i.adminOnly || isAdmin).map(
    (i) =>
      `<a href="${i.href}" ${i.key === activeKey ? 'class="active" aria-current="page"' : ""}>${i.label}</a>`
  ).join("");
  // ลิงก์ข้ามเมนู: ผู้ใช้คีย์บอร์ดกด Tab ครั้งแรกแล้วกระโดดเข้าเนื้อหาหลักได้เลย
  // ทุกหน้ามี <main id="main-content" tabindex="-1"> เป็นเป้าหมาย
  const main = document.getElementById("main-content");
  if (main && !main.hasAttribute("tabindex")) main.setAttribute("tabindex", "-1");
  document.body.insertAdjacentHTML(
    "afterbegin",
    `<a class="skip-link" href="#main-content">ข้ามไปที่เนื้อหาหลัก</a>
     <header class="site-header">
       <div class="container bar">
         <a class="brand" href="/">ASTRA<span class="tick">/</span>MOTORS</a>
         <nav class="site-nav" aria-label="เมนูหลัก">${nav}</nav>
         <div class="auth-zone" id="auth-zone"></div>
       </div>
     </header>`
  );
  renderAuthZone(activeKey);
}

/* ---------- แถบสมาชิกมุมขวาบน (ขึ้นกับสถานะล็อกอิน) ---------- */

function renderAuthZone(activeKey) {
  const zone = document.getElementById("auth-zone");
  if (!zone || typeof Auth === "undefined") return;

  const user = Auth.user();
  if (!Auth.isLoggedIn() || !user) {
    zone.innerHTML =
      `<a class="btn btn-ghost btn-sm" href="/pages/login.html">เข้าสู่ระบบ</a>
       <a class="btn btn-primary btn-sm" href="/pages/register.html">สมัครสมาชิก</a>`;
    return;
  }

  const initial = esc((user.full_name || user.username || "?").trim().charAt(0));
  zone.innerHTML = `
    <div class="bell-wrap">
      <button class="bell" id="bell" type="button" aria-haspopup="true" aria-expanded="false"
              aria-controls="bell-panel" aria-label="แจ้งเตือน">
        ${ICONS.bell}<span class="bell-count hidden" id="bell-count" aria-hidden="true">0</span>
      </button>
      <div class="bell-panel hidden" id="bell-panel" role="dialog" aria-label="แจ้งเตือนของฉัน"></div>
    </div>
    <a class="user-pill ${activeKey === "profile" ? "active" : ""}" href="/pages/profile.html"
       title="โปรไฟล์ของฉัน">
      <span class="avatar" aria-hidden="true">${initial}</span>
      <span class="who">
        <b>${esc(user.full_name || user.username)}</b>
        <small>${user.role === "admin" ? "ผู้ดูแลระบบ" : "สมาชิก"}</small>
      </span>
    </a>
    <button class="btn btn-ghost btn-sm" id="btn-logout" type="button">ออกจากระบบ</button>`;
  initBell();

  document.getElementById("btn-logout").addEventListener("click", async () => {
    _closeBellStream();   // ออกจากระบบแล้วสตรีมแจ้งเตือนของคนเดิมต้องหยุดทันที
    _stopBellPoll();
    try {
      await API.logout();
    } catch {
      /* token หมดอายุอยู่แล้วก็ถือว่าออกจากระบบสำเร็จ */
    }
    Auth.clear();
    toast("ออกจากระบบเรียบร้อย", "ok");
    setTimeout(() => (location.href = "/"), 600);
  });
}

/* ---------- กระดิ่งแจ้งเตือน (journey ขั้นตอน 6) ----------
   ช่องทางหลักคือ SSE: เซิร์ฟเวอร์ push แจ้งเตือนใหม่มาทันที ไม่ต้องรอรอบ poll
   แต่ยังต้องเก็บ poll ไว้เป็น fallback เพราะ EventSource อาจเปิดไม่ได้ (เบราว์เซอร์เก่า / proxy ตัด / เน็ตหลุด)
   กฎสำคัญ: ห้ามให้ poll ทำงานซ้อนกับสตรีมพร้อมกัน ไม่งั้นยิง API ซ้ำเปล่า ๆ */

const BELL_POLL_MS = 15000;          // รอบ poll ตอนที่ไม่มีสตรีม
const BELL_RETRY_MS = 3000;          // หน่วงก่อนลองเปิดสตรีมใหม่ครั้งแรก
const BELL_RETRY_MAX_MS = 60000;     // เพดานการถอยหลัง (3s → 6s → 12s → … → 60s)
let _bellUnread = null;
let _bellStream = null;              // EventSource ที่เปิดอยู่ (null = ยังไม่มีสตรีม)
let _bellPollTimer = null;
let _bellRetryTimer = null;
let _bellRetryMs = BELL_RETRY_MS;
let _bellUnloadHooked = false;

function _timeAgo(iso) {
  const sec = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (sec < 60) return "เมื่อสักครู่";
  if (sec < 3600) return `${Math.floor(sec / 60)} นาทีที่แล้ว`;
  if (sec < 86400) return `${Math.floor(sec / 3600)} ชั่วโมงที่แล้ว`;
  return new Date(iso).toLocaleDateString("th-TH", { day: "numeric", month: "short" });
}

function _setBellCount(n) {
  const badge = document.getElementById("bell-count");
  if (!badge) return;
  badge.textContent = n > 9 ? "9+" : String(n);
  badge.classList.toggle("hidden", !n);
  // ตัวเลขบนกระดิ่งเป็น aria-hidden — ใส่ความหมายไว้ใน aria-label ของปุ่มแทน
  const bell = document.getElementById("bell");
  if (bell) bell.setAttribute("aria-label", n ? `แจ้งเตือน — ยังไม่ได้อ่าน ${n} รายการ` : "แจ้งเตือน");
}

async function _renderBellPanel() {
  const panel = document.getElementById("bell-panel");
  panel.innerHTML = '<p class="muted small bell-empty">กำลังโหลด…</p>';
  try {
    const data = await API.notifications(12);
    _bellUnread = data.unread;
    _setBellCount(data.unread);
    const list = data.items
      .map(
        (n) => `<li class="${n.is_read ? "" : "unread"}">
          <a href="${esc(n.link || "#")}" data-id="${n.id}">
            <b>${esc(n.title)}</b><span>${esc(n.message)}</span><small>${_timeAgo(n.created_at)}</small>
          </a></li>`
      )
      .join("");
    panel.innerHTML = `
      <div class="bell-head">
        <b>แจ้งเตือน</b>
        <button type="button" class="link-btn" id="bell-read-all" ${data.unread ? "" : "disabled"}>อ่านทั้งหมด</button>
      </div>
      ${
        data.items.length
          ? `<ul class="bell-list">${list}</ul>`
          : '<p class="muted small bell-empty">ยังไม่มีแจ้งเตือน — ลองจองทดลองขับหรือจองรถดูสิ</p>'
      }`;
    document.getElementById("bell-read-all").addEventListener("click", async () => {
      await API.readAllNotifications().catch(() => null);
      _renderBellPanel();
    });
    panel.querySelectorAll("a[data-id]").forEach((a) => {
      a.addEventListener("click", () => API.readNotification(a.dataset.id).catch(() => null));
    });
  } catch (err) {
    panel.innerHTML = `<p class="muted small bell-empty">${esc(err.message)}</p>`;
  }
}

async function _pollBell() {
  if (!Auth.isLoggedIn()) return;
  try {
    const { unread } = await API.unreadCount();
    if (_bellUnread !== null && unread > _bellUnread) {
      const latest = await API.notifications(1);
      if (latest.items[0]) toast(`${latest.items[0].title} — ${latest.items[0].message}`, "ok");
    }
    _bellUnread = unread;
    _setBellCount(unread);
  } catch {
    /* ออฟไลน์ชั่วคราว — รอบหน้าลองใหม่ */
  }
}

/* เปิด/ปิด poll — ใช้เป็น fallback ระหว่างที่สตรีมยังต่อไม่ติดเท่านั้น */
function _startBellPoll() {
  if (_bellPollTimer) return;        // กันตั้ง interval ซ้อนกันหลายอัน
  _pollBell();
  _bellPollTimer = setInterval(_pollBell, BELL_POLL_MS);
}

function _stopBellPoll() {
  if (!_bellPollTimer) return;
  clearInterval(_bellPollTimer);
  _bellPollTimer = null;
}

function _closeBellStream() {
  if (_bellStream) {
    _bellStream.close();
    _bellStream = null;
  }
  if (_bellRetryTimer) {
    clearTimeout(_bellRetryTimer);
    _bellRetryTimer = null;
  }
}

// สตรีมพัง/ปิด → กลับไป poll ก่อน แล้วค่อย ๆ ถอยหลังไปขอตั๋วใหม่เปิดสตรีมใหม่ (exponential backoff)
function _retryBellStream() {
  _closeBellStream();
  _startBellPoll();
  if (!Auth.isLoggedIn()) return;
  _bellRetryTimer = setTimeout(_openBellStream, _bellRetryMs);
  _bellRetryMs = Math.min(_bellRetryMs * 2, BELL_RETRY_MAX_MS);
}

async function _openBellStream() {
  if (!Auth.isLoggedIn()) return;
  _closeBellStream();

  let ticket;
  try {
    // ขอตั๋วก่อนเพราะ EventSource แนบ header Authorization เองไม่ได้ และห้ามส่ง token ใน URL
    ticket = (await API.streamTicket()).ticket;
  } catch {
    _retryBellStream();
    return;
  }

  const stream = new EventSource(`/api/notifications/stream?ticket=${encodeURIComponent(ticket)}`);
  _bellStream = stream;

  stream.addEventListener("open", () => {
    _stopBellPoll();                 // สตรีมมาแล้ว ไม่ต้อง poll ซ้อน
    _bellRetryMs = BELL_RETRY_MS;    // ต่อสำเร็จแล้ว รีเซ็ตการถอยหลัง
  });

  stream.addEventListener("unread", (e) => {
    const data = _parseBellEvent(e);
    if (!data) return;
    _bellUnread = data.unread;
    _setBellCount(data.unread);
  });

  stream.addEventListener("notification", (e) => {
    const item = _parseBellEvent(e);
    if (!item) return;
    _bellUnread = (_bellUnread || 0) + 1;
    _setBellCount(_bellUnread);
    // toast() ใส่ข้อความด้วย textContent อยู่แล้ว ข้อความจากเซิร์ฟเวอร์จึงกลายเป็น HTML ไม่ได้ (ไม่ต้อง esc())
    toast(`${item.title} — ${item.message}`, "ok");
  });

  // ตั๋วใช้ซ้ำไม่ได้ ดังนั้น reconnect อัตโนมัติของ EventSource จะโดน 401 — ต้องปิดแล้วขอตั๋วใหม่เอง
  stream.addEventListener("error", () => {
    if (_bellStream !== stream) return;   // สตรีมเก่าที่เลิกใช้แล้ว ไม่ต้องทำอะไร
    _retryBellStream();
  });
}

function _parseBellEvent(e) {
  try {
    return JSON.parse(e.data);
  } catch {
    return null;                     // data เสียหนึ่งรอบ ไม่ควรทำให้กระดิ่งเจ๊ง
  }
}

function initBell() {
  const bell = document.getElementById("bell");
  const panel = document.getElementById("bell-panel");
  bell.addEventListener("click", (e) => {
    e.stopPropagation();
    const open = !panel.classList.toggle("hidden");
    bell.setAttribute("aria-expanded", String(open));
    if (open) _renderBellPanel();
  });
  document.addEventListener("click", (e) => {
    if (!panel.contains(e.target) && e.target !== bell) {
      panel.classList.add("hidden");
      bell.setAttribute("aria-expanded", "false");
    }
  });
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape" || panel.classList.contains("hidden")) return;
    panel.classList.add("hidden");
    bell.setAttribute("aria-expanded", "false");
    bell.focus();   // ปิดแล้วโฟกัสต้องกลับมาที่ปุ่มที่เปิด ไม่หลุดไปต้นหน้า
  });
  if (!_bellUnloadHooked) {
    // ปิดสตรีมเมื่อออกจากหน้า — ไม่งั้นเซิร์ฟเวอร์ถือ connection ค้างไว้
    window.addEventListener("pagehide", _closeBellStream);
    _bellUnloadHooked = true;
  }
  if (typeof EventSource === "function") {
    _pollBell();                     // เติมตัวเลขบนกระดิ่งทันทีหนึ่งรอบ ระหว่างรอขอตั๋ว/ต่อสตรีม
    _openBellStream();
  } else {
    _startBellPoll();                // เบราว์เซอร์เก่าไม่รองรับ SSE — ใช้ poll อย่างเดิม
  }
}

/* ---------- แท็บแบบ ARIA (ใช้ร่วมกัน: โปรไฟล์ / หลังการขาย / หลังบ้าน) ----------
   ตาม WAI-ARIA tabs pattern: ในกลุ่มแท็บมีปุ่มเดียวที่อยู่ในลำดับ Tab (roving tabindex)
   แล้วเดินระหว่างแท็บด้วยลูกศรซ้าย/ขวา + Home/End */

function initTabs(container, onSelect) {
  const tabs = container ? [...container.querySelectorAll("button[data-tab]")] : [];
  if (!tabs.length) return { select() {} };
  const panels = [...document.querySelectorAll("[data-panel]")];

  tabs.forEach((tab) => {
    const name = tab.dataset.tab;
    tab.setAttribute("role", "tab");
    tab.type = "button";
    if (!tab.id) tab.id = `tabbtn-${name}`;
    const panel = panels.find((p) => p.dataset.panel === name);
    if (panel) {
      if (!panel.id) panel.id = `tabpanel-${name}`;
      tab.setAttribute("aria-controls", panel.id);
      panel.setAttribute("role", "tabpanel");
      panel.setAttribute("aria-labelledby", tab.id);
    }
  });

  function paint(name) {
    tabs.forEach((tab) => {
      const on = tab.dataset.tab === name;
      tab.classList.toggle("active", on);
      tab.setAttribute("aria-selected", String(on));
      tab.tabIndex = on ? 0 : -1;
    });
    panels.forEach((p) => p.classList.toggle("hidden", p.dataset.panel !== name));
  }

  // moveFocus = true เมื่อผู้ใช้เดินด้วยลูกศร (โฟกัสต้องตามไปที่แท็บที่เลือก)
  function select(name, moveFocus) {
    const tab = tabs.find((t) => t.dataset.tab === name);
    if (!tab || tab.classList.contains("hidden")) return;
    paint(name);
    if (moveFocus) tab.focus();
    if (onSelect) onSelect(name);
  }

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => select(tab.dataset.tab));
    tab.addEventListener("keydown", (e) => {
      const open = tabs.filter((t) => !t.classList.contains("hidden"));
      const i = open.indexOf(tab);
      let next = null;
      if (e.key === "ArrowRight" || e.key === "ArrowDown") next = open[(i + 1) % open.length];
      else if (e.key === "ArrowLeft" || e.key === "ArrowUp") next = open[(i - 1 + open.length) % open.length];
      else if (e.key === "Home") next = open[0];
      else if (e.key === "End") next = open[open.length - 1];
      if (!next) return;
      e.preventDefault();
      select(next.dataset.tab, true);
    });
  });

  const current = tabs.find((t) => t.classList.contains("active")) || tabs[0];
  paint(current.dataset.tab);
  return { select };
}

/* ---------- กลุ่ม chip / swatch ที่เป็น role="radio" ----------
   radiogroup ตามมาตรฐานต้องมีสมาชิกเดียวที่อยู่ในลำดับ Tab แล้วเดินด้วยลูกศร
   (Enter/Space ใช้ได้เองเพราะทุกตัวเป็น <button>) */

function bindRadioGroup(zone) {
  if (!zone) return;
  const all = () => [...zone.querySelectorAll('[role="radio"]')];
  const usable = () => all().filter((el) => !el.disabled);

  // ตั้ง roving tabindex ใหม่ทุกครั้งที่กลุ่มถูก render ใหม่
  function syncTabindex() {
    const list = usable();
    if (!list.length) return;
    const on = list.find((el) => el.getAttribute("aria-checked") === "true") || list[0];
    all().forEach((el) => (el.tabIndex = el === on ? 0 : -1));
  }
  syncTabindex();

  if (zone.dataset.radioBound) return;   // ผูก listener ครั้งเดียวต่อ zone (innerHTML เปลี่ยนไม่ลบ dataset)
  zone.dataset.radioBound = "1";

  zone.addEventListener("keydown", (e) => {
    const cur = e.target.closest && e.target.closest('[role="radio"]');
    if (!cur) return;
    const list = usable();
    const i = list.indexOf(cur);
    if (i < 0) return;
    let next = null;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") next = list[(i + 1) % list.length];
    else if (e.key === "ArrowLeft" || e.key === "ArrowUp") next = list[(i - 1 + list.length) % list.length];
    else if (e.key === "Home") next = list[0];
    else if (e.key === "End") next = list[list.length - 1];
    if (!next) return;
    e.preventDefault();
    const at = all().indexOf(next);
    next.click();                        // radio เลือกทันทีที่เลื่อนถึง
    // บางกลุ่ม (ชิปรุ่นรถ/สี/งวด) render ใหม่ทั้งก้อน — หยิบตัวที่ตำแหน่งเดิมมาโฟกัสต่อ
    const fresh = all();
    (fresh[at] || next).focus();
  });

  zone.addEventListener("click", syncTabindex);
}

/* ---------- ฟอร์ม: ผูกข้อความ error เข้ากับช่องกรอก ----------
   ไม่ใช้สีเพียงอย่างเดียว (CSS เติมไอคอน + คำว่า "ผิดพลาด" ให้)
   และผูกด้วย aria-describedby + aria-invalid เพื่อให้โปรแกรมอ่านหน้าจออ่านเหตุผลได้ */

let _errSeq = 0;

function setFieldInvalid(inputId, invalid) {
  const input = document.getElementById(inputId);
  if (!input) return;
  const field = input.closest(".field");
  if (field) field.classList.toggle("invalid", Boolean(invalid));
  input.setAttribute("aria-invalid", invalid ? "true" : "false");

  const err = field && field.querySelector(".error");
  if (!err) return;
  if (!err.id) err.id = `err-${inputId || ++_errSeq}`;
  const described = (input.getAttribute("aria-describedby") || "").split(/\s+/).filter(Boolean);
  const rest = described.filter((id) => id !== err.id);
  // ใส่ id ของข้อความ error ต่อท้ายเฉพาะตอนที่ผิดจริง (ไม่งั้นจะอ่านข้อความที่ซ่อนอยู่)
  input.setAttribute("aria-describedby", invalid ? [...rest, err.id].join(" ") : rest.join(" "));
  if (!invalid && !rest.length) input.removeAttribute("aria-describedby");
}

/* ---------- บังคับให้ล็อกอินก่อนเข้าหน้าที่ต้องใช้สิทธิ์ ---------- */

function requireLogin(nextPath) {
  if (Auth.isLoggedIn()) return true;
  const next = encodeURIComponent(nextPath || location.pathname);
  location.href = `/pages/login.html?next=${next}`;
  return false;
}

function renderFooter() {
  document.body.insertAdjacentHTML(
    "beforeend",
    `<footer class="site-footer">
       <div class="container">
         <span>ASTRA<span style="color:var(--accent)">/</span>MOTORS — โปรเจกต์เพื่อการศึกษา</span>
         <span>ข้อมูลรถ ราคา และการชำระเงินทั้งหมดเป็นการจำลอง</span>
       </div>
     </footer>
     <div class="toast-zone" id="toast-zone" role="status" aria-live="polite" aria-atomic="false"></div>`
  );
}

/* ---------- รูปรถ SVG (เปลี่ยนสีได้ตามที่ผู้ใช้เลือก) ---------- */

let _svgSeq = 0;
function carSVG(color = "#4A4F55") {
  const uid = `g${++_svgSeq}`;
  return `
  <svg viewBox="0 0 640 240" role="img" aria-label="ภาพจำลองรถ SUV" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="${uid}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#ffffff" stop-opacity="0.22"/>
        <stop offset="0.45" stop-color="#ffffff" stop-opacity="0.04"/>
        <stop offset="1" stop-color="#000000" stop-opacity="0.25"/>
      </linearGradient>
    </defs>
    <ellipse cx="320" cy="212" rx="272" ry="13" fill="#000" opacity="0.45"/>
    <path d="M44,186 L44,150 C44,136 56,130 76,126 L130,118
             C162,76 202,62 250,60 L396,60 C446,62 488,84 518,112
             L566,122 C590,127 596,138 596,150 L596,186
             L524,186 A52,52 0 0 0 420,186 L220,186 A52,52 0 0 0 116,186 Z"
          fill="${color}" stroke="#0b0e12" stroke-width="2"/>
    <path d="M44,186 L44,150 C44,136 56,130 76,126 L130,118
             C162,76 202,62 250,60 L396,60 C446,62 488,84 518,112
             L566,122 C590,127 596,138 596,150 L596,186
             L524,186 A52,52 0 0 0 420,186 L220,186 A52,52 0 0 0 116,186 Z"
          fill="url(#${uid})"/>
    <path d="M158,116 L296,112 L296,72 L254,70 C216,73 184,90 158,116 Z" fill="#10151c"/>
    <path d="M312,112 L474,108 C450,84 420,71 390,70 L312,72 Z" fill="#10151c"/>
    <line x1="240" y1="56" x2="400" y2="56" stroke="#0b0e12" stroke-width="5" stroke-linecap="round"/>
    <line x1="305" y1="70" x2="305" y2="150" stroke="#0b0e12" stroke-width="2" opacity="0.5"/>
    <rect x="318" y="128" width="30" height="5" rx="2.5" fill="#0b0e12" opacity="0.6"/>
    <path d="M46,152 L84,146 L84,158 L46,160 Z" fill="#f2d6a0" opacity="0.95"/>
    <rect x="576" y="140" width="18" height="14" rx="3" fill="#b23838"/>
    <rect x="44" y="168" width="552" height="6" fill="#0b0e12" opacity="0.25"/>
    <g>
      <circle cx="168" cy="186" r="37" fill="#14181d" stroke="#2a3542" stroke-width="2"/>
      <circle cx="168" cy="186" r="20" fill="none" stroke="#8b939c" stroke-width="4"/>
      <circle cx="168" cy="186" r="6" fill="#566070"/>
    </g>
    <g>
      <circle cx="472" cy="186" r="37" fill="#14181d" stroke="#2a3542" stroke-width="2"/>
      <circle cx="472" cy="186" r="20" fill="none" stroke="#8b939c" stroke-width="4"/>
      <circle cx="472" cy="186" r="6" fill="#566070"/>
    </g>
  </svg>`;
}

/* ---------- โมเดล 3D ใช้ร่วมกันทุกหน้า (fallback เป็นภาพ SVG อัตโนมัติ) ---------- */

// material ที่เป็นสีตัวถัง — trim/caliper มีคำว่า paint แต่ห้ามเปลี่ยนสี
const PAINT_RE = /paint|body|carros|shell|exterior|main|primary/i;
const PAINT_SKIP_RE = /glass|window|tire|tyre|wheel|rim|light|chrome|interior|mirror|plate|trim|calliper|caliper/i;

// แปลงค่าสี sRGB → linear (glTF ต้องการค่า linear ไม่งั้นสีเพี้ยน/ซีด)
function srgbToLinear(c) {
  return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}

function hexToRgba(hex) {
  const n = parseInt(hex.slice(1), 16);
  return [
    srgbToLinear(((n >> 16) & 255) / 255),
    srgbToLinear(((n >> 8) & 255) / 255),
    srgbToLinear((n & 255) / 255),
    1,
  ];
}

// เปลี่ยนสีตัวถังของ <model-viewer> — คืนจำนวน material ที่เปลี่ยนได้
function recolorViewer(viewer, hex) {
  if (!viewer.model) return 0;
  const rgba = hexToRgba(hex);
  let hit = 0;
  for (const mat of viewer.model.materials) {
    // ห้ามให้ material เดียวพังทั้งลูป — บางไฟล์มี material ที่ inactive แล้ว throw
    try {
      if (!PAINT_RE.test(mat.name) || PAINT_SKIP_RE.test(mat.name)) continue;
      mat.pbrMetallicRoughness.setBaseColorFactor(rgba);
      hit++;
    } catch {
      /* material ใช้งานไม่ได้ — ข้ามไปตัวถัดไป */
    }
  }
  return hit;
}

// สร้างภาพรถ: แสดง SVG ทันทีเป็น placeholder แล้วอัปเกรดเป็นโมเดล 3D เมื่อพร้อม
function carVisual3D(carId, colorHex, opts = {}) {
  const { height = 210, controls = false } = opts;
  // shimmer-overlay = แสงวิ่งบอกว่ากำลังโหลดโมเดล 3D — ปลดออกเมื่อโหลดเสร็จ/ใช้ SVG แทน
  return `<div class="car-3d-wrap shimmer-overlay" data-car="${carId}" data-color="${colorHex}"
    data-height="${height}" data-controls="${controls ? "1" : "0"}"
    style="min-height:${height}px">${carSVG(colorHex)}</div>`;
}

// อัปเกรด placeholder ทุกตัวในหน้าเป็น <model-viewer> เมื่อไลบรารีโหลดเสร็จ
// (ช้าแค่ไหนก็รอได้ ไม่มี timeout — ถ้าไลบรารี/ไฟล์โมเดลพัง จะคง SVG ไว้)
function initCarVisuals(root = document) {
  if (!window.customElements) return; // เบราว์เซอร์เก่ามาก — ใช้ SVG ต่อไป
  customElements.whenDefined("model-viewer").then(() => {
    root.querySelectorAll(".car-3d-wrap").forEach((wrap) => {
      if (wrap.dataset.bound) return;
      wrap.dataset.bound = "1";
      const v = document.createElement("model-viewer");
      v.src = `/assets/models/${wrap.dataset.car}.glb`;
      v.alt = "โมเดล 3D";
      v.setAttribute("loading", "lazy");
      v.setAttribute("interaction-prompt", "none");
      v.setAttribute("shadow-intensity", "1");
      v.setAttribute("exposure", "1.05");
      v.setAttribute("auto-rotate", "");
      if (wrap.dataset.controls === "1") {
        v.setAttribute("camera-controls", "");
        v.setAttribute("disable-zoom", "");
      }
      v.style.cssText = `width:100%;height:${wrap.dataset.height}px;background:transparent`;
      // อ่านสีจาก dataset ตอนโหลดเสร็จ เพื่อให้สีที่ผู้ใช้เพิ่งเลือกถูกทาเสมอ
      v.addEventListener("load", () => {
        wrap.classList.remove("shimmer-overlay");
        recolorViewer(v, wrap.dataset.color);
      });
      v.addEventListener("error", () => {
        wrap.classList.remove("shimmer-overlay");
        wrap.innerHTML = carSVG(wrap.dataset.color);
      }, { once: true });
      wrap.replaceChildren(v);
    });
  });
}

/* ---------- ไอคอน SVG (ไม่ใช้ emoji ตามแนวทาง UI) ---------- */

const ICONS = {
  bell:
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>',
  check:
    '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#58b98b" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>',
  checkSmall:
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>',
  alert:
    '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#e06060" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
  // หัวใจของ "รายการที่สนใจ" — เส้นขอบเปล่าตอนยังไม่ติดตาม ส่วนตอนติดตามแล้ว CSS จะทาสีข้างในให้
  // (ใช้ SVG เส้นเดียวสองสถานะ จึงไม่ต้องสลับ markup ตอนกด — ปุ่มเดิมไม่ถูกสร้างใหม่ โฟกัสไม่หาย)
  heart:
    '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8l8.8 8.8 8.8-8.8a5.5 5.5 0 0 0 0-7.8z"/></svg>',
};

/* ---------- ตัวช่วยจัดรูปแบบ ---------- */

// ข้อความที่ผู้ใช้พิมพ์เอง (รีวิว ชื่อ หมายเหตุ) ต้อง escape ก่อนใส่ innerHTML เสมอ กัน XSS
function esc(value) {
  const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  return String(value ?? "").replace(/[&<>"']/g, (c) => map[c]);
}

// ดาวคะแนนรีวิว เช่น ★★★★☆ 4.2 (12)
function stars(avg, count) {
  if (!count) return '<span class="stars muted">ยังไม่มีรีวิว</span>';
  const full = Math.round(avg);
  return `<span class="stars" role="img" aria-label="คะแนน ${avg} จาก 5 (${count} รีวิว)">
    <span class="on">${"★".repeat(full)}</span><span class="off">${"★".repeat(5 - full)}</span>
    <b class="num">${Number(avg).toFixed(1)}</b><small>(${count})</small></span>`;
}

// ดาวของรีวิวรายการเดียว (ไม่มีตัวเลขเฉลี่ย)
function ratingStars(rating) {
  return `<span class="stars" role="img" aria-label="ให้คะแนน ${rating} จาก 5 ดาว"><span class="on">${"★".repeat(rating)}</span><span class="off">${"★".repeat(5 - rating)}</span></span>`;
}

// เติมชื่อ/เบอร์/อีเมลจากบัญชีที่ล็อกอินอยู่ลงฟอร์ม (ไม่ทับค่าที่ผู้ใช้พิมพ์ไว้แล้ว)
function prefillFromUser(map) {
  const user = typeof Auth !== "undefined" && Auth.user();
  if (!user) return;
  Object.entries(map).forEach(([inputId, key]) => {
    const input = document.getElementById(inputId);
    if (input && !input.value && user[key]) input.value = user[key];
  });
}

function baht(n) {
  return "฿" + Number(n).toLocaleString("th-TH");
}

function thaiDate(iso) {
  if (!iso) return "-";
  return new Date(`${iso}T00:00:00`).toLocaleDateString("th-TH", {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function stockBadge(stock) {
  if (stock === "in_stock") return '<span class="badge badge-ok">มีรถพร้อมส่งมอบ</span>';
  const weeks = String(stock).split("_")[1] || "?";
  return `<span class="badge badge-warn">รอผลิตประมาณ ${weeks} สัปดาห์</span>`;
}

// ยอดผ่อนต่อเดือนแบบดอกเบี้ยคงที่ (flat rate) — สูตรเดียวกับฝั่ง backend
function monthlyPayment(principal, flatRate, months) {
  const interestTotal = principal * (flatRate / 100) * (months / 12);
  return Math.round((principal + interestTotal) / months);
}

/* ---------- Toast ---------- */

// link = { href, text } เพิ่มลิงก์ต่อท้ายข้อความ (เช่น ชวนเข้าสู่ระบบ) — สร้างเป็น element
// ไม่ใช่ innerHTML เพราะข้อความอาจมีชื่อรุ่น/ข้อความจาก API ปนอยู่
function toast(message, type = "info", link = null) {
  const zone = document.getElementById("toast-zone");
  if (!zone) return;
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = message;
  if (link) {
    const a = document.createElement("a");
    a.href = link.href;
    a.textContent = link.text;
    a.className = "toast-link";
    el.append(" ", a);
  }
  // มีลิงก์ให้กดต้องอยู่นานพออ่านจบแล้วเอื้อมไปกด (4.2 วินาทีไม่พอ)
  setTimeout(() => el.remove(), link ? 10000 : 4200);
}

/* ---------- localStorage (เก็บ config รถ + รหัสจองของผู้ใช้) ---------- */

const Store = {
  save(key, value) {
    localStorage.setItem(`astra_${key}`, JSON.stringify(value));
  },
  load(key) {
    try {
      return JSON.parse(localStorage.getItem(`astra_${key}`));
    } catch {
      return null;
    }
  },
  remove(key) {
    localStorage.removeItem(`astra_${key}`);
  },
};

/* ---------- อ่านค่า query string ---------- */

function qs(name) {
  return new URLSearchParams(location.search).get(name);
}

/* ---------- รายการที่สนใจ (watchlist): ปุ่มหัวใจที่ใช้ร่วมกันทุกหน้า ----------
   เก็บรหัสที่ติดตามไว้ในหน่วยความจำของหน้า (Watch.ids) แล้วระบายสีปุ่มจากชุดนี้
   -> หน้าแรกมีการ์ดหลายใบแต่ถาม API แค่ครั้งเดียว และกดสลับแล้วไม่ต้องโหลดใหม่ทั้งหน้า */

const Watch = {
  ids: new Set(),
  // ยังไม่ล็อกอินก็ไม่ต้องยิง API (จะได้ 401 เปล่า ๆ แล้ว api.js จะล้าง token ทิ้ง)
  async load() {
    if (!Auth.isLoggedIn()) {
      Watch.ids = new Set();
      return Watch.ids;
    }
    try {
      Watch.ids = new Set(await API.watchlistIds());
    } catch {
      Watch.ids = new Set();   // โหลดไม่ได้ก็แค่ยังไม่ระบายสีหัวใจ หน้าเว็บต้องใช้งานต่อได้
    }
    return Watch.ids;
  },
  has(carId) {
    return Watch.ids.has(carId);
  },
};

// labelled = true: ปุ่มเต็มความกว้างมีข้อความ (หน้ารายละเอียดรุ่น)
// labelled = false: ปุ่มไอคอนบนการ์ด — ชื่อปุ่มมาจาก aria-label ที่บอกชื่อรุ่น
function watchButtonHTML(car, { labelled = false } = {}) {
  const on = Watch.has(car.id);
  const name = esc(car.name);
  const base = `type="button" class="watch-btn${labelled ? " labelled" : ""}" data-watch="${esc(car.id)}"
      data-watch-name="${name}" aria-pressed="${on}"`;
  // ข้อความที่เห็นต้องตรงกับชื่อที่สกรีนรีดเดอร์อ่าน (WCAG 2.5.3) จึงใช้ชื่อเดียวกันทั้งสองแบบ
  return labelled
    ? `<button ${base}>${ICONS.heart}<span class="txt">ติดตาม ${name}</span></button>`
    : `<button ${base} aria-label="ติดตาม ${name}" title="ติดตาม ${name}">${ICONS.heart}</button>`;
}

function paintWatchButtons() {
  document.querySelectorAll("[data-watch]").forEach((btn) => {
    btn.setAttribute("aria-pressed", String(Watch.has(btn.dataset.watch)));
  });
}

async function toggleWatch(btn, onChange) {
  const carId = btn.dataset.watch;
  const name = btn.dataset.watchName || "รุ่นนี้";
  if (!Auth.isLoggedIn()) {
    // ไม่เด้งหน้าทันที: ผู้ใช้กำลังดูรถอยู่ บอกก่อนแล้วให้เขาเลือกเองว่าจะไปล็อกอินไหม
    const next = encodeURIComponent(`${location.pathname}${location.search}`);
    toast(`เข้าสู่ระบบเพื่อเก็บ ${name} ไว้ในรายการที่สนใจ แล้วรับแจ้งเตือนเมื่อโปรโมชั่นใกล้หมด`, "info", {
      href: `/pages/login.html?next=${next}`,
      text: "เข้าสู่ระบบ",
    });
    return;
  }
  const on = btn.getAttribute("aria-pressed") === "true";
  btn.disabled = true;
  try {
    if (on) {
      await API.unwatchCar(carId);
      Watch.ids.delete(carId);
    } else {
      await API.watchCar(carId);
      Watch.ids.add(carId);
    }
    paintWatchButtons();
    // toast-zone เป็น aria-live="polite" อยู่แล้ว การเปลี่ยนสถานะจึงถูกประกาศให้สกรีนรีดเดอร์
    toast(
      on
        ? `เอา ${name} ออกจากรายการที่สนใจแล้ว`
        : `เพิ่ม ${name} ในรายการที่สนใจแล้ว — ระบบจะเตือนเมื่อโปรโมชั่นเหลือไม่เกิน 3 วัน`,
      "ok"
    );
    if (onChange) onChange(carId, !on);
  } catch (err) {
    toast(err.message, "error");
  } finally {
    btn.disabled = false;
  }
}

function bindWatchButtons(zone, onChange) {
  if (!zone) return;
  zone.querySelectorAll("[data-watch]").forEach((btn) =>
    btn.addEventListener("click", () => toggleWatch(btn, onChange))
  );
}

// ป้ายบอกสถานะโปรฯ ของรถที่ติดตาม (ข้อมูลมาจาก promo_status ฝั่ง backend)
function promoBadge(promo) {
  if (!promo) return '<span class="badge badge-bad">ไม่มีโปรโมชั่น</span>';
  if (!promo.active) return '<span class="badge badge-bad">โปรโมชั่นหมดอายุแล้ว</span>';
  const label = promo.days_left === 0 ? "โปรฯ หมดวันนี้" : `โปรฯ เหลือ ${promo.days_left} วัน`;
  return `<span class="badge ${promo.ending_soon ? "badge-warn" : "badge-accent"}">${label}</span>`;
}

/* ---------- รีวิว: การ์ด + ฟอร์ม (ใช้ร่วมกันหน้าแรก / รายละเอียดรุ่น / หลังการขาย) ---------- */

function reviewCardHTML(r, { showCar = true, onDelete = false } = {}) {
  return `
    <article class="card review-card">
      <div class="head">
        ${ratingStars(r.rating)}
        ${r.verified ? '<span class="badge badge-ok">ผ่านการใช้งานจริง</span>' : ""}
      </div>
      <h3>${esc(r.title)}</h3>
      <p>${esc(r.comment)}</p>
      <p class="by">
        <span>${esc(r.author)}</span>
        ${showCar ? `·<a href="/pages/model.html?id=${r.car.id}">${esc(r.car.name)}</a>` : ""}
        ·<span>${new Date(r.created_at).toLocaleDateString("th-TH", { day: "numeric", month: "short", year: "numeric" })}</span>
        ${onDelete ? `<button type="button" class="link-btn" data-del-review="${r.id}">ลบรีวิว</button>` : ""}
      </p>
    </article>`;
}

function reviewFormHTML(cars, selectedId) {
  const carField =
    cars.length > 1
      ? `<div class="field"><label for="rv-car">รุ่นที่ต้องการรีวิว</label>
           <select id="rv-car">${cars
             .map((c) => `<option value="${c.id}" ${c.id === selectedId ? "selected" : ""}>${esc(c.name)}</option>`)
             .join("")}</select></div>`
      : `<input type="hidden" id="rv-car" value="${cars[0].id}">`;
  return `
    <form id="rv-form" novalidate>
      <h3 class="mb-2">เขียนรีวิว <span class="badge badge-accent">+200 คะแนน</span></h3>
      ${carField}
      <div class="field">
        <!-- ไม่ใช่ <label> เพราะ label ต้องชี้ไปที่ control เดียว — กลุ่มดาวใช้ aria-labelledby แทน -->
        <p class="field-label" id="rv-stars-label">ให้คะแนน</p>
        <div class="star-input" id="rv-stars" role="radiogroup" aria-labelledby="rv-stars-label">
          ${[1, 2, 3, 4, 5]
            .map(
              (n) =>
                `<button type="button" data-n="${n}" role="radio" aria-checked="false"
                         tabindex="${n === 1 ? 0 : -1}" aria-label="${n} ดาว">★</button>`
            )
            .join("")}
        </div>
      </div>
      <div class="field">
        <label for="rv-title">หัวข้อรีวิว</label>
        <input type="text" id="rv-title" maxlength="80" placeholder="เช่น แรงแต่ขับในเมืองได้สบาย">
        <span class="error" id="err-rv-title">หัวข้ออย่างน้อย 2 ตัวอักษร</span>
      </div>
      <div class="field">
        <label for="rv-comment">รายละเอียด</label>
        <textarea id="rv-comment" maxlength="1000"
          placeholder="เล่าประสบการณ์ทดลองขับหรือการใช้งานจริง ช่วยให้คนที่กำลังตัดสินใจ"></textarea>
        <span class="error" id="err-rv-comment">รายละเอียดอย่างน้อย 10 ตัวอักษร</span>
      </div>
      <button class="btn btn-primary btn-block" id="rv-submit" type="submit">ส่งรีวิว</button>
    </form>`;
}

function bindReviewForm(onDone) {
  let rating = 0;
  const starZone = document.getElementById("rv-stars");
  const buttons = [...starZone.querySelectorAll("button")];
  // radiogroup: มีดาวเดียวที่อยู่ในลำดับ Tab — ถ้ายังไม่เลือกให้เป็นดาวแรก
  const paint = () =>
    buttons.forEach((b) => {
      const n = Number(b.dataset.n);
      b.classList.toggle("on", n <= rating);
      b.setAttribute("aria-checked", String(n === rating));
      b.tabIndex = n === (rating || 1) ? 0 : -1;
    });
  const pick = (n, moveFocus) => {
    rating = n;
    paint();
    if (moveFocus) buttons[n - 1].focus();
  };
  buttons.forEach((b) =>
    b.addEventListener("click", () => pick(Number(b.dataset.n)))
  );
  // ลูกศรซ้าย/ขวาเลื่อนคะแนน, Home/End ไปต่ำสุด/สูงสุด (Enter/Space ใช้ได้เองเพราะเป็น <button>)
  starZone.addEventListener("keydown", (e) => {
    const cur = rating || 1;
    let next = null;
    if (e.key === "ArrowRight" || e.key === "ArrowUp") next = Math.min(5, cur + 1);
    else if (e.key === "ArrowLeft" || e.key === "ArrowDown") next = Math.max(1, cur - 1);
    else if (e.key === "Home") next = 1;
    else if (e.key === "End") next = 5;
    if (!next) return;
    e.preventDefault();
    pick(next, true);
  });

  document.getElementById("rv-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const title = document.getElementById("rv-title").value.trim();
    const comment = document.getElementById("rv-comment").value.trim();
    setFieldInvalid("rv-title", title.length < 2);
    setFieldInvalid("rv-comment", comment.length < 10);
    if (!rating) return toast("กรุณาให้คะแนนดาวก่อนส่งรีวิว", "error");
    if (title.length < 2 || comment.length < 10) return;

    const btn = document.getElementById("rv-submit");
    btn.disabled = true;
    btn.textContent = "กำลังส่ง…";
    try {
      const review = await API.createReview({
        car_id: document.getElementById("rv-car").value, rating, title, comment,
      });
      toast("ขอบคุณสำหรับรีวิว — ได้รับ 200 คะแนน", "ok");
      onDone(review);
    } catch (err) {
      toast(err.message, "error");
      btn.disabled = false;
      btn.textContent = "ส่งรีวิว";
    }
  });
}
