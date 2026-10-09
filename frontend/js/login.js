// หน้าเข้าสู่ระบบ — เรียก POST /api/login แล้วเก็บ token ไว้ใช้กับ endpoint อื่น
"use strict";

renderHeader("login");
renderFooter();

// setFieldInvalid (ui.js) ผูก aria-invalid + aria-describedby ให้ด้วย ไม่ให้เหลือแค่สีแดง
const setInvalid = setFieldInvalid;

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

// กรอกช่องที่เว้นไว้แล้วสีแดงหายทันที ไม่ต้องรอกดเข้าสู่ระบบอีกรอบ
bindLiveClear({
  "li-username": (v) => !v.trim(),
  "li-password": (v) => !v,
});

async function submit(event) {
  event.preventDefault();

  const username = document.getElementById("li-username").value.trim();
  const password = document.getElementById("li-password").value;
  setInvalid("li-username", !username);
  setInvalid("li-password", !password);
  if (focusFirstInvalid()) return;

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
    // 429 = ยิงถี่เกิน (กันเดารหัสผ่าน) ไม่ใช่รหัสผ่านผิด จึงไม่ทาแดงช่องรหัสผ่าน
    // และไม่ล้างค่าที่ผู้ใช้พิมพ์ไว้ทั้งสองช่อง เพื่อให้กดลองใหม่ได้เลยเมื่อครบเวลา
    if (err.status === 429) {
      toast(retryMessage(err), "error");
    } else {
      toast(err.message, "error");
      setInvalid("li-password", true);
    }
    btn.disabled = false;
    btn.textContent = "เข้าสู่ระบบ";
  }
}

document.getElementById("login-form").addEventListener("submit", submit);
