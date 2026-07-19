// หน้าแรก: โหลดรุ่นรถทั้งหมดมาแสดงเป็นการ์ด + ภาพ hero
"use strict";

renderHeader("home");
renderFooter();

const HERO_COLOR = "#C8102E"; // แดง Rosso Corsa — สีซูเปอร์คาร์ในใจทุกคน

async function initHome() {
  // hero ใช้โมเดล 3D ของ Ferrari 488 หมุนโชว์ (ลากหมุนได้)
  document.getElementById("hero-visual").innerHTML =
    carVisual3D("ferrari-488", HERO_COLOR, { height: 380, controls: true });
  initCarVisuals();

  const grid = document.getElementById("car-grid");
  // การ์ดโครง (skeleton) ระหว่างรอข้อมูลจาก API
  grid.innerHTML = Array.from({ length: 4 })
    .map(
      () => `
      <div class="skel-card" aria-hidden="true">
        <div class="skel-visual shimmer-overlay"></div>
        <div class="skel-line shimmer-overlay w60"></div>
        <div class="skel-line shimmer-overlay"></div>
        <div class="skel-line shimmer-overlay w40"></div>
      </div>`
    )
    .join("");
  try {
    const cars = await API.cars();

    // แถบสเปคใต้ hero ใช้ตัวเลขจริงของรุ่นท็อป (Ferrari 488 GTB)
    const top = cars.find((c) => c.id === "ferrari-488") || cars[0];
    document.getElementById("hero-ticker").innerHTML = `
      <span><b class="num">${top.power_hp} <i>HP</i></b>กำลังสูงสุด</span>
      <span><b class="num">${top.torque_nm} <i>Nm</i></b>แรงบิด</span>
      <span><b class="num">${top.accel} <i>วิ</i></b>0–100 กม./ชม.</span>
      <span><b class="num">${cars.length} <i>รุ่น</i></b>ให้เลือกเปรียบเทียบ</span>`;

    grid.setAttribute("aria-busy", "false");
    grid.innerHTML = cars
      .map((car, i) => {
        const defaultColor = car.colors.find((c) => c.extra === 0) || car.colors[0];
        return `
        <article class="car-card rise" style="animation-delay:${i * 90}ms">
          <div class="visual">${carVisual3D(car.id, defaultColor.hex)}</div>
          <div class="body">
            <h3>${car.name}</h3>
            <p class="tagline">${car.tagline}</p>
            <p class="price">${baht(car.price)} <small>ราคาเริ่มต้น</small></p>
            <div class="actions">
              <a class="btn btn-primary" href="/pages/model.html?id=${car.id}">ดูรายละเอียด</a>
              <a class="btn btn-ghost" href="/pages/test-drive.html?car=${car.id}">ทดลองขับ</a>
            </div>
          </div>
        </article>`;
      })
      .join("");
    initCarVisuals();
  } catch (err) {
    grid.innerHTML = `<p class="muted">${err.message}</p>`;
  }
}

initHome();
