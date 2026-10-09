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
  // ส่งไฟล์ (FormData) ต้องให้เบราว์เซอร์ตั้ง Content-Type + boundary เอง
  const isForm = options.body instanceof FormData;
  const headers = { ...(isForm ? {} : { "Content-Type": "application/json" }), ...(options.headers || {}) };
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
    const err = new Error(
      typeof detail === "string" ? detail : "เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง"
    );
    err.status = res.status;
    // 422 ส่ง fields: [{field, label, message}] มาด้วย — หน้าเว็บเอาไปทาสีแดงช่องที่ผิดได้ตรงช่อง
    if (data && Array.isArray(data.fields)) err.fields = data.fields;
    // 429 (ยิงถี่เกิน) บอกด้วยว่าให้รออีกกี่วินาที
    if (res.status === 429) err.retryAfter = Number(res.headers.get("Retry-After")) || null;
    throw err;
  }
  return data;
}

// ตัด key ที่ไม่มีค่าออก แล้วแปลงเป็น query string
function _query(params = {}) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") q.set(k, v);
  });
  const text = q.toString();
  return text ? `?${text}` : "";
}

const API = {
  /* ---------- แคตตาล็อก (รับรู้ / ค้นหา / รายละเอียด) ---------- */
  cars: (filters) => _api(`/api/cars${_query(filters)}`),
  carFacets: () => _api("/api/cars/facets"),
  car: (id) => _api(`/api/cars/${encodeURIComponent(id)}`),
  promotions: () => _api("/api/promotions"),
  showrooms: () => _api("/api/showrooms"),
  slots: (id, date) =>
    _api(`/api/showrooms/${encodeURIComponent(id)}/slots?date=${encodeURIComponent(date)}`),
  financePlans: () => _api("/api/finance/plans"),
  createTestdrive: (body) =>
    _api("/api/testdrives", { method: "POST", body: JSON.stringify(body) }),
  cancelTestdrive: (code) =>
    _api(`/api/testdrives/${encodeURIComponent(code)}/cancel`, { method: "POST" }),
  myBookings: () => _api("/api/me/bookings"),
  // เส้นทาง legacy ที่ออกใบจองทันที — หน้าเว็บใช้ชุด payment* ด้านล่างแทน (จ่ายก่อนจึงออกใบจอง)
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
  /* ---------- ชำระเงินจอง (จำลอง): payment intent → QR/บัตร → ยืนยัน → ออกใบจอง ---------- */
  createPayment: (body) => _api("/api/payments", { method: "POST", body: JSON.stringify(body) }),
  payment: (id) => _api(`/api/payments/${encodeURIComponent(id)}`),
  // ของจริงเป็น webhook จาก payment gateway — ที่นี่เปิดให้กดจำลองเพื่อเดโมให้ครบวงจร
  confirmPayment: (id) => _api(`/api/payments/${encodeURIComponent(id)}/confirm`, { method: "POST" }),
  cancelPayment: (id) => _api(`/api/payments/${encodeURIComponent(id)}/cancel`, { method: "POST" }),

  createLoan: (body) => _api("/api/loans", { method: "POST", body: JSON.stringify(body) }),
  loan: (id) => _api(`/api/loans/${encodeURIComponent(id)}`),
  uploadDocument: (file, kind) => {
    const form = new FormData();
    form.append("file", file);
    form.append("kind", kind);
    return _api("/api/documents", { method: "POST", body: form });
  },

  /* ---------- รายการที่สนใจ (watchlist) — ต้องล็อกอิน ---------- */
  watchlist: () => _api("/api/watchlist"),
  // ขอแค่รหัสรถในคิวรีเดียว ไว้ระบายสีปุ่มหัวใจบนการ์ดทุกใบในหน้าแรก
  watchlistIds: () => _api("/api/watchlist/ids"),
  watchCar: (carId) => _api("/api/watchlist", { method: "POST", body: JSON.stringify({ car_id: carId }) }),
  unwatchCar: (carId) => _api(`/api/watchlist/${encodeURIComponent(carId)}`, { method: "DELETE" }),

  /* ---------- แจ้งเตือน (ติดตามสถานะ) ---------- */
  notifications: (limit = 15) => _api(`/api/notifications?limit=${limit}`),
  unreadCount: () => _api("/api/notifications/unread-count"),
  // ตั๋วอายุสั้นสำหรับเปิดสตรีม SSE (EventSource แนบ header Authorization เองไม่ได้)
  streamTicket: () => _api("/api/notifications/stream-ticket", { method: "POST" }),
  readNotification: (id) => _api(`/api/notifications/${id}/read`, { method: "POST" }),
  readAllNotifications: () => _api("/api/notifications/read-all", { method: "POST" }),

  /* ---------- หลังการขาย: รีวิว / ศูนย์บริการ / คะแนนสะสม ---------- */
  reviews: (carId, limit = 20) => _api(`/api/reviews${_query({ car_id: carId, limit })}`),
  myReviews: () => _api("/api/reviews/mine"),
  createReview: (body) => _api("/api/reviews", { method: "POST", body: JSON.stringify(body) }),
  deleteReview: (id) => _api(`/api/reviews/${id}`, { method: "DELETE" }),
  serviceTypes: () => _api("/api/service/types"),
  serviceSlots: (showroomId, date) => _api(`/api/service/slots${_query({ showroom_id: showroomId, date })}`),
  createService: (body) =>
    _api("/api/service/appointments", { method: "POST", body: JSON.stringify(body) }),
  myServices: () => _api("/api/service/appointments"),
  cancelService: (code) =>
    _api(`/api/service/appointments/${encodeURIComponent(code)}/cancel`, { method: "POST" }),
  loyalty: () => _api("/api/loyalty"),
  redeem: (rewardId) =>
    _api("/api/loyalty/redeem", { method: "POST", body: JSON.stringify({ reward_id: rewardId }) }),

  /* ---------- จำลองการใช้งานบนถนนไทย ---------- */
  simulationConditions: () => _api("/api/simulation/conditions"),
  simulate: (body) => _api("/api/simulation", { method: "POST", body: JSON.stringify(body) }),

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

  /* ---------- หลังบ้านพนักงานโชว์รูม (เฉพาะ admin — เรียกจาก /pages/admin.html) ---------- */
  adminOverview: () => _api("/api/admin/overview"),
  adminTestdrives: (filters) => _api(`/api/admin/testdrives${_query(filters)}`),
  adminReservations: (filters) => _api(`/api/admin/reservations${_query(filters)}`),
  adminLoans: (filters) => _api(`/api/admin/loans${_query(filters)}`),
  adminServices: (filters) => _api(`/api/admin/service-appointments${_query(filters)}`),
  adminCompleteTestdrive: (code, outcome = "completed") =>
    _api(`/api/admin/testdrives/${encodeURIComponent(code)}/complete${_query({ outcome })}`, {
      method: "POST",
    }),
  adminCompleteService: (code) =>
    _api(`/api/admin/service-appointments/${encodeURIComponent(code)}/complete`, { method: "POST" }),
};
