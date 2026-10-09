# สร้าง QR payload ของพร้อมเพย์ (PromptPay) ตามสเปก EMVCo Merchant-Presented QR
#
# อ่านก่อนแก้ — ทำไมเขียนเองไม่ใช้ไลบรารี:
#   payload มีแค่ไม่กี่ tag และต้องปิดท้ายด้วย CRC16 ที่คำนวณจากทั้งสตริง
#   เขียนเองจึงตรวจสอบ/อธิบายในรายงานได้ว่าทุก byte มาจากสเปกข้อไหน
#
# !! สำคัญ: payload ที่ได้เป็น "ของจริงตามสเปก" (แอปธนาคารอ่านออกและขึ้นชื่อบัญชีผู้รับ)
#    แต่เบอร์พร้อมเพย์ของ "ร้านค้า" ในโปรเจกต์นี้เป็นบัญชีสมมติ (ดู data.py)
#    จึงห้ามนำ QR ที่ระบบนี้สร้างไปสแกนจ่ายเงินจริงเด็ดขาด — ทุก response มี simulation: true กำกับไว้
import io

import segno

# ค่าคงที่ตามสเปก
_AID_PROMPTPAY = "A000000677010111"   # Application ID ของพร้อมเพย์ (ใต้ tag 29 sub-tag 00)
_CURRENCY_THB = "764"                 # ISO 4217 ตัวเลขของเงินบาท (tag 53)
_COUNTRY_TH = "TH"                    # ISO 3166-1 (tag 58)


def _tag(tag_id: str, value: str) -> str:
    """1 field ของ EMVCo = ID 2 หลัก + ความยาว 2 หลัก + ค่า (ความยาวนับเป็นตัวอักษร)"""
    return f"{tag_id}{len(value):02d}{value}"


def crc16_ccitt(data: str) -> str:
    """CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF) — คืนเลขฐาน 16 ตัวใหญ่ 4 หลักตามที่สเปกกำหนด"""
    crc = 0xFFFF
    for byte in data.encode("ascii"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return f"{crc:04X}"


def _phone_proxy(phone: str) -> str:
    """เบอร์มือถือไทย -> รูปแบบ proxy ของพร้อมเพย์: 0066 + เบอร์ที่ตัด 0 หน้าออก (รวม 13 หลัก)"""
    digits = "".join(ch for ch in phone if ch.isdigit())
    if digits.startswith("66"):
        digits = digits[2:]
    return ("0066" + digits.lstrip("0")).rjust(13, "0")


def promptpay_payload(phone: str, amount: float) -> str:
    """payload ของ QR พร้อมเพย์แบบระบุจำนวนเงิน (one-time / dynamic)

    tag ที่ใช้:
      00 = "01"            รุ่นของรูปแบบ payload
      01 = "12"            12 = ใช้ครั้งเดียว (ระบุยอดแล้ว) / 11 = QR คงที่ไม่ระบุยอด
      29 = ข้อมูลผู้รับเงินพร้อมเพย์ { 00 = AID, 01 = proxy เบอร์โทร }
      53 = "764"           สกุลเงินบาท
      54 = ยอดเงิน         ทศนิยม 2 ตำแหน่งเสมอ
      58 = "TH"            ประเทศผู้รับ
      63 = CRC16           คำนวณจากสตริงทั้งหมดที่มี "6304" ต่อท้ายแล้ว
    """
    merchant = _tag("00", _AID_PROMPTPAY) + _tag("01", _phone_proxy(phone))
    body = (
        _tag("00", "01")
        + _tag("01", "12")
        + _tag("29", merchant)
        + _tag("53", _CURRENCY_THB)
        + _tag("54", f"{amount:.2f}")
        + _tag("58", _COUNTRY_TH)
    )
    # CRC ต้องรวม "6304" (ID + ความยาว ของ tag 63) เข้าไปในข้อมูลที่คำนวณด้วย
    return body + "6304" + crc16_ccitt(body + "6304")


def qr_svg(payload: str, scale: int = 5) -> str:
    """แปลง payload เป็น QR รูปแบบ SVG (string) — ไม่เก็บไฟล์รูปในฐานข้อมูล เก็บแค่ payload

    SVG เพราะคมทุกขนาดหน้าจอ และฝังลง innerHTML ได้ตรง ๆ โดยไม่ต้องทำ endpoint เสิร์ฟรูป
    """
    buffer = io.BytesIO()
    segno.make(payload, error="m").save(
        buffer,
        kind="svg",
        scale=scale,
        border=2,
        # สีดำ/ขาวตรง ๆ ไม่ใช้ design token เพราะ QR ต้องคอนทราสต์สูงจริงถึงจะสแกนติด
        # (ถ้าไล่ตามธีมมืด โมดูลจะกลืนพื้นหลังจนอ่านไม่ออก)
        dark="#000000",
        light="#ffffff",
        xmldecl=False,   # ฝังลง innerHTML ได้ตรง ๆ ไม่ต้องมีหัว <?xml ?>
        nl=False,
        svgclass=None,
        lineclass=None,
        omitsize=True,   # ไม่ล็อก width/height ให้ CSS คุมขนาดตามหน้าจอ
    )
    return buffer.getvalue().decode("utf-8")
