// หน้าบัญชีของฉัน — ใช้ REST API ครบชุด: GET /api/me, PUT /api/users/{id},
// POST /api/change-password และ GET /api/users (แบบแบ่งหน้า สำหรับ admin)
"use strict";

renderHeader("profile");
renderFooter();

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const ROLE_LABEL = { admin: "ผู้ดูแลระบบ (admin)", customer: "สมาชิก (customer)" };

let me = null;
const usersView = { page: 1, perPage: 5, q: "", role: "" };

// setFieldInvalid (ui.js) ผูก aria-invalid + aria-describedby ให้ด้วย
const setInvalid = setFieldInvalid;

/* ---------- แท็บ ---------- */

// initTabs (ui.js) ดูแล aria-selected / aria-controls / roving tabindex / ลูกศรซ้าย-ขวาให้
initTabs(document.querySelector(".tabs"), (name) => {
  if (name === "users") loadUsers();
});

/* ---------- แท็บ 1: ข้อมูลส่วนตัว ---------- */

function fillProfile(user) {
  me = user;
  Auth.saveUser(user);
  document.getElementById("pf-username").value = user.username;
  document.getElementById("pf-role").value = ROLE_LABEL[user.role] || user.role;
  document.getElementById("pf-fullname").value = user.full_name;
  document.getElementById("pf-email").value = user.email;
  document.getElementById("pf-phone").value = user.phone;
  document.getElementById("pf-meta").textContent =
    `รหัสผู้ใช้ #${user.id} · สมัครเมื่อ ${user.created_at.replace("T", " ")} · แก้ไขล่าสุด ${user.updated_at.replace("T", " ")}`;

  document.getElementById("tab-users").classList.toggle("hidden", user.role !== "admin");
  if (user.role === "admin") {
    document.getElementById("pf-subtitle").textContent =
      "แก้ไขข้อมูลของคุณ และจัดการบัญชีผู้ใช้ทั้งหมดในระบบได้จากแท็บ “จัดการผู้ใช้”";
  }
  renderAuthZone("profile");   // อัปเดตชื่อบนแถบด้านบนให้ตรงกับข้อมูลล่าสุด
}

async function saveProfile(event) {
  event.preventDefault();

  const fullName = document.getElementById("pf-fullname").value.trim();
  const email = document.getElementById("pf-email").value.trim();
  const phone = document.getElementById("pf-phone").value.trim();

  setInvalid("pf-fullname", fullName.length < 2);
  setInvalid("pf-email", !EMAIL_RE.test(email));
  setInvalid("pf-phone", !phoneOk(phone));
  if (focusFirstInvalid(document.querySelector("[data-panel='info']"))) return;

  const btn = document.getElementById("pf-submit");
  btn.disabled = true;
  btn.textContent = "กำลังบันทึก...";

  try {
    const updated = await API.updateUser(me.id, { full_name: fullName, email, phone });
    fillProfile(updated);
    toast("บันทึกข้อมูลเรียบร้อย", "ok");
  } catch (err) {
    toast(err.message, "error");
    if (err.message.includes("อีเมล")) setInvalid("pf-email", true);
  } finally {
    btn.disabled = false;
    btn.textContent = "บันทึกการแก้ไข";
  }
}

/* ---------- แท็บ 2: เปลี่ยนรหัสผ่าน ---------- */

// แก้ให้ถูกแล้วสีแดงหายทันที (ของเดิม validate แค่ตอนกดบันทึก)
bindLiveClear({
  "pf-fullname": (v) => v.trim().length < 2,
  "pf-email": (v) => !EMAIL_RE.test(v.trim()),
  "pf-phone": (v) => !phoneOk(v),
  "pw-current": (v) => !v,
  "pw-new": (v) => !(v.length >= 8 && /[A-Za-z]/.test(v) && /\d/.test(v)),
  "pw-new2": (v) => !v || v !== document.getElementById("pw-new").value,
});

async function changePassword(event) {
  event.preventDefault();

  const current = document.getElementById("pw-current").value;
  const next = document.getElementById("pw-new").value;
  const next2 = document.getElementById("pw-new2").value;
  const strong = next.length >= 8 && /[A-Za-z]/.test(next) && /\d/.test(next);

  setInvalid("pw-current", !current);
  setInvalid("pw-new", !strong);
  setInvalid("pw-new2", next !== next2 || !next2);
  if (focusFirstInvalid(document.querySelector("[data-panel='password']"))) return;

  const btn = document.getElementById("pw-submit");
  btn.disabled = true;
  btn.textContent = "กำลังเปลี่ยนรหัสผ่าน...";

  try {
    await API.changePassword({ current_password: current, new_password: next });
    // backend ยกเลิก token ทุกอันหลังเปลี่ยนรหัส จึงต้องพากลับไปหน้าล็อกอิน
    Auth.clear();
    toast("เปลี่ยนรหัสผ่านสำเร็จ กรุณาเข้าสู่ระบบใหม่", "ok");
    setTimeout(() => (location.href = "/pages/login.html"), 1200);
  } catch (err) {
    toast(err.message, "error");
    setInvalid("pw-current", err.message.includes("รหัสผ่านเดิม"));
    btn.disabled = false;
    btn.textContent = "เปลี่ยนรหัสผ่าน";
  }
}

/* ---------- แท็บ 3: จัดการผู้ใช้ (เฉพาะ admin) ---------- */

function badgeFor(user) {
  return user.is_active
    ? '<span class="badge badge-ok">ใช้งานอยู่</span>'
    : '<span class="badge badge-bad">ถูกระงับ</span>';
}

async function loadUsers() {
  const tbody = document.getElementById("us-rows");
  tbody.setAttribute("aria-busy", "true");
  tbody.innerHTML = '<tr><td colspan="7" class="muted">กำลังโหลด...</td></tr>';

  try {
    const data = await API.users(usersView);
    if (!data.items.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="muted">ไม่พบผู้ใช้ตามเงื่อนไขที่ค้นหา</td></tr>';
    } else {
      tbody.innerHTML = data.items
        .map(
          (u) => `
        <tr>
          <td class="num">#${u.id}</td>
          <td>${esc(u.username)}</td>
          <td>${esc(u.full_name)}</td>
          <td class="muted">${esc(u.email)}</td>
          <td>${u.role === "admin" ? '<span class="badge badge-accent">admin</span>' : "customer"}</td>
          <td>${badgeFor(u)}</td>
          <td>
            <div class="row-actions">
              <button type="button" class="btn btn-ghost btn-sm" data-toggle="${u.id}" data-active="${u.is_active}"
                aria-label="${u.is_active ? "ระงับ" : "เปิดใช้"}บัญชี ${esc(u.username)}">
                ${u.is_active ? "ระงับ" : "เปิดใช้"}
              </button>
              <button type="button" class="btn btn-danger btn-sm" data-delete="${u.id}" data-name="${esc(u.username)}"
                aria-label="ลบบัญชี ${esc(u.username)}"
                ${u.id === me.id ? "disabled title='ลบบัญชีของตัวเองไม่ได้'" : ""}>ลบ</button>
            </div>
          </td>
        </tr>`
        )
        .join("");
    }

    const from = data.total ? (data.page - 1) * data.per_page + 1 : 0;
    const to = Math.min(data.page * data.per_page, data.total);
    document.getElementById("us-summary").textContent =
      `แสดง ${from}-${to} จากทั้งหมด ${data.total} บัญชี (หน้า ${data.page}/${data.total_pages})`;
    renderPager(data);
    bindRowActions();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="muted">${esc(err.message)}</td></tr>`;
  } finally {
    tbody.setAttribute("aria-busy", "false");
  }
}

function renderPager(data) {
  const pages = document.getElementById("us-pages");
  let html = `<button type="button" ${data.page <= 1 ? "disabled" : ""} data-page="${data.page - 1}">ก่อนหน้า</button>`;
  for (let p = 1; p <= data.total_pages; p++) {
    const on = p === data.page;
    html += `<button type="button" class="${on ? "active" : ""}" data-page="${p}"
      aria-label="หน้า ${p}" ${on ? 'aria-current="page"' : ""}>${p}</button>`;
  }
  html += `<button type="button" ${data.page >= data.total_pages ? "disabled" : ""} data-page="${data.page + 1}">ถัดไป</button>`;
  pages.innerHTML = html;

  pages.querySelectorAll("[data-page]").forEach((btn) => {
    btn.addEventListener("click", () => {
      usersView.page = Number(btn.dataset.page);
      loadUsers();
    });
  });
}

function bindRowActions() {
  document.querySelectorAll("[data-toggle]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = Number(btn.dataset.toggle);
      const nextActive = btn.dataset.active !== "true";
      try {
        await API.updateUser(id, { is_active: nextActive });
        toast(nextActive ? "เปิดใช้งานบัญชีแล้ว" : "ระงับบัญชีแล้ว", "ok");
        loadUsers();
      } catch (err) {
        toast(err.message, "error");
      }
    });
  });

  document.querySelectorAll("[data-delete]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = Number(btn.dataset.delete);
      // window.confirm ถูกบล็อกในบางสภาพแวดล้อม (กดแล้วเงียบ) — ใช้ modal ของระบบเองแทน
      const ok = await confirmDialog({
        title: "ยืนยันลบบัญชีผู้ใช้?",
        body: `ลบบัญชี "${btn.dataset.name}" ออกจากระบบถาวร — การลบนี้ย้อนกลับไม่ได้`,
        confirmText: "ยืนยันลบบัญชี",
        cancelText: "ไม่ลบ",
        danger: true,
      });
      if (!ok) return;
      try {
        await API.deleteUser(id);
        toast("ลบบัญชีเรียบร้อย", "ok");
        loadUsers();
      } catch (err) {
        toast(err.message, "error");
      }
    });
  });
}

let searchTimer = null;
document.getElementById("us-q").addEventListener("input", (e) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    usersView.q = e.target.value.trim();
    usersView.page = 1;
    loadUsers();
  }, 350);
});

document.getElementById("us-role").addEventListener("change", (e) => {
  usersView.role = e.target.value;
  usersView.page = 1;
  loadUsers();
});

/* ---------- เริ่มทำงาน ---------- */

async function initProfile() {
  if (!requireLogin("/pages/profile.html")) return;
  try {
    fillProfile(await API.me());
  } catch (err) {
    toast(err.message, "error");
    return setTimeout(() => (location.href = "/pages/login.html?next=/pages/profile.html"), 900);
  }
  document.getElementById("pf-form").addEventListener("submit", saveProfile);
  document.getElementById("pw-form").addEventListener("submit", changePassword);
}

initProfile();
