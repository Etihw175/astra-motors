# ข้อมูลจำลอง (mock data) สำหรับสัปดาห์ที่ 1 — สัปดาห์ที่ 2 จะย้ายไปเก็บใน PostgreSQL
# หมายเหตุ: ชื่อแบรนด์/รุ่น/สถาบันการเงินเป็นชื่อสมมติทั้งหมด

CARS = [
    {
        "id": "terra-x",
        "name": "ASTRA Terra X",
        "tagline": "SUV ครอบครัว 7 ที่นั่ง ขุมพลังไฮบริด",
        "body": "SUV 7 ที่นั่ง",
        "price": 1459000,
        "engine": "1.5L เทอร์โบ ไฮบริด",
        "power_hp": 190,
        "torque_nm": 340,
        "drive": "ขับเคลื่อนล้อหน้า (FWD)",
        "seats": 7,
        "fuel": "22.7 กม./ลิตร",
        "accel": 8.9,
        "safety": "ADAS 21 ระบบ",
        "warranty": "5 ปี / 150,000 กม.",
        "colors": [
            {"id": "pearl", "name": "ขาวเพิร์ลมูน", "hex": "#E8E9EB", "extra": 10000, "stock": "in_stock"},
            {"id": "graphite", "name": "เทากราไฟต์", "hex": "#4A4F55", "extra": 0, "stock": "in_stock"},
            {"id": "copper", "name": "ทองแดงซันเซ็ต", "hex": "#B4653A", "extra": 15000, "stock": "wait_6"},
            {"id": "navy", "name": "น้ำเงินมิดไนต์", "hex": "#22314E", "extra": 0, "stock": "in_stock"},
        ],
        "options": [
            {"id": "sunroof", "name": "หลังคาพาโนรามิกซันรูฟ", "price": 45000},
            {"id": "leather", "name": "เบาะหนังแนปปา", "price": 38000},
            {"id": "adas-plus", "name": "แพ็กเกจ ADAS Plus", "price": 29000},
            {"id": "powergate", "name": "ประตูท้ายไฟฟ้าเซ็นเซอร์เตะ", "price": 18000},
        ],
        "promotion": {"title": "ดอกเบี้ยพิเศษ 1.99% + ฟรีประกันภัยชั้น 1 ปีแรก", "expires": "2026-08-15"},
    },
    {
        "id": "vertex-ev",
        "name": "ASTRA Vertex EV",
        "tagline": "SUV ไฟฟ้า 100% วิ่งไกล 520 กม.",
        "body": "SUV ไฟฟ้า 5 ที่นั่ง",
        "price": 1799000,
        "engine": "มอเตอร์ไฟฟ้าคู่ (Dual Motor)",
        "power_hp": 320,
        "torque_nm": 540,
        "drive": "ขับเคลื่อน 4 ล้อ (AWD)",
        "seats": 5,
        "fuel": "520 กม./ชาร์จ (WLTP)",
        "accel": 5.8,
        "safety": "ADAS 24 ระบบ",
        "warranty": "8 ปี / 180,000 กม. (แบตเตอรี่)",
        "colors": [
            {"id": "silver", "name": "เงินลูนาร์", "hex": "#C4C9CE", "extra": 0, "stock": "in_stock"},
            {"id": "white", "name": "ขาวกลาเซียร์", "hex": "#EDEFF0", "extra": 0, "stock": "in_stock"},
            {"id": "red", "name": "แดงอิกไนต์", "hex": "#9E2B25", "extra": 20000, "stock": "wait_8"},
            {"id": "green", "name": "เขียวฟอเรสต์", "hex": "#2E4B3F", "extra": 15000, "stock": "in_stock"},
        ],
        "options": [
            {"id": "home-charger", "name": "เครื่องชาร์จติดผนังบ้าน + ติดตั้ง", "price": 35000},
            {"id": "sunroof", "name": "หลังคากระจกพาโนรามิก", "price": 42000},
            {"id": "premium-audio", "name": "เครื่องเสียงพรีเมียม 14 ลำโพง", "price": 32000},
            {"id": "autopark", "name": "ระบบจอดอัตโนมัติ", "price": 25000},
        ],
        "promotion": {"title": "ฟรีเครื่องชาร์จบ้าน + ค่าติดตั้ง เมื่อจองภายในเดือนนี้", "expires": "2026-07-31"},
    },
    {
        "id": "nova-sport",
        "name": "ASTRA Nova Sport",
        "tagline": "Coupe SUV สายสปอร์ต คล่องตัวในเมือง",
        "body": "Coupe SUV 5 ที่นั่ง",
        "price": 1299000,
        "engine": "1.5L เทอร์โบ",
        "power_hp": 163,
        "torque_nm": 253,
        "drive": "ขับเคลื่อนล้อหน้า (FWD)",
        "seats": 5,
        "fuel": "16.4 กม./ลิตร",
        "accel": 9.6,
        "safety": "ADAS 17 ระบบ",
        "warranty": "5 ปี / 150,000 กม.",
        "colors": [
            {"id": "yellow", "name": "เหลืองโวลต์", "hex": "#D9A62E", "extra": 12000, "stock": "in_stock"},
            {"id": "black", "name": "ดำออบซิเดียน", "hex": "#23262B", "extra": 0, "stock": "in_stock"},
            {"id": "white", "name": "ขาวอาร์กติก", "hex": "#E9EAEC", "extra": 0, "stock": "in_stock"},
            {"id": "blue", "name": "ฟ้าซีเรน", "hex": "#3E6C93", "extra": 8000, "stock": "wait_4"},
        ],
        "options": [
            {"id": "sport-kit", "name": "ชุดแต่งสปอร์ตรอบคัน", "price": 39000},
            {"id": "leather", "name": "เบาะหนังสังเคราะห์สปอร์ต", "price": 22000},
            {"id": "wireless", "name": "แท่นชาร์จไร้สาย + USB-C คู่หลัง", "price": 6900},
        ],
        "promotion": {"title": "ดาวน์เริ่มต้น 0 บาท + ฟรีประกันชั้น 1", "expires": "2026-09-01"},
    },
    {
        "id": "summit-pro",
        "name": "ASTRA Summit Pro",
        "tagline": "PPV ดีเซล 4x4 ลุยได้ทุกเส้นทาง",
        "body": "PPV 7 ที่นั่ง",
        "price": 1899000,
        "engine": "2.2L ดีเซลเทอร์โบคู่",
        "power_hp": 204,
        "torque_nm": 500,
        "drive": "ขับเคลื่อน 4 ล้อ (4x4)",
        "seats": 7,
        "fuel": "14.3 กม./ลิตร",
        "accel": 10.2,
        "safety": "ADAS 19 ระบบ",
        "warranty": "5 ปี / 160,000 กม.",
        "colors": [
            {"id": "bronze", "name": "บรอนซ์แคนยอน", "hex": "#8A6A4B", "extra": 15000, "stock": "in_stock"},
            {"id": "grey", "name": "เทาสตอร์ม", "hex": "#5B6167", "extra": 0, "stock": "in_stock"},
            {"id": "black", "name": "ดำแกรนิต", "hex": "#26292E", "extra": 0, "stock": "wait_3"},
            {"id": "white", "name": "ขาวเอเวอเรสต์", "hex": "#ECEDEE", "extra": 0, "stock": "in_stock"},
        ],
        "options": [
            {"id": "towbar", "name": "ชุดลากจูง (Tow Bar)", "price": 28000},
            {"id": "roofrack", "name": "แร็คหลังคา + บันไดข้าง", "price": 24000},
            {"id": "offroad", "name": "แพ็กเกจออฟโรด (สกิดเพลท+ยาง AT)", "price": 46000},
            {"id": "camera360", "name": "กล้องรอบคัน 360°", "price": 19000},
        ],
        "promotion": {"title": "ฟรีอุปกรณ์ลุย 3 รายการ มูลค่า 45,000 บาท", "expires": "2026-08-31"},
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

BOOKING_FEE = 5000          # เงินจอง (บาท)
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
