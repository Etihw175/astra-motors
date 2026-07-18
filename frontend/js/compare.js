// หน้าเปรียบเทียบรุ่น (journey ขั้นตอน 1): ตารางเทียบสเปค 3 คอลัมน์ เปลี่ยนรุ่นได้ทุกคอลัมน์
"use strict";

renderHeader("compare");
renderFooter();

let allCars = [];
let selected = []; // id ของรถแต่ละคอลัมน์

// แถวสเปค: [ป้ายชื่อ, ฟังก์ชันดึงค่า, วิธีหาค่าที่ดีที่สุด (min/max/null)]
const ROWS = [
  ["ราคาเริ่มต้น", (c) => baht(c.price), "min", (c) => c.price],
  ["ตัวถัง", (c) => c.body, null],
  ["เครื่องยนต์", (c) => c.engine, null],
  ["กำลังสูงสุด", (c) => `${c.power_hp} แรงม้า`, "max", (c) => c.power_hp],
  ["แรงบิด", (c) => `${c.torque_nm} นิวตันเมตร`, "max", (c) => c.torque_nm],
  ["ระบบขับเคลื่อน", (c) => c.drive, null],
  ["จำนวนที่นั่ง", (c) => `${c.seats} ที่นั่ง`, null],
  ["อัตราสิ้นเปลือง / ระยะทาง", (c) => c.fuel, null],
  ["อัตราเร่ง 0–100", (c) => `${c.accel} วินาที`, "min", (c) => c.accel],
  ["ความปลอดภัย", (c) => c.safety, null],
  ["การรับประกัน", (c) => c.warranty, null],
  ["โปรโมชั่น", (c) => c.promotion ? c.promotion.title : "-", null],
];

function render() {
  const cars = selected.map((id) => allCars.find((c) => c.id === id));

  document.getElementById("head-row").innerHTML =
    `<th class="row-label">รายการ</th>` +
    cars
      .map(
        (car, i) => `
        <th>
          <select data-col="${i}" aria-label="เลือกรุ่นคอลัมน์ที่ ${i + 1}">
            ${allCars
              .map(
                (c) =>
                  `<option value="${c.id}" ${c.id === car.id ? "selected" : ""}>${c.name}</option>`
              )
              .join("")}
          </select>
        </th>`
      )
      .join("");

  const bodyRows = ROWS.map(([label, getText, mode, getNum]) => {
    let bestIdx = -1;
    if (mode) {
      const nums = cars.map(getNum);
      const best = mode === "min" ? Math.min(...nums) : Math.max(...nums);
      bestIdx = nums.indexOf(best);
    }
    const cells = cars
      .map((c, i) => `<td class="${i === bestIdx ? "best" : ""}">${getText(c)}</td>`)
      .join("");
    return `<tr><td class="row-label">${label}</td>${cells}</tr>`;
  });

  // แถวปุ่มไปหน้าถัดไปของ journey
  bodyRows.push(
    `<tr><td class="row-label"></td>` +
      cars
        .map(
          (c) => `
          <td>
            <div style="display:flex;flex-direction:column;gap:8px">
              <a class="btn btn-primary" href="/pages/model.html?id=${c.id}">ดูรุ่นนี้</a>
              <a class="btn btn-ghost" href="/pages/test-drive.html?car=${c.id}">ทดลองขับ</a>
            </div>
          </td>`
        )
        .join("") +
      `</tr>`
  );
  document.getElementById("body-rows").innerHTML = bodyRows.join("");

  document.querySelectorAll("#head-row select").forEach((sel) => {
    sel.addEventListener("change", () => {
      selected[Number(sel.dataset.col)] = sel.value;
      render();
    });
  });
}

async function initCompare() {
  try {
    allCars = await API.cars();
    selected = allCars.slice(0, 3).map((c) => c.id);
    render();
  } catch (err) {
    document.getElementById("body-rows").innerHTML =
      `<tr><td colspan="4" class="muted">${err.message}</td></tr>`;
  }
}

initCompare();
