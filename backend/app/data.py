# ข้อมูลจำลอง (mock data) สำหรับสัปดาห์ที่ 1 — สัปดาห์ที่ 2 จะย้ายไปเก็บใน PostgreSQL
# หมายเหตุ: ใช้ชื่อรถจริงเพื่อการศึกษาเท่านั้น ราคา/สเปค/โปรโมชั่นเป็นการจำลอง ไม่ผูกกับตัวแทนจำหน่ายจริง

CARS = [
    {
        "id": "gtr-r35",
        "name": "Nissan GT-R R35",
        "tagline": "ตำนาน Godzilla ซูเปอร์คาร์ญี่ปุ่นที่จับต้องได้ที่สุด",
        "body": "ซูเปอร์คาร์ 2+2 ที่นั่ง",
        "price": 10500000,
        "engine": "3.8L V6 ทวินเทอร์โบ",
        "power_hp": 570,
        "torque_nm": 637,
        "drive": "ขับเคลื่อน 4 ล้อ (ATTESA E-TS AWD)",
        "seats": 4,
        "fuel": "8.5 กม./ลิตร",
        "accel": 2.8,
        "safety": "ระบบช่วยขับ + โหมดสนามแข่ง",
        "warranty": "3 ปี / 100,000 กม.",
        "colors": [
            {"id": "bayside-blue", "name": "น้ำเงิน Bayside Blue", "hex": "#1F4E9C", "extra": 100000, "stock": "in_stock"},
            {"id": "gun-metallic", "name": "เทา Gun Metallic", "hex": "#4B4F54", "extra": 0, "stock": "in_stock"},
            {"id": "pearl-white", "name": "ขาว Pearl White", "hex": "#E9EAEA", "extra": 50000, "stock": "in_stock"},
            {"id": "vibrant-red", "name": "แดง Vibrant Red", "hex": "#A6232C", "extra": 80000, "stock": "wait_8"},
        ],
        "options": [
            {"id": "nismo-exhaust", "name": "ชุดท่อไทเทเนียม NISMO", "price": 450000},
            {"id": "recaro", "name": "เบาะ Recaro Carbon", "price": 280000},
            {"id": "rays-wheels", "name": "ล้อฟอร์จ RAYS 20 นิ้ว", "price": 220000},
            {"id": "ppf", "name": "ฟิล์มกันรอย PPF รอบคัน", "price": 180000},
        ],
        "promotion": {"title": "ฟรีประกันภัยชั้น 1 + บำรุงรักษา 3 ปี", "expires": "2026-08-15"},
    },
    {
        "id": "porsche-911",
        "name": "Porsche 911 Carrera S",
        "tagline": "สปอร์ตคาร์ในตำนานกว่า 60 ปี ขับได้ทุกวัน",
        "body": "สปอร์ตคาร์ 2+2 ที่นั่ง",
        "price": 13900000,
        "engine": "3.0L บ็อกเซอร์ 6 สูบ ทวินเทอร์โบ",
        "power_hp": 450,
        "torque_nm": 530,
        "drive": "ขับเคลื่อนล้อหลัง (RWD)",
        "seats": 4,
        "fuel": "11.2 กม./ลิตร",
        "accel": 3.7,
        "safety": "Porsche Active Safe + ระบบช่วยขับครบ",
        "warranty": "4 ปี / ไม่จำกัดระยะทาง",
        "colors": [
            {"id": "guards-red", "name": "แดง Guards Red", "hex": "#C22F2B", "extra": 0, "stock": "in_stock"},
            {"id": "gt-silver", "name": "เงิน GT Silver", "hex": "#B9BCC0", "extra": 150000, "stock": "in_stock"},
            {"id": "racing-yellow", "name": "เหลือง Racing Yellow", "hex": "#E5C21E", "extra": 150000, "stock": "wait_6"},
            {"id": "gentian-blue", "name": "น้ำเงิน Gentian Blue", "hex": "#1F3B70", "extra": 100000, "stock": "in_stock"},
        ],
        "options": [
            {"id": "sport-chrono", "name": "แพ็กเกจ Sport Chrono", "price": 350000},
            {"id": "pccb", "name": "เบรกเซรามิก PCCB", "price": 620000},
            {"id": "burmester", "name": "เครื่องเสียง Burmester", "price": 390000},
            {"id": "glass-roof", "name": "หลังคากระจก", "price": 190000},
        ],
        "promotion": {"title": "ดอกเบี้ยพิเศษ 2.29% เมื่อดาวน์ 30% ขึ้นไป", "expires": "2026-07-31"},
    },
    {
        "id": "huracan-evo",
        "name": "Lamborghini Huracán EVO",
        "tagline": "V10 เสียงร้องสุดท้ายของยุค ก่อนโลกเปลี่ยนสู่ไฮบริด",
        "body": "ซูเปอร์คาร์ 2 ที่นั่ง",
        "price": 24900000,
        "engine": "5.2L V10 ไร้ระบบอัดอากาศ",
        "power_hp": 640,
        "torque_nm": 600,
        "drive": "ขับเคลื่อน 4 ล้อ (AWD)",
        "seats": 2,
        "fuel": "7.8 กม./ลิตร",
        "accel": 2.9,
        "safety": "โหมดขับขี่ ANIMA 3 โหมด + ESC",
        "warranty": "3 ปี / ไม่จำกัดระยะทาง",
        "colors": [
            {"id": "verde-mantis", "name": "เขียว Verde Mantis", "hex": "#3FA33C", "extra": 0, "stock": "in_stock"},
            {"id": "arancio", "name": "ส้ม Arancio Borealis", "hex": "#E5731F", "extra": 200000, "stock": "in_stock"},
            {"id": "nero", "name": "ดำ Nero Noctis", "hex": "#17181C", "extra": 0, "stock": "in_stock"},
            {"id": "bianco", "name": "ขาว Bianco Monocerus", "hex": "#E9E9E7", "extra": 150000, "stock": "wait_10"},
        ],
        "options": [
            {"id": "front-lift", "name": "ระบบยกหน้ารถ (Front Lift)", "price": 450000},
            {"id": "sport-exhaust", "name": "ท่อสปอร์ตไทเทเนียม", "price": 380000},
            {"id": "carbon-seats", "name": "เบาะคาร์บอนน้ำหนักเบา", "price": 520000},
            {"id": "carbon-pack", "name": "ชุดแต่งคาร์บอนรอบคัน", "price": 750000},
        ],
        "promotion": {"title": "ฟรี Track Day Experience ที่สนามช้าง 2 ครั้ง", "expires": "2026-09-01"},
    },
    {
        "id": "ferrari-488",
        "name": "Ferrari 488 GTB",
        "tagline": "ม้าลำพองจากมาราเนลโล V8 ทวินเทอร์โบระดับรางวัล",
        "body": "ซูเปอร์คาร์ 2 ที่นั่ง",
        "price": 27900000,
        "engine": "3.9L V8 ทวินเทอร์โบ",
        "power_hp": 670,
        "torque_nm": 760,
        "drive": "ขับเคลื่อนล้อหลัง (RWD)",
        "seats": 2,
        "fuel": "8.7 กม./ลิตร",
        "accel": 3.0,
        "safety": "Side Slip Control 2 + F1-Trac",
        "warranty": "3 ปี + Genuine Maintenance 7 ปี",
        "colors": [
            {"id": "rosso-corsa", "name": "แดง Rosso Corsa", "hex": "#C8102E", "extra": 0, "stock": "in_stock"},
            {"id": "giallo", "name": "เหลือง Giallo Modena", "hex": "#F2C511", "extra": 250000, "stock": "in_stock"},
            {"id": "nero-daytona", "name": "ดำ Nero Daytona", "hex": "#1A1B1F", "extra": 150000, "stock": "wait_12"},
            {"id": "argento", "name": "เงิน Argento Nürburgring", "hex": "#AEB2B5", "extra": 200000, "stock": "in_stock"},
        ],
        "options": [
            {"id": "carbon-wheels", "name": "ล้อคาร์บอนไฟเบอร์", "price": 900000},
            {"id": "front-lift", "name": "ระบบยกหน้ารถ (Front Lift)", "price": 480000},
            {"id": "daytona-seats", "name": "เบาะแข่งสไตล์ Daytona", "price": 550000},
            {"id": "carbon-interior", "name": "ภายในคาร์บอนไฟเบอร์", "price": 680000},
        ],
        "promotion": {"title": "ฟรีโปรแกรมบำรุงรักษา Genuine Maintenance 7 ปี", "expires": "2026-08-31"},
    },
]

SHOWROOMS = [
    {
        "id": "rama3",
        "name": "ASTRA สาขาพระราม 3",
        "address": "129 ถนนพระราม 3 แขวงบางโพงพาง เขตยานนาวา กรุงเทพฯ 10120",
        "phone": "02-100-2900",
        "hours": "เปิดทุกวัน 09:00–19:00",
    },
    {
        "id": "bangna",
        "name": "ASTRA สาขาบางนา กม.7",
        "address": "88/8 ถนนบางนา-ตราด กม.7 อำเภอบางพลี สมุทรปราการ 10540",
        "phone": "02-100-2901",
        "hours": "เปิดทุกวัน 09:00–19:00",
    },
    {
        "id": "rangsit",
        "name": "ASTRA สาขารังสิต",
        "address": "55 ถนนพหลโยธิน ตำบลคลองหนึ่ง อำเภอคลองหลวง ปทุมธานี 12120",
        "phone": "02-100-2902",
        "hours": "เปิดทุกวัน 09:00–19:00",
    },
    {
        "id": "chiangmai",
        "name": "ASTRA สาขาเชียงใหม่",
        "address": "199 ถนนซุปเปอร์ไฮเวย์ ตำบลหนองป่าครั่ง อำเภอเมือง เชียงใหม่ 50000",
        "phone": "052-100-290",
        "hours": "เปิดทุกวัน 09:00–18:30",
    },
]

# แผนสินเชื่อ (อัตราดอกเบี้ยคงที่แบบ flat rate ต่อปี — ชื่อสถาบันเป็นชื่อสมมติ)
FINANCE_PLANS = [
    {
        "id": "astra-finance",
        "name": "ASTRA Finance",
        "flat_rate": 1.99,
        "min_down_pct": 25,
        "terms": [48, 60],
        "promo": True,
        "note": "อัตราโปรโมชั่น — ต้องดาวน์ขั้นต่ำ 25% และจองภายในช่วงโปรโมชั่น",
    },
    {
        "id": "krungthai-leasing",
        "name": "กรุงสยามลิสซิ่ง",
        "flat_rate": 2.39,
        "min_down_pct": 15,
        "terms": [48, 60, 72, 84],
        "promo": False,
        "note": "อนุมัติไว เอกสารน้อย",
    },
    {
        "id": "scb-auto",
        "name": "สยามออโต้แคปปิตอล",
        "flat_rate": 2.59,
        "min_down_pct": 10,
        "terms": [48, 60, 72, 84],
        "promo": False,
        "note": "รองรับอาชีพอิสระ ใช้ statement ย้อนหลัง 6 เดือน",
    },
    {
        "id": "ttb-drive",
        "name": "ทีบีดี ไดรฟ์",
        "flat_rate": 2.85,
        "min_down_pct": 5,
        "terms": [60, 72, 84],
        "promo": False,
        "note": "ดาวน์ต่ำสุด 5% สำหรับผู้มีประวัติเครดิตดี",
    },
]

# ช่วงเวลาทดลองขับที่เปิดให้จองในแต่ละวัน
TESTDRIVE_HOURS = ["10:00", "11:00", "12:00", "14:00", "15:00", "16:00", "17:00", "18:00"]

BOOKING_FEE = 200000        # เงินจอง (บาท) — ระดับซูเปอร์คาร์
PRICE_LOCK_DAYS = 14        # จำนวนวันที่ล็อกราคา/โปรโมชั่นหลังออกใบจอง
REFUND_FULL_WITHIN_DAYS = 7  # ยกเลิกภายในกี่วันได้เงินจองคืนเต็มจำนวน

# เอกสารที่ต้องเตรียมในวันนัดรับรถ
DELIVERY_DOCUMENTS = [
    "บัตรประชาชนตัวจริง",
    "ใบขับขี่",
    "สำเนาทะเบียนบ้าน",
    "สลิปเงินเดือน/หลักฐานรายได้ 3 เดือนล่าสุด",
    "สมุดบัญชีธนาคารสำหรับหักค่างวดอัตโนมัติ",
]
