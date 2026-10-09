# การเข้าถึง (Accessibility) — ASTRA Motors

เอกสารนี้สรุป "รอบตรวจการเข้าถึง" ที่ทำกับหน้าเว็บฝั่งผู้ใช้ทั้ง 14 หน้า
(`frontend/index.html` + `frontend/pages/*.html`) โดยยึดเกณฑ์ WCAG 2.2 ระดับ AA เป็นหลัก

ขอบเขต: แก้เฉพาะ `frontend/css/style.css`, `frontend/index.html`, `frontend/pages/*.html`
และ `frontend/js/*.js` — ไม่แตะ backend และไม่เพิ่ม dependency ใด ๆ (ยังเป็น vanilla JS ไม่มี build step)

---

## 1. ตารางสรุป: ปัญหา → แก้อย่างไร → ไฟล์

### โครงสร้างหน้าและการนำทางด้วยคีย์บอร์ด

| ปัญหาที่พบ | แก้อย่างไร | ไฟล์ |
|---|---|---|
| ผู้ใช้คีย์บอร์ดต้องกด Tab ผ่านเมนู 6-7 อันทุกครั้งก่อนถึงเนื้อหา | เพิ่มลิงก์ "ข้ามไปที่เนื้อหาหลัก" เป็นตัวแรกของ `<body>` ใน `renderHeader` (ซ่อนไว้จนถูกโฟกัส) | `js/ui.js`, `css/style.css` |
| ไม่มีเป้าหมายให้ skip link กระโดดไป | ทุกหน้าให้ `<main id="main-content" tabindex="-1">` และ `main:focus { outline: none }` เพื่อไม่ให้ขึ้นวงแหวนรกตาตอนกระโดดถึง | `index.html`, `pages/*.html`, `css/style.css` |
| วงแหวนโฟกัสบาง กลืนกับพื้นหลังเข้ม | `:focus-visible` เป็นเส้นหนา 3px + `outline-offset` (ทำไว้ในรอบก่อน) และเพิ่ม offset ให้การ์ดที่กดได้ | `css/style.css` |
| ลำดับหัวข้อกระโดด / ไม่มี `<h1>` เลยในหน้าย่อย | ทุกหน้ามี `<h1>` เดียวเป็นหัวเรื่องของหน้า, เลื่อนการ์ดระดับบนจาก `h3` → `h2`, การ์ดโชว์รูม `h4` → `h3`, การ์ดรีวิว `h4` → `h3`, และใส่ `<h2 class="sr-only">` ให้แต่ละ tabpanel ของหน้าโปรไฟล์/หลังการขาย/หลังบ้าน | ทุกหน้า HTML, `js/status.js`, `js/test-drive.js`, `js/thai-road.js`, `js/ui.js` |

### ปุ่มไอคอน / ชื่อที่โปรแกรมอ่านหน้าจออ่านได้

| ปัญหาที่พบ | แก้อย่างไร | ไฟล์ |
|---|---|---|
| กระดิ่งแจ้งเตือนอ่านว่า "แจ้งเตือน 3" แบบตัวเลขลอย ๆ | ตัวเลขบนกระดิ่งเป็น `aria-hidden` แล้วเปลี่ยน `aria-label` ของปุ่มเป็น "แจ้งเตือน — ยังไม่ได้อ่าน N รายการ" ทุกครั้งที่จำนวนเปลี่ยน + เพิ่ม `aria-controls` ชี้ไปแผงแจ้งเตือน | `js/ui.js` |
| `<th></th>` ว่างในตาราง (คอลัมน์ปุ่ม) ไม่มีชื่อ | ใส่ `<span class="sr-only">การจัดการ</span>` | `pages/admin.html`, `pages/profile.html` |
| ปุ่ม "ระงับ / เปิดใช้ / ลบ" ในตารางซ้ำกันทุกแถว ไม่รู้ว่าของใคร | เติม `aria-label` ที่มีชื่อ username กำกับ | `js/profile.js` |
| ปุ่ม "แลก" ในรายการของรางวัลไม่บอกว่าแลกอะไร | เติม `aria-label` ที่มีชื่อรางวัล | `js/after-sales.js` |
| ปุ่มตัวเลขหน้าในตัวแบ่งหน้าอ่านว่า "1 2 3" เฉย ๆ | เติม `aria-label="หน้า N"` + `aria-current="page"` และห่อด้วย `<nav aria-label="แบ่งหน้า">` | `js/admin.js`, `js/profile.js`, `pages/admin.html`, `pages/profile.html` |
| ดาวคะแนนใช้ `<span aria-label>` ซึ่ง span เปล่าไม่มีชื่อได้ | เติม `role="img"` ให้ span ดาว | `js/ui.js` |

### คอนโทรลที่คีย์บอร์ดเคยใช้ไม่ได้ / สถานะไม่ถูกประกาศ

| ปัญหาที่พบ | แก้อย่างไร | ไฟล์ |
|---|---|---|
| ชิป/สวอตช์ที่เป็น `role="radio"` ทุกกลุ่มอยู่ในลำดับ Tab ทั้งหมด และเดินด้วยลูกศรไม่ได้ (ผิดแพทเทิร์น radiogroup) | เพิ่มตัวช่วยกลาง `bindRadioGroup()` ทำ roving tabindex + ลูกศรซ้าย/ขวา/บน/ล่าง + Home/End และโฟกัสตามไปหลังกลุ่ม render ใหม่ | `js/ui.js` + เรียกใช้ใน `js/test-drive.js`, `js/finance.js`, `js/thai-road.js`, `js/model.js`, `js/reserve.js`, `js/after-sales.js` |
| ชิป "ช่วงเวลาว่าง" (ทดลองขับ) และ "ช่วงเวลา" (ศูนย์บริการ) มีแค่คลาส `.selected` ไม่มี role/สถานะ | เป็น `role="radio"` + `aria-checked` จริง, กลุ่มเป็น `role="radiogroup"` ที่มี `aria-labelledby` | `js/test-drive.js`, `js/after-sales.js`, `pages/test-drive.html`, `pages/after-sales.html` |
| การ์ดใบจอง `.booking-pick` กดได้แต่ไม่บอกว่าใบไหนกำลังถูกเลือก | เพิ่ม `aria-pressed` และใส่ชื่อรุ่นรถใน `aria-label` (เดิมมี `role="button"` + Enter/Space + `tabindex="0"` อยู่แล้ว) | `js/status.js` |
| สวอตช์สีบอกแค่ชื่อสี ไม่บอกค่าใช้จ่ายเพิ่ม | `aria-label` เป็น "สี… เพิ่ม ฿…" + `title` สำหรับผู้ใช้เมาส์ | `js/model.js` |
| แท็บ (โปรไฟล์ / หลังการขาย / หลังบ้าน) ไม่ครบตามแพทเทิร์น ARIA — หน้าโปรไฟล์ไม่มี `aria-selected` เลย, ไม่มี `aria-controls`, ทุกแท็บอยู่ในลำดับ Tab | ตัวช่วยกลาง `initTabs()` จัดการ `role=tab/tabpanel`, `aria-selected`, `aria-controls`, `aria-labelledby`, roving tabindex และลูกศร/Home/End ให้ทั้ง 3 หน้า | `js/ui.js`, `js/profile.js`, `js/after-sales.js`, `js/admin.js`, `pages/profile.html` |
| ตารางกว้างเกินจอเลื่อนด้วยคีย์บอร์ดไม่ได้ | `.table-wrap` เป็น `tabindex="0" role="group" aria-label="… (เลื่อนแนวนอนได้)"` | `pages/admin.html`, `pages/profile.html`, `pages/compare.html`, `js/thai-road.js` |

### Modal ยกเลิกใบจอง (`status.html`)

| ปัญหาที่พบ | แก้อย่างไร | ไฟล์ |
|---|---|---|
| ปิดอยู่ด้วย `display: none` แต่เนื้อหายังอยู่ในลำดับ Tab ในบางสถานะ | ใช้แอตทริบิวต์ `hidden` คุมการเข้าถึง + `[hidden] { display: none !important }` | `pages/status.html`, `css/style.css` |
| เปิดแล้วโฟกัสยังค้างอยู่หลังฉาก | เปิดแล้วย้ายโฟกัสไปปุ่ม "เก็บใบจองไว้" (ตัวเลือกที่ปลอดภัยที่สุด) | `js/status.js` |
| กด Escape ปิดไม่ได้ | `keydown` บน modal: Escape = ปิด | `js/status.js` |
| Tab หลุดออกไปหลังฉากได้ | focus trap: Tab/Shift+Tab วนอยู่แค่ปุ่มใน modal | `js/status.js` |
| ปิดแล้วโฟกัสหลุดไปต้นหน้า | จำปุ่มที่เปิด (`document.activeElement`) แล้วคืนโฟกัสกลับเมื่อปิด | `js/status.js` |
| เลื่อนพื้นหลังได้ขณะ modal เปิด | `body.modal-open { overflow: hidden }` + คลิกพื้นหลังมืด = ปิด | `css/style.css`, `js/status.js` |
| หัวข้อ modal เป็น `h3` และปุ่มไม่มี `type` | เป็น `h2` + `type="button"` + เพิ่ม `aria-describedby` ชี้ไปข้อความเงื่อนไข | `pages/status.html` |

### Live region — ประกาศการเปลี่ยนแปลงโดยไม่แย่งโฟกัส

| พื้นที่ | ที่ทำ | ไฟล์ |
|---|---|---|
| `#toast-zone` | `role="status" aria-live="polite" aria-atomic="false"` | `js/ui.js` |
| สถานะสินเชื่อ/ใบจอง/นัดต่าง ๆ ในหน้าติดตามสถานะ (อัปเดตเองจาก poll ทุก 4 วินาที) | `aria-live="polite"` บน `#rsv-zone`, `#td-zone`, `#sv-zone` | `pages/status.html` |
| รายการคิวว่าง | `aria-live="polite"` บน `#slot-chips`, `#sv-slots` | `pages/test-drive.html`, `pages/after-sales.html` |
| ตารางหลังบ้าน / ตารางผู้ใช้ | `aria-live="polite"` + สลับ `aria-busy` ระหว่างโหลดบน `<tbody>` และ `aria-live` บนข้อความสรุปจำนวน | `pages/admin.html`, `pages/profile.html`, `js/admin.js`, `js/profile.js` |
| ราคา/ผลคำนวณที่อัปเดตทันที | `aria-live="polite"` บน `#price-lines`, `#sum-lines`, `#ln-preview`, `#loan-summary`, `#plan-list`, `#color-info` | หน้า model/reserve/loan/finance |

### ฟอร์มและข้อความผิดพลาด

| ปัญหาที่พบ | แก้อย่างไร | ไฟล์ |
|---|---|---|
| ข้อความ error สื่อด้วย "สีแดง" อย่างเดียว (ผิด WCAG 1.4.1 Use of Color) | `.field.invalid .error::before` เติมไอคอน ⚠ + คำว่า "ผิดพลาด:" นำหน้าข้อความ | `css/style.css` |
| สีแดง `--bad` (#e06060) บนพื้นเข้มได้คอนทราสต์แค่ 4.16:1 | ข้อความ/ป้าย/ปุ่มอันตรายเปลี่ยนไปใช้ `--bad-soft` ที่สว่างกว่า | `css/style.css` |
| ข้อความ error ไม่ได้ผูกกับช่องกรอก และไม่มี `aria-invalid` | ตัวช่วยกลาง `setFieldInvalid()` สลับคลาส `.invalid`, ตั้ง `aria-invalid` และต่อ/ถอด `aria-describedby` ให้ชี้ไปข้อความ error เฉพาะตอนที่ผิดจริง | `js/ui.js` + ใช้ใน `login.js`, `register.js`, `loan.js`, `reserve.js`, `profile.js`, `test-drive.js`, `after-sales.js` |
| มี `<label>` ที่ไม่มี `for` ชี้ไปที่อะไร (กลุ่มชิป/สวอตช์/เช็กบ็อกซ์) — label แบบนี้ไม่ถูกอ่าน | เปลี่ยนเป็น `<p class="field-label" id="…">` แล้วให้กลุ่มใช้ `aria-labelledby` | `pages/test-drive.html`, `pages/finance.html`, `pages/thai-road.html`, `pages/after-sales.html`, `js/ui.js` (ฟอร์มรีวิว) |
| เส้นขอบช่องกรอก/ชิปใช้ `--line` ซึ่งคอนทราสต์ไม่ถึง 3:1 (ผิด WCAG 1.4.11) | ใช้ `--field-border` กับ input / select / textarea / chip / swatch | `css/style.css` |

### ตาราง

| ปัญหาที่พบ | แก้อย่างไร | ไฟล์ |
|---|---|---|
| หัวตารางไม่มี `scope` | `scope="col"` ทุกหัวคอลัมน์ | `pages/admin.html` (4 ตาราง), `pages/profile.html`, `js/thai-road.js`, `js/compare.js` |
| ตารางเปรียบเทียบใช้ `<td>` เป็นชื่อรายการ (หัวแถว) | เปลี่ยนเป็น `<th scope="row">` | `js/compare.js` |
| ไม่มีคำอธิบายตาราง | `<caption class="sr-only">` ทุกตาราง (และถอด `aria-label` ที่ซ้ำซ้อนออกจากตารางเปรียบเทียบ) | ตารางทั้งหมด |

### จอแคบ 360px

| ปัญหาที่พบ | แก้อย่างไร | ไฟล์ |
|---|---|---|
| แถบบนสุดล้นออกนอกจอ — ปุ่ม "สมัครสมาชิก" ถูกดันออกไปจนกดไม่ได้ | ที่ ≤720px ให้ `.site-header .bar` ขึ้นบรรทัดใหม่: โลโก้ + ปุ่มสมาชิกแถวบน, เมนูเลื่อนแนวนอนแถวล่าง | `css/style.css` |
| ปุ่มเล็ก (`.btn-sm` 38px, ปุ่มการ์ดรถ 42px, ปุ่มแบ่งหน้า 38px) ต่ำกว่า 44px | ที่ ≤420px และบนอุปกรณ์สัมผัส (`pointer: coarse`) บังคับ `min-height: 44px` (ปุ่มแบ่งหน้าได้ `min-width` ด้วย) | `css/style.css` |
| แถบแท็บตัดบรรทัดเละที่จอแคบ | ที่ ≤420px ให้แท็บเลื่อนแนวนอนในแถบของตัวเอง | `css/style.css` |
| ปุ่มใน modal เบียดกัน | ที่ ≤420px เรียงปุ่มเป็นคอลัมน์เต็มความกว้าง | `css/style.css` |
| ตารางกว้างดันทั้งหน้าให้เลื่อนแนวนอน | `.table-wrap` เลื่อนในกรอบตัวเอง + `html, body { overflow-x: hidden }` ที่ ≤420px เป็นกันชนชั้นสุดท้าย | `css/style.css` |

### อื่น ๆ

- `prefers-reduced-motion` ครอบคลุม `.reveal` ด้วยแล้ว (ก่อนหน้านี้ค้างที่ `opacity: 0` เมื่อผู้ใช้ปิดแอนิเมชัน) และปิด `scroll-behavior` — ทำไว้ในรอบก่อนใน `css/style.css`
- แผงกระดิ่งแจ้งเตือน: Escape ปิดแล้วคืนโฟกัสกลับไปที่ปุ่มกระดิ่ง และคลิกที่ปุ่มเองไม่ทำให้แผงปิด-เปิดซ้อนกัน (`js/ui.js`)
- bump `?v=12` → `?v=13` ของทุก css/js ในทุกหน้า HTML (14 ไฟล์ × 5 รายการ) เพื่อไม่ให้เบราว์เซอร์ใช้ไฟล์เก่าค้าง

---

## 2. สิ่งที่ยังไม่ได้ทำ

1. **ยังไม่ได้ทดสอบกับโปรแกรมอ่านหน้าจอจริง** — ยังไม่เคยเปิดด้วย NVDA (Windows), VoiceOver (macOS/iOS) หรือ TalkBack (Android)
   สิ่งที่ตรวจไปคือโครงสร้าง ARIA/DOM และพฤติกรรมคีย์บอร์ด ซึ่งไม่รับประกันว่าเสียงอ่านจริงจะฟังรู้เรื่อง
   โดยเฉพาะ live region หลายจุดในหน้าเดียว (หน้าติดตามสถานะมี 4 จุด) อาจอ่านรัวเกินไปในการใช้งานจริง
2. **ยังไม่ได้ทำ WCAG audit เต็มรูปแบบ** — ยังไม่ได้ไล่ทีละ success criterion ระดับ AA ครบทุกข้อ
   และยังไม่ได้รันเครื่องมืออัตโนมัติ (axe DevTools, Lighthouse, WAVE, Pa11y) เพราะโปรเจกต์ไม่มี build step/ชุด tooling ฝั่งหน้าเว็บ
3. **คอนทราสต์ยังไม่ได้วัดครบทุกคู่สี** — แก้เฉพาะคู่ที่รู้ว่าตก (`--bad` บนพื้นเข้ม, เส้นขอบช่องกรอก)
   ยังไม่ได้วัด `--text-dim` บนพื้น `--surface-2`, ป้าย badge ทุกสี, ตัวเลขใน `.stat-tile` และข้อความบนภาพ hero
4. **โมเดล 3D (`<model-viewer>`)** — เป็น custom element จากภายนอก ยังไม่ได้ตรวจว่าตัว canvas/ปุ่มควบคุมของมันเข้าถึงด้วยคีย์บอร์ดได้แค่ไหน
   ตอนนี้ให้แค่ `alt="โมเดล 3D"` และมีภาพ SVG (`role="img"` + `aria-label`) เป็น fallback
5. **`<dialog>` ของเบราว์เซอร์** — modal ยกเลิกใบจองยังเป็น `div` + focus trap เขียนเอง ถ้าย้ายไปใช้ `<dialog>` จะได้ inert ของพื้นหลังฟรีและโค้ดสั้นลง
6. **ยังไม่มี `inert`/`aria-hidden` บนพื้นหลังขณะ modal เปิด** — ผู้ใช้โปรแกรมอ่านหน้าจอที่เดินด้วยโหมดสำรวจ (ไม่ใช่ Tab) ยังอ่านเนื้อหาหลังฉากได้
7. **ภาษาและทิศทางข้อความ** — `lang="th"` ตั้งไว้ระดับหน้า แต่คำอังกฤษปนไทย (eyebrow เช่น "Promotions", "Journey 6/7") ยังไม่ได้ใส่ `lang="en"` กำกับ
8. **ยังไม่ได้ทดสอบ zoom 200% / text-spacing** ตาม WCAG 1.4.4 และ 1.4.12

---

## 3. เช็กลิสต์ "วิธีตรวจซ้ำ"

รันเซิร์ฟเวอร์ก่อน แล้วเปิด `http://127.0.0.1:8010/`

### ก. คีย์บอร์ดล้วน (ห้ามแตะเมาส์เลย)

- [ ] กด Tab ครั้งแรกในทุกหน้า → ต้องเห็นปุ่ม "ข้ามไปที่เนื้อหาหลัก" โผล่มุมซ้ายบน กด Enter แล้วโฟกัสต้องไปอยู่ที่ `<main>`
- [ ] ไล่ Tab ทั้งหน้า → ต้องเห็นวงแหวนโฟกัสชัดทุกจุด ไม่มีจุดไหนที่โฟกัสหายไป และลำดับต้องตรงกับที่ตาเห็น
- [ ] กลุ่มชิป/สีรถ/ดาวรีวิว → Tab เข้ามาได้ **ครั้งเดียวต่อกลุ่ม** แล้วใช้ลูกศรซ้าย/ขวาเลือก (Home/End ไปตัวแรก/ตัวสุดท้าย)
- [ ] แท็บหน้าโปรไฟล์/หลังการขาย/หลังบ้าน → ลูกศรซ้ายขวาสลับแท็บ และแผงที่แสดงต้องเปลี่ยนตาม
- [ ] การ์ดโชว์รูม (`test-drive.html`) และการ์ดใบจอง (`status.html`) → โฟกัสถึงได้ และ Enter หรือ Space เลือกได้
- [ ] Modal ยกเลิกใบจอง (`status.html` → ปุ่ม "ยกเลิกใบจอง"):
  - [ ] เปิดแล้วโฟกัสอยู่ที่ปุ่ม "เก็บใบจองไว้"
  - [ ] Tab วนอยู่แค่ 2 ปุ่มใน modal ไม่หลุดไปหลังฉาก
  - [ ] Escape ปิด แล้วโฟกัสกลับไปที่ปุ่ม "ยกเลิกใบจอง"
- [ ] ตารางหลังบ้าน/ตารางผู้ใช้ → Tab ถึงกรอบตารางได้ แล้วลูกศรซ้าย/ขวาเลื่อนตารางแนวนอนได้
- [ ] กระดิ่งแจ้งเตือน → Enter เปิด, Escape ปิดแล้วโฟกัสกลับที่ปุ่มกระดิ่ง

### ข. จอกว้าง 360px

เปิด DevTools → Device toolbar → ตั้งความกว้าง 360px (หรือย่อหน้าต่างจริงให้เหลือ 360px)

- [ ] ไม่มีสกรอลล์แนวนอนของทั้งหน้าในทุกหน้า — ตรวจเร็วด้วยคอนโซล: `document.documentElement.scrollWidth - window.innerWidth` ต้อง ≤ 0
- [ ] แถบบนสุด: โลโก้ + ปุ่มสมาชิกแถวบน / เมนูแถวล่าง — ปุ่ม "สมัครสมาชิก" ต้องกดถึงได้
- [ ] ปุ่มทุกปุ่มสูงอย่างน้อย 44px — ตรวจเร็วด้วยคอนโซล:
  ```js
  [...document.querySelectorAll('button,.btn,[role=button],[role=radio]')]
    .filter(e => e.offsetParent && e.getBoundingClientRect().height < 44)
  ```
  ต้องได้ array ว่าง (ลิงก์ข้อความในย่อหน้าไม่นับ เป็นข้อยกเว้นของ WCAG 2.5.8)
- [ ] ตารางหลังบ้าน/โปรไฟล์/เปรียบเทียบ → เลื่อนในกรอบของตัวเอง ไม่ดันหน้าทั้งหน้า
- [ ] Modal ยกเลิก → ปุ่มเรียงเป็นคอลัมน์ ไม่ล้นกรอบ

### ค. คอนทราสต์

- [ ] ข้อความปกติต้อง ≥ 4.5:1, ข้อความใหญ่ (≥24px หรือ ≥19px ตัวหนา) ≥ 3:1, เส้นขอบ/คอนโทรล ≥ 3:1
- [ ] จุดที่ต้องดูเป็นพิเศษ: ข้อความ `.muted` (`--text-dim`) บนการ์ด, ป้าย badge ทั้ง 4 สี, ข้อความ error, เส้นขอบช่องกรอก
- [ ] ตรวจด้วย DevTools → เลือก element → ช่องสีใน Styles จะบอกอัตราคอนทราสต์ให้ หรือใช้ Lighthouse / axe DevTools
- [ ] ข้อผิดพลาดต้องไม่สื่อด้วยสีอย่างเดียว — ลองส่งฟอร์มว่าง ๆ แล้วต้องเห็น "⚠ ผิดพลาด:" นำหน้าข้อความทุกช่อง
  (ตรวจซ้ำด้วยการเปิดโหมด grayscale: DevTools → Rendering → Emulate vision deficiencies → Achromatopsia)

### ง. prefers-reduced-motion

- [ ] DevTools → Rendering → Emulate CSS media feature `prefers-reduced-motion: reduce`
- [ ] รีโหลดหน้าแรก → เนื้อหาทุกส่วนต้องแสดงครบทันที (`.rise` และ `.reveal` ต้องไม่ค้างที่โปร่งใส)
- [ ] แถบรายชื่อรุ่นวิ่ง (marquee) และ shimmer ตอนโหลดต้องหยุด
- [ ] การเลื่อนหน้าแบบ smooth ต้องกลายเป็นกระโดดทันที

### จ. ตรวจอัตโนมัติขั้นต่ำ (ไม่ต้องลง dependency)

- [ ] `for f in frontend/js/*.js; do node --check "$f"; done` — ต้องไม่มี error
- [ ] คอนโซลเบราว์เซอร์ต้องไม่มี error ในทุกหน้า
- [ ] ไม่เหลือ `?v=` รุ่นเก่า: `grep -rn "v=12" frontend/` ต้องไม่เจอ (เปลี่ยนเลขตามรอบที่ bump)
- [ ] `<label for>` ทุกตัวต้องชี้ไปที่ `id` ที่มีจริง — ตรวจเร็วในคอนโซล:
  ```js
  [...document.querySelectorAll('label[for]')].filter(l => !document.getElementById(l.htmlFor))
  ```
  ต้องได้ array ว่าง
