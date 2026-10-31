// ที่อยู่ของ API — แก้ไฟล์นี้ไฟล์เดียวเวลาเอาหน้าเว็บไปวางคนละที่กับ backend
"use strict";

// ค่าว่าง = หน้าเว็บกับ API อยู่โดเมนเดียวกัน (ตอนรัน docker compose หรือ deploy ขึ้น Render)
// ถ้าลากหน้าเว็บขึ้นโฮสต์ FTP แล้ว backend อยู่อีกที่ ให้ใส่ URL ของ backend ลงไป
// เช่น  window.API_BASE = "https://astra-motors-xxxx.onrender.com";
// ห้ามมี / ปิดท้าย และต้องเป็น https ถ้าหน้าเว็บเปิดด้วย https (เบราว์เซอร์บล็อก mixed content)
window.API_BASE = "";

// ต่อ API_BASE เข้ากับ path ของ API ให้ทุกไฟล์ใช้ร่วมกัน (api.js และสตรีมแจ้งเตือนใน ui.js)
window.apiUrl = function apiUrl(path) {
  const base = (window.API_BASE || "").replace(/\/+$/, "");
  return base + path;
};
