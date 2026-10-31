"""เตรียมไฟล์หน้าเว็บสำหรับอัปขึ้นโฮสต์ที่ให้พื้นที่เป็นโฟลเดอร์ย่อย เช่น angsila ของคณะ

ทำไมต้องมีสคริปต์นี้
    ทุกหน้าในโปรเจกต์อ้างไฟล์แบบ "/js/..." ซึ่งนับจากรากของโดเมนเสมอ
    พอเว็บไปอยู่ที่ http://angsila.cs.buu.ac.th/~67160175/ เบราว์เซอร์จะไปหา
    http://angsila.cs.buu.ac.th/js/... ซึ่งไม่มี หน้าเว็บจึงขึ้นมาเปล่า ๆ
    สคริปต์นี้คัดลอก frontend/ ไปไว้ที่ dist/ แล้วเติมคำนำหน้าให้ทุกลิงก์ภายใน
    พร้อมใส่ที่อยู่ของ API ลงใน js/config.js ให้ในตัว ตัวต้นฉบับใน frontend/ ไม่ถูกแตะ

วิธีใช้
    python scripts/build-static.py --base /~67160175 --api https://astra-motors-xxxx.onrender.com
    แล้วลากของข้างใน dist/ ขึ้นโฮสต์ด้วย FileZilla

    ถ้าเว็บอยู่ที่รากของโดเมนอยู่แล้ว ไม่ต้องใช้สคริปต์นี้ อัป frontend/ ขึ้นไปตรง ๆ ได้เลย
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "frontend"

# โฟลเดอร์ที่เป็นไฟล์ของเว็บเอง ลิงก์ที่ขึ้นต้นด้วยชื่อพวกนี้ต้องเติมคำนำหน้า
# "/api/..." ไม่อยู่ในรายการโดยเจตนา เพราะมันวิ่งไปหา backend คนละโฮสต์ผ่าน API_BASE
LOCAL_PREFIXES = ("css", "js", "pages", "assets", "index.html")

TEXT_SUFFIXES = {".html", ".js", ".css"}


def rewrite(text: str, base: str) -> str:
    """เติม base ให้ลิงก์ที่ขึ้นต้นด้วย / แล้วตามด้วยโฟลเดอร์ของเว็บ

    ครอบทั้ง href="/css/..." ใน HTML และสตริง "/pages/..." กับ `/assets/...` ใน JavaScript
    """
    pattern = re.compile(r'(["\'`])/(' + "|".join(re.escape(p) for p in LOCAL_PREFIXES) + r')')
    return pattern.sub(lambda m: f"{m.group(1)}{base}/{m.group(2)}", text)


def main() -> int:
    ap = argparse.ArgumentParser(description="เตรียมไฟล์หน้าเว็บสำหรับอัปขึ้นโฮสต์")
    ap.add_argument("--base", default="", help="โฟลเดอร์ย่อยบนโฮสต์ เช่น /~67160175 (ว่าง = รากของโดเมน)")
    ap.add_argument("--api", default="", help="ที่อยู่ของ backend เช่น https://astra-motors-xxxx.onrender.com")
    ap.add_argument("--out", default="dist", help="โฟลเดอร์ผลลัพธ์ (ค่าเริ่มต้น dist)")
    ap.add_argument("--skip-models", action="store_true",
                    help="ไม่คัดลอกโมเดล 3D (~46 MB) ใช้ตอนอัปรอบที่สองที่โมเดลขึ้นไปแล้ว")
    args = ap.parse_args()

    base = args.base.rstrip("/")
    if base and not base.startswith("/"):
        base = "/" + base
    api = args.api.rstrip("/")

    if api and not api.startswith(("http://", "https://")):
        print("--api ต้องขึ้นต้นด้วย http:// หรือ https://", file=sys.stderr)
        return 1

    out = (ROOT / args.out).resolve()
    if out.exists():
        shutil.rmtree(out)

    ignore = shutil.ignore_patterns("models") if args.skip_models else None
    shutil.copytree(SRC, out, ignore=ignore)

    touched = 0
    for f in out.rglob("*"):
        if f.suffix.lower() not in TEXT_SUFFIXES or not f.is_file():
            continue
        text = f.read_text(encoding="utf-8")
        new = rewrite(text, base) if base else text
        if f.name == "config.js":
            # ผูกกับต้นบรรทัด ไม่งั้นไปโดนบรรทัดตัวอย่างในคอมเมนต์ซึ่งอยู่เหนือค่าจริง
            new = re.sub(r'^window\.API_BASE = "[^"]*";',
                         f'window.API_BASE = "{api}";', new, count=1, flags=re.M)
        if new != text:
            f.write_text(new, encoding="utf-8", newline="\n")
            touched += 1

    print(f"เขียนไฟล์ไว้ที่ {out}")
    print(f"แก้ลิงก์ภายในแล้ว {touched} ไฟล์")
    print(f"  base = {base or '(รากของโดเมน)'}")
    print(f"  API  = {api or '(โฮสต์เดียวกับหน้าเว็บ)'}")
    if args.skip_models:
        print("  ไม่ได้คัดลอกโมเดล 3D ตามที่สั่ง")
    print("\nขั้นต่อไป: ลากของข้างในโฟลเดอร์นี้ขึ้นโฮสต์ (ไม่ใช่ลากตัวโฟลเดอร์)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
