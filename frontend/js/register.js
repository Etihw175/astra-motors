// หน้าสมัครสมาชิก — เช็ค username ว่างแบบ real-time แล้วเรียก POST /api/register
"use strict";

renderHeader("register");
renderFooter();

if (Auth.isLoggedIn()) location.replace("/pages/profile.html");

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
// กฎเดียวกับ USERNAME_RE ฝั่ง backend (a-z A-Z 0-9 _ . ยาว 4-20) — ตัวพิมพ์ใหญ่ใช้ได้
const USERNAME_RE = /^[a-zA-Z0-9_.]{4,20}$/;
let usernameAvailable = false;
let usernameReason = null;    // เหตุผลจาก backend ครั้งล่าสุด (null = ยังไม่ได้คำตอบ)

// setFieldInvalid (ui.js) ผูก aria-invalid + aria-describedby ให้ด้วย ไม่ให้เหลือแค่สีแดง
const setInvalid = setFieldInvalid;

function passwordOk(value) {
  return value.length >= 8 && /[A-Za-z]/.test(value) && /\d/.test(value);
}

// บอกสาเหตุจริงของ username ที่ใช้ไม่ได้ (คืน null = รูปแบบผ่าน)
// ของเดิมขึ้นข้อความรวม "ต้องยาว 4-20 ตัวอักษร และยังไม่มีคนใช้" ซึ่งชี้ผิดจุด
// เช่น "QA5 User" ยาว 8 ตัวและยังไม่มีคนใช้ ปัญหาจริงคือมีช่องว่างอยู่ข้างใน
function usernameProblem(value) {
  if (!value) return "กรุณากรอก username";
  if (/\s/.test(value)) return "username ห้ามมีช่องว่าง — ใช้ _ หรือ . คั่นแทนได้";
  if (value.length < 4) return `username สั้นเกินไป (${value.length} ตัว) ต้องยาวอย่างน้อย 4 ตัวอักษร`;
  if (value.length > 20) return `username ยาวเกินไป (${value.length} ตัว) ได้ไม่เกิน 20 ตัวอักษร`;
  if (!USERNAME_RE.test(value)) {
    const bad = [...new Set(value.replace(/[a-zA-Z0-9_.]/g, "").split(""))].join(" ");
    return `username ใช้ได้เฉพาะ a-z, A-Z, 0-9, _ และ . — ตัวที่ใช้ไม่ได้: ${bad}`;
  }
  return null;
}

/* ---------- ตรวจ username ว่างไหม (debounce กันยิง API ทุกตัวอักษร) ---------- */

const nameInput = document.getElementById("rg-username");
const nameState = document.getElementById("rg-username-state");
let nameTimer = null;

nameInput.addEventListener("input", () => {
  usernameAvailable = false;
  usernameReason = null;
  clearTimeout(nameTimer);
  const value = nameInput.value.trim();

  if (!value) {
    nameState.className = "name-state";
    nameState.textContent = "";
    return;
  }
  // รูปแบบผิดอยู่แล้วไม่ต้องยิง API — บอกสาเหตุได้ทันทีตรงจุด
  const problem = usernameProblem(value);
  if (problem) {
    nameState.className = "name-state bad";
    nameState.textContent = problem;
    setFieldError("rg-username", problem);
    return;
  }
  nameState.className = "name-state busy";
  nameState.textContent = "กำลังตรวจสอบ...";
  nameTimer = setTimeout(() => checkName(value), 400);
});

async function checkName(value) {
  try {
    const result = await API.checkUsername(value);
    if (nameInput.value.trim() !== value) return;   // ผู้ใช้พิมพ์ต่อไปแล้ว ทิ้งผลเก่า
    usernameAvailable = result.available;
    usernameReason = result.reason;
    nameState.className = `name-state ${result.available ? "ok" : "bad"}`;
    nameState.textContent = result.available
      ? `ใช้ชื่อ "${value}" ได้`
      : result.reason;
    if (result.available) {
      setInvalid("rg-username", false);
    } else {
      setFieldError("rg-username", result.reason || "username นี้ใช้ไม่ได้");
      setInvalid("rg-username", true);
    }
  } catch {
    nameState.className = "name-state busy";
    nameState.textContent = "ตรวจสอบไม่ได้ในตอนนี้ ระบบจะตรวจอีกครั้งตอนกดสมัคร";
  }
}

/* ---------- ล้างสีแดงทันทีที่แก้ให้ถูก (ของเดิม validate แค่ตอนกดสมัคร) ---------- */

bindLiveClear({
  // username ปล่อยให้ checkName/usernameProblem จัดการ เพราะต้องถาม backend ว่าชื่อว่างไหม
  "rg-fullname": (v) => v.trim().length < 2,
  "rg-email": (v) => !EMAIL_RE.test(v.trim()),
  "rg-phone": (v) => !phoneOk(v),
  "rg-password": (v) => !passwordOk(v),
  "rg-password2": (v) => !v || v !== document.getElementById("rg-password").value,
});
// พิมพ์รหัสผ่านช่องแรกแก้แล้ว ช่องยืนยันที่ "ตรงกันแล้ว" ต้องหายแดงด้วย
document.getElementById("rg-password").addEventListener("input", () => {
  const p2 = document.getElementById("rg-password2");
  if (p2.value && p2.value === document.getElementById("rg-password").value) {
    setInvalid("rg-password2", false);
  }
});
bindConsentClear("rg-consent");

/* ---------- ส่งฟอร์ม ---------- */

async function submit(event) {
  event.preventDefault();

  const username = nameInput.value.trim();
  const fullName = document.getElementById("rg-fullname").value.trim();
  const email = document.getElementById("rg-email").value.trim();
  const phone = document.getElementById("rg-phone").value.trim();
  const password = document.getElementById("rg-password").value;
  const password2 = document.getElementById("rg-password2").value;

  // username: บอกสาเหตุจริง (รูปแบบผิด / ยังตรวจไม่เสร็จ / ถูกใช้แล้ว) ไม่ใช่ข้อความรวมอันเดียว
  const nameProblem = usernameProblem(username);
  if (nameProblem) setFieldError("rg-username", nameProblem);
  else if (!usernameAvailable) {
    // รูปแบบถูกแต่ยังไม่ว่าง หรือยังไม่ได้คำตอบจาก backend — แยกสองกรณีให้ชัด
    setFieldError("rg-username", usernameReason || "ยังตรวจสอบชื่อนี้ไม่เสร็จ กรุณารอครู่แล้วกดสมัครอีกครั้ง");
  }
  setInvalid("rg-username", Boolean(nameProblem) || !usernameAvailable);
  setInvalid("rg-fullname", fullName.length < 2);
  setInvalid("rg-email", !EMAIL_RE.test(email));
  setInvalid("rg-phone", !phoneOk(phone));
  setInvalid("rg-password", !passwordOk(password));
  setInvalid("rg-password2", password !== password2 || !password2);
  // ไม่ติ๊กยินยอมก็เป็นข้อผิดพลาดของฟอร์มเหมือนช่องอื่น — ขึ้นข้อความตรงใต้ช่องนั้น
  setInvalid("rg-consent", !document.getElementById("rg-consent").checked);
  if (focusFirstInvalid()) return;

  const btn = document.getElementById("rg-submit");
  btn.disabled = true;
  btn.textContent = "กำลังสมัคร...";

  try {
    // สมัครสำเร็จ backend คืน token มาให้เลย ผู้ใช้จึงไม่ต้องล็อกอินซ้ำ
    const data = await API.register({
      username,
      password,
      full_name: fullName,
      email,
      phone,
    });
    Auth.set(data.access_token);
    Auth.saveUser(data.user);
    toast("สมัครสมาชิกสำเร็จ ยินดีต้อนรับสู่ ASTRA Motors", "ok");
    setTimeout(() => (location.href = "/pages/profile.html"), 700);
  } catch (err) {
    // 429 = ยิงถี่เกิน — ข้อความบอกเวลาที่ต้องรอ และค่าที่กรอกไว้ยังอยู่ครบ
    toast(err.status === 429 ? retryMessage(err) : err.message, "error");
    // 422 ชี้ช่องที่ผิดมาให้แล้ว (422 = ข้อมูลไม่ผ่านกฎฝั่งเซิร์ฟเวอร์) — ทาสีแดงตรงช่องนั้น
    applyServerFieldErrors(err, {
      username: "rg-username", full_name: "rg-fullname", email: "rg-email",
      phone: "rg-phone", password: "rg-password",
    });
    if (err.message.includes("username")) {
      setFieldError("rg-username", err.message);
      setInvalid("rg-username", true);
    }
    if (err.message.includes("อีเมล")) setInvalid("rg-email", true);
    btn.disabled = false;
    btn.textContent = "สมัครสมาชิก";
  }
}

document.getElementById("register-form").addEventListener("submit", submit);
