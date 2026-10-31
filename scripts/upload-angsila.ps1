# อัปหน้าเว็บขึ้นโฮสต์ของคณะผ่าน SSH (angsila) โดยไม่ต้องลากไฟล์ใน FileZilla
#
# ต้องตั้ง SSH key ให้เข้าได้โดยไม่ถามรหัสผ่านก่อน (ทำครั้งเดียว ดู docs/DEPLOY-FTP.md)
# สคริปต์นี้ไม่รับและไม่เก็บรหัสผ่าน ถ้า key ยังไม่พร้อม ssh จะถามรหัสผ่านแล้วค้าง ให้กด Ctrl+C
#
# ตัวอย่าง
#   .\scripts\upload-angsila.ps1 -User 67160175 -Api https://astra-motors-xxxx.onrender.com
#   .\scripts\upload-angsila.ps1 -User 67160175 -Api https://... -SkipModels   # รอบถัดไปที่โมเดลขึ้นไปแล้ว
param(
    [Parameter(Mandatory = $true)][string]$User,
    [Parameter(Mandatory = $true)][string]$Api,
    [string]$ServerHost = "angsila.cs.buu.ac.th",
    [string]$RemoteDir = "public_html",
    [string]$Base = "",
    [switch]$SkipModels
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$dist = Join-Path $repo "dist"

# ไม่ระบุ -Base มาก็เดาจากชื่อผู้ใช้ เพราะ angsila ให้พื้นที่เป็น /~<ชื่อผู้ใช้>/
if (-not $Base) { $Base = "/~$User" }

Write-Output "เตรียมไฟล์ลง dist/ (base=$Base)"
$buildArgs = @("$repo\scripts\build-static.py", "--base", $Base, "--api", $Api)
if ($SkipModels) { $buildArgs += "--skip-models" }
$env:PYTHONUTF8 = "1"
python @buildArgs
if ($LASTEXITCODE -ne 0) { throw "เตรียมไฟล์ไม่สำเร็จ" }

$target = "$User@$ServerHost"

Write-Output "ตรวจว่าเข้า SSH ได้โดยไม่ถามรหัสผ่าน"
ssh -o BatchMode=yes -o ConnectTimeout=10 $target "mkdir -p ~/$RemoteDir"
if ($LASTEXITCODE -ne 0) {
    throw "เข้า $target ด้วย key ไม่ได้ ติดตั้ง public key บนเครื่องปลายทางก่อน (ดู docs/DEPLOY-FTP.md)"
}

Write-Output "ส่งไฟล์ขึ้น $target`:$RemoteDir"
# ส่งของข้างใน dist ไม่ใช่ตัวโฟลเดอร์ ไม่งั้นเว็บจะไปอยู่ลึกอีกชั้น
scp -r -q "$dist\*" "${target}:$RemoteDir/"
if ($LASTEXITCODE -ne 0) { throw "ส่งไฟล์ไม่สำเร็จ" }

# เว็บเซิร์ฟเวอร์ต้องอ่านไฟล์ในบ้านของเราได้ ไม่งั้นจะได้ 403
Write-Output "ตั้งสิทธิ์ไฟล์ให้เว็บเซิร์ฟเวอร์อ่านได้"
ssh -o BatchMode=yes $target "chmod 711 ~ && chmod -R a+rX ~/$RemoteDir"

$url = "http://$ServerHost/~$User/"
Write-Output ""
Write-Output "เสร็จแล้ว เปิดดูที่ $url"
Write-Output "ถ้าขึ้น 403 ให้ถามผู้ดูแลว่าโฟลเดอร์เว็บของนิสิตชื่ออะไร บางเครื่องไม่ใช่ public_html"
