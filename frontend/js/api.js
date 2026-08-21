// ชั้นเรียก API — ทุกหน้าใช้ผ่านอ็อบเจกต์ API นี้เท่านั้น (จะได้แก้ที่เดียวตอนเชื่อม backend จริง)
"use strict";

// เก็บ token ที่ได้จาก /api/login ไว้ใน localStorage แล้วแนบไปกับทุก request อัตโนมัติ
const Auth = {
  KEY: "astra_token",
  token() {
    return localStorage.getItem(Auth.KEY) || null;
  },
  set(token) {
    localStorage.setItem(Auth.KEY, token);
  },
  clear() {
    localStorage.removeItem(Auth.KEY);
    localStorage.removeItem("astra_user");
  },
  saveUser(user) {
    localStorage.setItem("astra_user", JSON.stringify(user));
  },
  user() {
    try {
      return JSON.parse(localStorage.getItem("astra_user"));
    } catch {
      return null;
    }
  },
  isLoggedIn() {
    return Boolean(Auth.token());
  },
};

async function _api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  const token = Auth.token();
  if (token) headers.Authorization = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(path, { ...options, headers });
  } catch {
    throw new Error("เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ กรุณาตรวจสอบอินเทอร์เน็ตแล้วลองใหม่");
  }
  if (res.status === 204) return null;   // ลบสำเร็จ ไม่มีเนื้อหาตอบกลับ
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    // token หมดอายุ/ถูกยกเลิก -> ล้างทิ้งเพื่อให้หน้าเว็บกลับไปสถานะยังไม่ล็อกอิน
    if (res.status === 401) Auth.clear();
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

  /* ---------- ระบบสมาชิก (Authentication) ---------- */
  register: (body) => _api("/api/register", { method: "POST", body: JSON.stringify(body) }),
  login: (body) => _api("/api/login", { method: "POST", body: JSON.stringify(body) }),
  logout: () => _api("/api/logout", { method: "POST" }),
  changePassword: (body) =>
    _api("/api/change-password", { method: "POST", body: JSON.stringify(body) }),

  /* ---------- จัดการข้อมูลผู้ใช้ (User Management) ---------- */
  me: () => _api("/api/me"),
  users: ({ page = 1, perPage = 10, q = "", role = "" } = {}) => {
    const params = new URLSearchParams({ page, per_page: perPage });
    if (q) params.set("q", q);
    if (role) params.set("role", role);
    return _api(`/api/users?${params}`);
  },
  user: (id) => _api(`/api/users/${encodeURIComponent(id)}`),
  updateUser: (id, body) =>
    _api(`/api/users/${encodeURIComponent(id)}`, { method: "PUT", body: JSON.stringify(body) }),
  deleteUser: (id) => _api(`/api/users/${encodeURIComponent(id)}`, { method: "DELETE" }),
  checkUsername: (name) => _api(`/api/check-username/${encodeURIComponent(name)}`),
};
