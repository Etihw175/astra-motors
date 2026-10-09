// หลังการขาย (journey ขั้นตอน 7): คะแนนสะสม + แลกรางวัล / นัดเข้าศูนย์บริการ / รีวิว
// คะแนนไม่ได้ถูกบวกจากหน้านี้ — Loyalty service ฝั่ง backend บวกให้เองเมื่อมี event จากขั้นตอนอื่น
"use strict";

requireLogin("/pages/after-sales.html");
renderHeader("after-sales");
renderFooter();

const EARN_LABELS = {
  testdrive: "จองทดลองขับ",
  reservation: "วางเงินจองรถ (หักคืนถ้ายกเลิก)",
  review: "เขียนรีวิว",
  service: "นัดเข้าศูนย์บริการออนไลน์",
};

let cars = [];
// myCarIds เรียงตามลำดับความเป็นเจ้าของ: รถที่มีใบจองมาก่อน แล้วค่อยรถที่เคยจองทดลองขับ
// (ฟอร์มรีวิวต้องตั้งต้นเป็นรถที่ลูกค้ามีจริง ไม่ใช่รุ่นแรกในรายการทั้งหมด)
let myCarIds = [];
let reservedCarIds = [];
let serviceTime = null;

/* ---------- แท็บ (จำแท็บไว้ใน URL #service / #reviews ให้ลิงก์จากแจ้งเตือนตรงแท็บ) ---------- */

// initTabs (ui.js) ดูแล aria-selected / aria-controls / roving tabindex / ลูกศรซ้าย-ขวาให้
const TABS = initTabs(document.querySelector(".tabs"), (name) => {
  history.replaceState(null, "", `#${name}`);
});

function openTab(name) {
  TABS.select(name);
}

/* ---------- คะแนนสะสม ---------- */

async function renderLoyalty() {
  let data;
  try {
    data = await API.loyalty();
  } catch (err) {
    document.getElementById("member-card").innerHTML = `<p class="muted">${esc(err.message)}</p>`;
    return;
  }

  const next = data.next_tier;
  const pct = next ? Math.min(100, Math.round((data.lifetime_earned / next.min) * 100)) : 100;
  document.getElementById("member-card").innerHTML = `
    <p class="tier">${data.tier.name} member</p>
    <p class="points">${data.balance.toLocaleString("th-TH")}<small>คะแนนพร้อมใช้</small></p>
    <p class="muted small">สะสมทั้งหมด ${data.lifetime_earned.toLocaleString("th-TH")} คะแนน</p>
    <div class="progress" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}"
         aria-label="ความคืบหน้าสู่ระดับถัดไป"><span style="width:${pct}%"></span></div>
    <p class="small mt-1">${
      next
        ? `อีก <b class="num">${next.points_needed.toLocaleString("th-TH")}</b> คะแนน เลื่อนเป็น ${next.name}`
        : "คุณอยู่ระดับสูงสุดแล้ว"
    }</p>`;

  document.getElementById("earn-rules").innerHTML = Object.entries(data.earn_rules)
    .map(
      ([key, pts]) => `
      <div class="list-row"><div class="main"><b>${EARN_LABELS[key] || key}</b></div>
      <span class="pts-plus">+${pts.toLocaleString("th-TH")}</span></div>`
    )
    .join("");

  document.getElementById("rewards").innerHTML = data.rewards
    .map(
      (r) => `
      <div class="list-row reward-row">
        <div class="main"><b>${esc(r.name)}</b><span class="num">${r.points.toLocaleString("th-TH")} คะแนน</span></div>
        <button class="btn ${r.affordable ? "btn-primary" : "btn-ghost"}" data-reward="${r.id}" type="button"
          aria-label="${r.affordable ? "แลก" : "คะแนนไม่พอสำหรับ"} ${esc(r.name)}"
          ${r.affordable ? "" : "disabled"}>${r.affordable ? "แลก" : "คะแนนไม่พอ"}</button>
      </div>`
    )
    .join("");
  document.querySelectorAll("[data-reward]").forEach((btn) =>
    btn.addEventListener("click", async () => {
      // คลิกเดียวแล้วคะแนนหายไปเลยกู้คืนไม่ได้ — ต้องถามยืนยันก่อน (confirmDialog ใน ui.js
      // ใช้ modal เดียวกับหน้า "การจองของฉัน" ไม่ใช้ window.confirm ที่บางที่บล็อกไว้)
      const reward = data.rewards.find((r) => r.id === btn.dataset.reward);
      const name = reward ? reward.name : "ของรางวัลนี้";
      const cost = reward ? reward.points.toLocaleString("th-TH") : "";
      const ok = await confirmDialog({
        title: "ยืนยันแลกของรางวัล?",
        body: `แลก "${name}" ใช้ ${cost} คะแนน จากที่มี ${data.balance.toLocaleString("th-TH")} คะแนน`
          + " — คะแนนจะถูกหักทันทีและไม่สามารถยกเลิกได้",
        confirmText: "ยืนยันแลก",
        cancelText: "ไม่แลก",
      });
      if (!ok) return;

      btn.disabled = true;
      try {
        const res = await API.redeem(btn.dataset.reward);
        toast(`แลกสำเร็จ รหัสสิทธิ์ ${res.voucher}`, "ok");
        showVoucher(name, res.voucher);
        renderLoyalty();
      } catch (err) {
        toast(err.message, "error");
        btn.disabled = false;
      }
    })
  );

  document.getElementById("history").innerHTML = data.history.length
    ? data.history
        .map(
          (h) => `
          <div class="list-row">
            <div class="main"><b>${esc(h.reason)}</b>
              <span>${new Date(h.created_at).toLocaleDateString("th-TH", { day: "numeric", month: "short", year: "numeric" })}</span></div>
            <span class="${h.points > 0 ? "pts-plus" : "pts-minus"}">${h.points > 0 ? "+" : ""}${h.points.toLocaleString("th-TH")}</span>
          </div>`
        )
        .join("")
    : '<p class="muted small">ยังไม่มีคะแนน — เริ่มจาก<a href="/pages/test-drive.html"> จองทดลองขับ</a> รับ 100 คะแนน</p>';
}

// รหัสสิทธิ์ที่แลกได้ต้องอ่านได้จากหน้านี้ ไม่ใช่มีแต่ในกระดิ่งแจ้งเตือน
// (renderLoyalty วาดใหม่แค่รายการรางวัล กล่องนี้อยู่คนละ element จึงไม่ถูกล้าง)
function showVoucher(rewardName, code) {
  const zone = document.getElementById("redeem-result");
  if (!zone) return;
  zone.classList.remove("hidden");
  zone.innerHTML = `
    <p class="small">แลก <b>${esc(rewardName)}</b> สำเร็จ — รหัสสิทธิ์ของคุณ</p>
    <p class="code num">${esc(code)}</p>
    <p class="muted small">แสดงรหัสนี้ที่โชว์รูมหรือศูนย์บริการ (ดูย้อนหลังได้ที่กระดิ่งแจ้งเตือน)</p>`;
}

/* ---------- นัดเข้าศูนย์บริการ ---------- */

async function loadServiceSlots() {
  const zone = document.getElementById("sv-slots");
  const center = document.getElementById("sv-center").value;
  const date = document.getElementById("sv-date").value;
  serviceTime = null;
  if (!center || !date) return;
  zone.innerHTML = '<p class="muted small">กำลังเช็คคิวศูนย์บริการ…</p>';
  try {
    const data = await API.serviceSlots(center, date);
    zone.innerHTML = data.slots
      .map(
        (s) => `<button type="button" class="chip" data-time="${s.time}" ${s.available ? "" : "disabled"}
          role="radio" aria-checked="false"
          aria-label="${s.time} น. ${s.available ? `ว่าง ${s.remaining} ช่อง` : "เต็ม"}">${s.time}</button>`
      )
      .join("");
    zone.querySelectorAll(".chip:not(:disabled)").forEach((chip) =>
      chip.addEventListener("click", () => {
        serviceTime = chip.dataset.time;
        zone.querySelectorAll(".chip").forEach((c) => {
          c.classList.toggle("selected", c === chip);
          c.setAttribute("aria-checked", String(c === chip));
        });
      })
    );
    bindRadioGroup(zone);
  } catch (err) {
    zone.innerHTML = `<p class="muted small">${esc(err.message)}</p>`;
  }
}

async function renderServiceList() {
  const zone = document.getElementById("sv-list");
  try {
    const list = await API.myServices();
    if (!list.length) {
      zone.innerHTML = '<div class="card muted">ยังไม่มีนัดหมาย</div>';
      return;
    }
    zone.innerHTML = `<div class="card list-rows">${list
      .map(
        (s) => `
        <div class="list-row">
          <div class="main">
            <b>${esc(s.service_type.name)}</b>
            <span>${esc(s.car.name)} · เลขไมล์ ${s.mileage_km.toLocaleString("th-TH")} กม.</span>
            <span>${esc(s.showroom.name)} · ${thaiDate(s.date)} ${s.time} น.</span>
            <span class="num">${s.code}</span>
          </div>
          ${
            s.status === "booked"
              ? `<button class="btn btn-danger btn-sm" data-cancel-sv="${s.code}" type="button">ยกเลิก</button>`
              : '<span class="badge badge-bad">ยกเลิกแล้ว</span>'
          }
        </div>`
      )
      .join("")}</div>`;
    zone.querySelectorAll("[data-cancel-sv]").forEach((btn) =>
      btn.addEventListener("click", async () => {
        btn.disabled = true;
        try {
          await API.cancelService(btn.dataset.cancelSv);
          toast("ยกเลิกนัดแล้ว (หักคืน 100 คะแนน)", "ok");
          renderServiceList();
          loadServiceSlots();
          renderLoyalty();
        } catch (err) {
          toast(err.message, "error");
          btn.disabled = false;
        }
      })
    );
  } catch (err) {
    zone.innerHTML = `<p class="muted">${esc(err.message)}</p>`;
  }
}

async function submitService(e) {
  e.preventDefault();
  const mileageInput = document.getElementById("sv-mileage");
  const mileage = Number(mileageInput.value);
  const badMileage = mileageInput.value === "" || mileage < 0;
  setFieldInvalid("sv-mileage", badMileage);
  if (!document.getElementById("sv-date").value) return toast("กรุณาเลือกวันที่", "error");
  if (!serviceTime) return toast("กรุณาเลือกช่วงเวลา", "error");
  if (focusFirstInvalid(document.getElementById("sv-form"))) return;

  const btn = document.getElementById("sv-submit");
  btn.disabled = true;
  btn.textContent = "กำลังยืนยัน…";
  try {
    const record = await API.createService({
      car_id: document.getElementById("sv-car").value,
      showroom_id: document.getElementById("sv-center").value,
      date: document.getElementById("sv-date").value,
      time: serviceTime,
      service_type: document.getElementById("sv-type").value,
      mileage_km: mileage,
      note: document.getElementById("sv-note").value,
    });
    toast(`นัดหมายสำเร็จ ${record.code} — ได้รับ 100 คะแนน`, "ok");
    document.getElementById("sv-note").value = "";
    renderServiceList();
    loadServiceSlots();
    renderLoyalty();
  } catch (err) {
    toast(err.message, "error");
    if (err.message.includes("เต็ม")) loadServiceSlots();
  } finally {
    btn.disabled = false;
    btn.textContent = "ยืนยันนัดหมาย";
  }
}

async function initService() {
  const [types, showrooms] = await Promise.all([API.serviceTypes(), API.showrooms()]);
  // รถที่ผู้ใช้จอง/ซื้อไว้ขึ้นก่อน รุ่นอื่นตามมา (กรณีซื้อจากช่องทางอื่นแต่ใช้ศูนย์เรา)
  const rank = (id) => (reservedCarIds.includes(id) ? 0 : myCarIds.includes(id) ? 1 : 2);
  const ordered = [...cars].sort((a, b) => rank(a.id) - rank(b.id));
  document.getElementById("sv-car").innerHTML = ordered
    .map((c) => `<option value="${c.id}">${esc(c.name)}${myCarIds.includes(c.id) ? " (รถของฉัน)" : ""}</option>`)
    .join("");
  document.getElementById("sv-car-hint").textContent = myCarIds.length
    ? "รุ่นที่มีใบจองในบัญชีของคุณแสดงเป็นอันดับแรก"
    : "";
  document.getElementById("sv-type").innerHTML = types
    .map((t) => `<option value="${t.id}">${t.name} (ประมาณ ${t.hours} ชม.)</option>`)
    .join("");
  // แสดงเฉพาะสาขาที่มีศูนย์บริการ (สาขารังสิตเป็นโชว์รูมขายอย่างเดียว)
  document.getElementById("sv-center").innerHTML = showrooms
    .filter((s) => s.service_center)
    .map((s) => `<option value="${s.id}">${esc(s.name)}</option>`)
    .join("");

  const dateInput = document.getElementById("sv-date");
  dateInput.min = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
  // แก้เลขไมล์ให้ถูกแล้วสีแดงหายทันที (ของเดิม validate แค่ตอนกดยืนยัน)
  bindLiveClear({ "sv-mileage": (v) => v === "" || Number(v) < 0 });
  dateInput.addEventListener("change", loadServiceSlots);
  document.getElementById("sv-center").addEventListener("change", loadServiceSlots);
  document.getElementById("sv-form").addEventListener("submit", submitService);
  renderServiceList();
}

/* ---------- รีวิว ---------- */

async function renderReviewTab() {
  const mine = await API.myReviews();
  const reviewed = new Set(mine.map((r) => r.car.id));
  const left = cars.filter((c) => !reviewed.has(c.id));

  const formZone = document.getElementById("rv-zone");
  if (left.length) {
    // เลือกตามลำดับ "ความเป็นรถของฉัน" (ใบจอง → ทดลองขับ) ไม่ใช่ลำดับของรายการรถทั้งหมด
    // ของเดิมไล่จาก left ก่อน จึงได้รุ่นแรกที่ตรงอะไรก็ได้ (เช่น Nissan ที่เพียงเคยทดลองขับ)
    const preferredId = myCarIds.find((id) => left.some((c) => c.id === id));
    const preferred = left.find((c) => c.id === preferredId) || left[0];
    formZone.innerHTML = reviewFormHTML(left, preferred.id);
    bindReviewForm(() => {
      renderReviewTab();
      renderLoyalty();
    });
  } else {
    formZone.innerHTML = '<h3>รีวิวครบทุกรุ่นแล้ว</h3><p class="muted mt-1">ขอบคุณที่ช่วยแบ่งปันประสบการณ์</p>';
  }

  const list = document.getElementById("my-reviews");
  list.innerHTML = mine.length
    // ปุ่มลบขึ้นตาม is_mine จาก backend (เลิกเทียบ user_id เอง)
    ? mine.map((r) => reviewCardHTML(r, { onDelete: r.is_mine !== false })).join("")
    : '<div class="card muted">ยังไม่ได้เขียนรีวิว</div>';
  list.querySelectorAll("[data-del-review]").forEach((btn) =>
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      try {
        await API.deleteReview(btn.dataset.delReview);
        toast("ลบรีวิวแล้ว (หักคืน 200 คะแนน)", "ok");
        renderReviewTab();
        renderLoyalty();
      } catch (err) {
        toast(err.message, "error");
        btn.disabled = false;
      }
    })
  );
}

/* ---------- รายการที่สนใจ ---------- */

async function renderWatchlist() {
  const grid = document.getElementById("wl-grid");
  let items;
  try {
    items = await API.watchlist();
  } catch (err) {
    grid.innerHTML = `<p class="muted">${esc(err.message)}</p>`;
    return;
  }
  // ซิงก์ชุดรหัสที่ติดตามไว้ด้วย เพื่อให้ปุ่ม "เอาออก" ของการ์ดสะท้อนสถานะจริง
  Watch.ids = new Set(items.map((w) => w.car.id));
  if (!items.length) {
    grid.innerHTML = `<div class="card muted" style="grid-column:1/-1">
      ยังไม่มีรุ่นที่สนใจ — กดปุ่มหัวใจบนการ์ดรถที่<a href="/"> หน้าแรก</a>
      หรือในหน้ารายละเอียดรุ่น เพื่อเก็บไว้ดูภายหลัง</div>`;
    return;
  }
  grid.innerHTML = items
    .map(
      (w) => `
      <article class="card wl-card">
        <div class="head">
          ${stars(w.car.rating.avg, w.car.rating.count)}
          ${promoBadge(w.promotion)}
        </div>
        <h3>${esc(w.car.name)}</h3>
        <p class="muted small">${esc(w.car.tagline)}</p>
        <p class="price num">${baht(w.car.price)}</p>
        ${w.promotion && w.promotion.active ? `<p class="small">${esc(w.promotion.title)}</p>` : ""}
        <div class="actions">
          <a class="btn btn-primary btn-sm" href="/pages/model.html?id=${encodeURIComponent(w.car.id)}">ดูรายละเอียด</a>
          <a class="btn btn-ghost btn-sm" href="/pages/test-drive.html?car=${encodeURIComponent(w.car.id)}">จองทดลองขับ</a>
          <button type="button" class="btn btn-ghost btn-sm" data-unwatch="${esc(w.car.id)}"
                  aria-label="เอา ${esc(w.car.name)} ออกจากรายการที่สนใจ">เอาออก</button>
        </div>
      </article>`
    )
    .join("");
  grid.querySelectorAll("[data-unwatch]").forEach((btn) =>
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      try {
        await API.unwatchCar(btn.dataset.unwatch);
        Watch.ids.delete(btn.dataset.unwatch);
        toast("เอาออกจากรายการที่สนใจแล้ว", "ok");
        renderWatchlist();
      } catch (err) {
        toast(err.message, "error");
        btn.disabled = false;
      }
    })
  );
}

/* ---------- เริ่มต้น ---------- */

async function initAfterSales() {
  if (!Auth.isLoggedIn()) return;
  const tab = location.hash.slice(1);
  if (["points", "service", "reviews", "watchlist"].includes(tab)) openTab(tab);

  try {
    const [carList, mine] = await Promise.all([API.cars(), API.myBookings()]);
    cars = carList;
    reservedCarIds = mine.reservations.filter((r) => r.status !== "cancelled").map((r) => r.car.id);
    myCarIds = [...new Set([...reservedCarIds, ...mine.testdrives.map((t) => t.car.id)])];
  } catch (err) {
    return toast(err.message, "error");
  }
  renderLoyalty();
  initService().catch((err) => toast(err.message, "error"));
  renderReviewTab().catch((err) => toast(err.message, "error"));
  renderWatchlist();
}

initAfterSales();
