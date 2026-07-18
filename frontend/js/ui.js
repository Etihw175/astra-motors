// ส่วนกลางของทุกหน้า: header/footer, รูปรถ SVG, ตัวช่วยจัดรูปแบบ, toast, localStorage
"use strict";

/* ---------- Header / Footer ---------- */

const NAV_ITEMS = [
  { key: "home", label: "หน้าแรก", href: "/" },
  { key: "compare", label: "เปรียบเทียบรุ่น", href: "/pages/compare.html" },
  { key: "finance", label: "คำนวณไฟแนนซ์", href: "/pages/finance.html" },
  { key: "testdrive", label: "จองทดลองขับ", href: "/pages/test-drive.html" },
  { key: "status", label: "การจองของฉัน", href: "/pages/status.html" },
];

function renderHeader(activeKey) {
  const nav = NAV_ITEMS.map(
    (i) =>
      `<a href="${i.href}" ${i.key === activeKey ? 'class="active" aria-current="page"' : ""}>${i.label}</a>`
  ).join("");
  document.body.insertAdjacentHTML(
    "afterbegin",
    `<header class="site-header">
       <div class="container bar">
         <a class="brand" href="/">ASTRA<span class="tick">/</span>MOTORS</a>
         <nav class="site-nav" aria-label="เมนูหลัก">${nav}</nav>
       </div>
     </header>`
  );
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
     <div class="toast-zone" id="toast-zone" aria-live="polite"></div>`
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

/* ---------- ไอคอน SVG (ไม่ใช้ emoji ตามแนวทาง UI) ---------- */

const ICONS = {
  check:
    '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#58b98b" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>',
  alert:
    '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#e06060" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
};

/* ---------- ตัวช่วยจัดรูปแบบ ---------- */

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

function toast(message, type = "info") {
  const zone = document.getElementById("toast-zone");
  if (!zone) return;
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = message;
  zone.appendChild(el);
  setTimeout(() => el.remove(), 4200);
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
