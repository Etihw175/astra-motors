// หน้าสมัครสมาชิก — เช็ค username ว่างแบบ real-time แล้วเรียก POST /api/register
"use strict";

renderHeader("register");
renderFooter();

if (Auth.isLoggedIn()) location.replace("/pages/profile.html");

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
let usernameAvailable = false;

// setFieldInvalid (ui.js) ผูก aria-invalid + aria-describedby ให้ด้วย ไม่ให้เหลือแค่สีแดง
const setInvalid = setFieldInvalid;

function passwordOk(value) {
  return value.length >= 8 && /[A-Za-z]/.test(value) && /\d/.test(value);
}

/* ---------- ตรวจ username ว่างไหม (debounce กันยิง API ทุกตัวอักษร) ---------- */

const nameInput = document.getElementById("rg-username");
const nameState = document.getElementById("rg-username-state");
let nameTimer = null;

nameInput.addEventListener("input", () => {
  usernameAvailable = false;
  clearTimeout(nameTimer);
  const value = nameInput.value.trim();

  if (!value) {
    nameState.className = "name-state";
    nameState.textContent = "";
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
    nameState.className = `name-state ${result.available ? "ok" : "bad"}`;
    nameState.textContent = result.available
      ? `ใช้ชื่อ "${value}" ได้`
      : result.reason;
    setInvalid("rg-username", !result.available);
  } catch {
    nameState.className = "name-state busy";
    nameState.textContent = "ตรวจสอบไม่ได้ในตอนนี้ ระบบจะตรวจอีกครั้งตอนกดสมัคร";
  }
}

/* ---------- ส่งฟอร์ม ---------- */

async function submit(event) {
  event.preventDefault();

  const username = nameInput.value.trim();
  const fullName = document.getElementById("rg-fullname").value.trim();
  const email = document.getElementById("rg-email").value.trim();
  const phone = document.getElementById("rg-phone").value.trim();
  const password = document.getElementById("rg-password").value;
  const password2 = document.getElementById("rg-password2").value;

  setInvalid("rg-username", !usernameAvailable);
  setInvalid("rg-fullname", fullName.length < 2);
  setInvalid("rg-email", !EMAIL_RE.test(email));
  setInvalid("rg-phone", phone.replace(/\D/g, "").length < 9);
  setInvalid("rg-password", !passwordOk(password));
  setInvalid("rg-password2", password !== password2 || !password2);
  if (document.querySelector(".field.invalid")) return;

  if (!document.getElementById("rg-consent").checked) {
    return toast("กรุณายินยอมเงื่อนไขการใช้ข้อมูลส่วนบุคคล (PDPA) ก่อนสมัคร", "error");
  }

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
    toast(err.message, "error");
    if (err.message.includes("username")) setInvalid("rg-username", true);
    if (err.message.includes("อีเมล")) setInvalid("rg-email", true);
    btn.disabled = false;
    btn.textContent = "สมัครสมาชิก";
  }
}

document.getElementById("register-form").addEventListener("submit", submit);
