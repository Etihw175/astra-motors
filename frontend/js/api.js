// ชั้นเรียก API — ทุกหน้าใช้ผ่านอ็อบเจกต์ API นี้เท่านั้น (จะได้แก้ที่เดียวตอนเชื่อม backend จริง)
"use strict";

async function _api(path, options = {}) {
  let res;
  try {
    res = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw new Error("เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ กรุณาตรวจสอบอินเทอร์เน็ตแล้วลองใหม่");
  }
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = data && data.detail;
    throw new Error(
      typeof detail === "string" ? detail : "เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง"
    );
  }
  return data;
}

const API = {
  cars: () => _api("/api/cars"),
  car: (id) => _api(`/api/cars/${encodeURIComponent(id)}`),
  showrooms: () => _api("/api/showrooms"),
  slots: (id, date) =>
    _api(`/api/showrooms/${encodeURIComponent(id)}/slots?date=${encodeURIComponent(date)}`),
  financePlans: () => _api("/api/finance/plans"),
  createTestdrive: (body) =>
    _api("/api/testdrives", { method: "POST", body: JSON.stringify(body) }),
  createReservation: (body) =>
    _api("/api/reservations", { method: "POST", body: JSON.stringify(body) }),
  reservation: (code) => _api(`/api/reservations/${encodeURIComponent(code)}`),
  cancelReservation: (code) =>
    _api(`/api/reservations/${encodeURIComponent(code)}/cancel`, { method: "POST" }),
  scheduleDelivery: (code, date) =>
    _api(`/api/reservations/${encodeURIComponent(code)}/delivery`, {
      method: "POST",
      body: JSON.stringify({ date }),
    }),
  createLoan: (body) => _api("/api/loans", { method: "POST", body: JSON.stringify(body) }),
  loan: (id) => _api(`/api/loans/${encodeURIComponent(id)}`),
};
