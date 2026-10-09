# ข้อมูลตั้งต้น (seed data) — ตอนแอปเริ่มทำงาน seed.py จะนำข้อมูลชุดนี้ไปบันทึกลงฐานข้อมูล
# (PostgreSQL ใน Docker / SQLite เมื่อรันในเครื่องโดยไม่ใช้ Docker) ทุก endpoint อ่านจากฐานข้อมูลเท่านั้น
# หมายเหตุ: ใช้ชื่อรถจริงเพื่อการศึกษาเท่านั้น ราคา/สเปค/โปรโมชั่นเป็นการจำลอง ไม่ผูกกับตัวแทนจำหน่ายจริง

CARS = [
    {
        "id": "gtr-r35",
        "brand": "Nissan",
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
        # ค่าจำลองสำหรับหน้า "ถนนไทย" — ระยะต่ำสุดใต้ท้อง, ระบบยกหน้า, ล้อ/ยาง, ถังน้ำมัน
        "road": {
            "ground_clearance_mm": 110,
            "front_lift_mm": 0,          # R35 ไม่มีระบบยกหน้าจากโรงงาน
            "front_lift_option": None,
            "wheel_inch": 20,
            "tire_aspect": 35,           # ยางแก้มเตี้ย ยิ่งตัวเลขน้อยยิ่งเสี่ยงล้อคด
            "fuel_tank_l": 74,
            "fuel_grade": "เบนซิน 95",
            "city_kmpl": 5.6,
            "highway_kmpl": 11.5,
            "drive_code": "awd",
        },
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
        "brand": "Porsche",
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
        "road": {
            "ground_clearance_mm": 110,
            "front_lift_mm": 40,
            "front_lift_option": "front-lift",
            "wheel_inch": 20,
            "tire_aspect": 30,
            "fuel_tank_l": 67,
            "fuel_grade": "เบนซิน 95",
            "city_kmpl": 8.0,
            "highway_kmpl": 14.5,
            "drive_code": "rwd",
        },
        "safety": "Porsche Active Safe + ระบบช่วยขับครบ",
        "warranty": "4 ปี / ไม่จำกัดระยะทาง",
        "colors": [
            {"id": "guards-red", "name": "แดง Guards Red", "hex": "#C22F2B", "extra": 0, "stock": "in_stock"},
            {"id": "gt-silver", "name": "เงิน GT Silver", "hex": "#B9BCC0", "extra": 150000, "stock": "in_stock"},
            {"id": "racing-yellow", "name": "เหลือง Racing Yellow", "hex": "#E5C21E", "extra": 150000, "stock": "wait_6"},
            {"id": "gentian-blue", "name": "น้ำเงิน Gentian Blue", "hex": "#1F3B70", "extra": 100000, "stock": "in_stock"},
        ],
        "options": [
            {"id": "front-lift", "name": "ระบบยกหน้ารถ (Front Lift)", "price": 380000},
            {"id": "sport-chrono", "name": "แพ็กเกจ Sport Chrono", "price": 350000},
            {"id": "pccb", "name": "เบรกเซรามิก PCCB", "price": 620000},
            {"id": "burmester", "name": "เครื่องเสียง Burmester", "price": 390000},
            {"id": "glass-roof", "name": "หลังคากระจก", "price": 190000},
        ],
        "promotion": {"title": "ดอกเบี้ยพิเศษ 2.29% เมื่อดาวน์ 30% ขึ้นไป", "expires": "2026-12-31"},
    },
    {
        "id": "huracan-evo",
        "brand": "Lamborghini",
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
        "road": {
            "ground_clearance_mm": 115,
            "front_lift_mm": 45,
            "front_lift_option": "front-lift",
            "wheel_inch": 20,
            "tire_aspect": 30,
            "fuel_tank_l": 80,
            "fuel_grade": "เบนซิน 95",
            "city_kmpl": 5.2,
            "highway_kmpl": 10.4,
            "drive_code": "awd",
        },
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
        "promotion": {"title": "ฟรี Track Day Experience ที่สนามช้าง 2 ครั้ง", "expires": "2026-11-30"},
    },
    {
        "id": "ferrari-488",
        "brand": "Ferrari",
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
        "road": {
            "ground_clearance_mm": 115,
            "front_lift_mm": 40,
            "front_lift_option": "front-lift",
            "wheel_inch": 20,
            "tire_aspect": 30,
            "fuel_tank_l": 78,
            "fuel_grade": "เบนซิน 95",
            "city_kmpl": 5.8,
            "highway_kmpl": 11.6,
            "drive_code": "rwd",
        },
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
        "promotion": {"title": "ฟรีโปรแกรมบำรุงรักษา Genuine Maintenance 7 ปี", "expires": "2026-12-31"},
    },
]

SHOWROOMS = [
    {
        "id": "rama3",
        "name": "ASTRA สาขาพระราม 3",
        "address": "129 ถนนพระราม 3 แขวงบางโพงพาง เขตยานนาวา กรุงเทพฯ 10120",
        "phone": "02-100-2900",
        "hours": "เปิดทุกวัน 09:00–19:00",
        "service_center": True,
    },
    {
        "id": "bangna",
        "name": "ASTRA สาขาบางนา กม.7",
        "address": "88/8 ถนนบางนา-ตราด กม.7 อำเภอบางพลี สมุทรปราการ 10540",
        "phone": "02-100-2901",
        "hours": "เปิดทุกวัน 09:00–19:00",
        "service_center": True,
    },
    {
        "id": "rangsit",
        "name": "ASTRA สาขารังสิต",
        "address": "55 ถนนพหลโยธิน ตำบลคลองหนึ่ง อำเภอคลองหลวง ปทุมธานี 12120",
        "phone": "02-100-2902",
        "hours": "เปิดทุกวัน 09:00–19:00",
        "service_center": False,   # โชว์รูมขายอย่างเดียว ไม่มีศูนย์บริการ
    },
    {
        "id": "chiangmai",
        "name": "ASTRA สาขาเชียงใหม่",
        "address": "199 ถนนซุปเปอร์ไฮเวย์ ตำบลหนองป่าครั่ง อำเภอเมือง เชียงใหม่ 50000",
        "phone": "052-100-290",
        "hours": "เปิดทุกวัน 09:00–18:30",
        "service_center": True,
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

# ---------- การชำระเงินจอง (จำลอง) ----------
# เบอร์พร้อมเพย์ของ "ร้านค้า" — เป็นบัญชีสมมติสำหรับโปรเจกต์เรียนเท่านั้น
# QR ที่สร้างจากเบอร์นี้ถูกต้องตามสเปก EMVCo จริง แต่ปลายทางไม่ใช่บัญชีจริง ห้ามสแกนจ่าย
SHOP_PROMPTPAY_PHONE = "0812345678"
SHOP_PROMPTPAY_NAME = "ASTRA MOTORS (DEMO)"
PAYMENT_EXPIRE_MINUTES = 15   # QR/รายการชำระเงินอายุ 15 นาที เท่ากับของจริงที่ธนาคารใช้

# เอกสารที่ต้องเตรียมในวันนัดรับรถ
DELIVERY_DOCUMENTS = [
    "บัตรประชาชนตัวจริง",
    "ใบขับขี่",
    "สำเนาทะเบียนบ้าน",
    "สลิปเงินเดือน/หลักฐานรายได้ 3 เดือนล่าสุด",
    "สมุดบัญชีธนาคารสำหรับหักค่างวดอัตโนมัติ",
]


# ---------- บริการหลังการขาย (journey ขั้นตอน 7) ----------

# ช่วงเวลานัดเข้าศูนย์บริการ — แต่ละช่วงรับรถได้ SERVICE_BAYS คัน (จำนวนช่องซ่อม)
SERVICE_HOURS = ["08:30", "10:00", "11:30", "13:30", "15:00", "16:30"]
SERVICE_BAYS = 2

SERVICE_TYPES = [
    {"id": "periodic", "name": "เช็กระยะตามกำหนด", "hours": 2},
    {"id": "repair", "name": "ตรวจเช็ก/ซ่อมอาการผิดปกติ", "hours": 4},
    {"id": "tire", "name": "ยาง ล้อ และตั้งศูนย์ล้อ", "hours": 2},
    {"id": "detailing", "name": "ล้าง-เคลือบสี ดูแลสีรถ", "hours": 3},
    {"id": "software", "name": "อัปเดตซอฟต์แวร์/เรียกคืนตามประกาศผู้ผลิต", "hours": 1},
]

# คะแนนสะสมสมาชิก — ได้คะแนนเมื่อทำกิจกรรมใน journey แล้วนำไปแลกของรางวัล
POINTS_EARN = {
    "testdrive": 100,       # จองทดลองขับ
    "reservation": 2000,    # วางเงินจองรถ (ยกเลิกใบจองแล้วคะแนนถูกหักคืน)
    "review": 200,          # เขียนรีวิว
    "service": 100,         # นัดเข้าศูนย์บริการ
}

# ระดับสมาชิกคิดจากคะแนนที่ "เคยได้รับทั้งหมด" (ไม่ลดลงเมื่อแลกของรางวัล)
MEMBER_TIERS = [
    {"id": "member", "name": "Member", "min": 0},
    {"id": "silver", "name": "Silver", "min": 1000},
    {"id": "gold", "name": "Gold", "min": 3000},
    {"id": "platinum", "name": "Platinum", "min": 6000},
]

REWARDS = [
    {"id": "car-wash", "name": "ล้างรถ + เคลือบสีฟรี 1 ครั้ง", "points": 300},
    {"id": "oil-change", "name": "ส่วนลดเปลี่ยนน้ำมันเครื่อง 50%", "points": 800},
    {"id": "ppf-discount", "name": "ส่วนลดฟิล์มกันรอย PPF 20,000 บาท", "points": 1500},
    {"id": "track-day", "name": "Track Day Experience ที่สนามช้าง 1 ครั้ง", "points": 3000},
]

# ---------- ผู้ใช้งานระบบ (Authentication / User Management) ----------
# บัญชีผู้ใช้เก็บในตาราง users ของฐานข้อมูล (รหัสผ่านเป็น hash เท่านั้น)
# บัญชีตัวอย่างสำหรับเดโม — seed.py จะแฮชรหัสผ่านแล้วสร้างให้ ถ้ายังไม่มี username นี้ในฐานข้อมูล
# ห้ามใช้รูปแบบนี้กับระบบจริง! เป็นข้อมูลจำลองสำหรับการเรียนการสอนเท่านั้น
SEED_USERS = [
    {
        "username": "admin",
        "password": "admin1234",
        "full_name": "ผู้ดูแลระบบ ASTRA",
        "email": "admin@astramotors.demo",
        "phone": "0800000000",
        "role": "admin",
    },
    {
        "username": "somchai",
        "password": "somchai123",
        "full_name": "สมชาย ใจดี",
        "email": "somchai@example.com",
        "phone": "0812345678",
        "role": "customer",
    },
    {
        "username": "nattaya",
        "password": "nattaya123",
        "full_name": "ณัฐญา พงศ์ไพบูลย์",
        "email": "nattaya@example.com",
        "phone": "0899876543",
        "role": "customer",
    },
]


# ---------- สถานการณ์จำลองการใช้งานบนถนนไทย ----------
# ตัวเลขทั้งหมดเป็นค่าจำลองเพื่อการศึกษา ไม่ใช่ข้อมูลรับรองจากผู้ผลิต

FUEL_PRICE_DEFAULT = 41.5      # บาท/ลิตร (เบนซิน 95 โดยประมาณ)
KM_PER_YEAR_DEFAULT = 12000
TRAFFIC_SHARE_DEFAULT = 60     # % ระยะทางที่วิ่งในเมือง/รถติด

# ระยะทางอ้างอิงสำหรับคำนวณจำนวนครั้งที่ต้องเติมน้ำมัน
TRIP_BKK_CHIANGMAI_KM = 690

THAI_ROAD_PRESETS = {
    "floods": [
        {"id": "dry", "label": "ถนนแห้ง", "depth_cm": 0},
        {"id": "puddle", "label": "น้ำขังผิวถนน (ฝนเพิ่งหยุด)", "depth_cm": 5},
        {"id": "soi", "label": "น้ำรอระบายในซอย", "depth_cm": 15},
        {"id": "heavy", "label": "ฝนตกหนัก น้ำท่วมขังถนนใหญ่", "depth_cm": 25},
        {"id": "flood", "label": "น้ำท่วมสูง (ระดับกลางล้อ)", "depth_cm": 40},
    ],
    "bumps": [
        {"id": "flat", "label": "ไม่มีเนิน", "height_cm": 0},
        {"id": "ramp", "label": "ทางลาดเข้าห้าง/คอนโด", "height_cm": 9},
        {"id": "bump", "label": "ลูกระนาดหมู่บ้าน", "height_cm": 12},
        {"id": "hump", "label": "เนินชะลอความเร็วแบบสูง", "height_cm": 15},
        {"id": "bridge", "label": "คอสะพาน/รอยต่อถนนยกระดับ", "height_cm": 18},
    ],
    "roads": [
        {"id": "expressway", "label": "ทางด่วน/มอเตอร์เวย์ ผิวเรียบ", "rough": 0},
        {"id": "city", "label": "ถนนในเมือง มีรอยปะและฝาท่อ", "rough": 1},
        {"id": "upcountry", "label": "ถนนต่างจังหวัด มีหลุมบ่อ", "rough": 2},
        {"id": "narrow-soi", "label": "ซอยแคบ ผิวถนนชำรุด", "rough": 3},
    ],
    "defaults": {
        "fuel_price": FUEL_PRICE_DEFAULT,
        "km_per_year": KM_PER_YEAR_DEFAULT,
        "traffic_share_pct": TRAFFIC_SHARE_DEFAULT,
    },
}
