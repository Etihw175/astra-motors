// หน้าเข้าสู่ระบบ — เรียก POST /api/login แล้วเก็บ token ไว้ใช้กับ endpoint อื่น
"use strict";

renderHeader("login");
renderFooter();

function setInvalid(id, invalid) {
  document.getElementById(id).closest(".field").classList.toggle("invalid", invalid);
}

// ล็อกอินอยู่แล้วไม่ต้องกรอกซ้ำ — ส่งไปหน้าโปรไฟล์เลย
if (Auth.isLoggedIn()) {
  location.replace(qs("next") || "/pages/profile.html");
}

// ปุ่ม "ใช้บัญชีนี้" ในกล่องบัญชีตัวอย่าง (ช่วยตอนสาธิตหน้าห้อง)
document.querySelectorAll("[data-fill]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const [username, password] = btn.dataset.fill.split("|");
    document.getElementById("li-username").value = username;
    document.getElementById("li-password").value = password;
    document.getElementById("li-submit").focus();
  });
});

async function submit(event) {
  event.preventDefault();

  const username = document.getElementById("li-username").value.trim();
  const password = document.getElementById("li-password").value;
  setInvalid("li-username", !username);
  setInvalid("li-password", !password);
  if (document.querySelector(".field.invalid")) return;

  const btn = document.getElementById("li-submit");
  btn.disabled = true;
  btn.textContent = "กำลังเข้าสู่ระบบ...";

  try {
    const data = await API.login({ username, password });
    Auth.set(data.access_token);
    Auth.saveUser(data.user);
    toast(`ยินดีต้อนรับ ${data.user.full_name}`, "ok");
    setTimeout(() => (location.href = qs("next") || "/pages/profile.html"), 500);
  } catch (err) {
    toast(err.message, "error");
    setInvalid("li-password", true);
    btn.disabled = false;
    btn.textContent = "เข้าสู่ระบบ";
  }
}

document.getElementById("login-form").addEventListener("submit", submit);
