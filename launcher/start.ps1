# VMU PlotterPen - bat server (neu chua chay) roi mo trinh duyet.
# Goi tu start.vbs (chay an). Server tu tat khi dong het trang 10 phut (backend/app/idle.py), dang ve thi khong tat.
$root = Split-Path $PSScriptRoot -Parent
$port = 8000
$python = Join-Path $root "Python\python.exe"

# IP LAN cua card mang dang ra router (tranh nham VPN, vEthernet). Uu tien = RouteMetric + InterfaceMetric
# (giong Windows chon). Bo qua 169.254.x.x (card khong nhan duoc IP tu router). Khong co mang: dung localhost.
$ip = $null
$routes = Get-NetRoute -DestinationPrefix 0.0.0.0/0 -ErrorAction SilentlyContinue | Sort-Object {
  $_.RouteMetric + (Get-NetIPInterface -InterfaceIndex $_.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue).InterfaceMetric
}
foreach ($r in $routes) {
  $ip = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceIndex $r.ifIndex -ErrorAction SilentlyContinue |
         Where-Object { $_.IPAddress -notlike "169.254.*" } | Select-Object -First 1).IPAddress
  if ($ip) { break }
}
if (-not $ip) { $ip = "localhost" }

if (-not (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)) {
  if (-not (Test-Path $python)) {
    $sh = New-Object -ComObject WScript.Shell
    $sh.Popup("Khong tim thay $python", 0, "VMU PlotterPen", 16) | Out-Null
    exit 1
  }
  $env:EXTRUXY_ALLOWED_HOSTS = "localhost,127.0.0.1,$ip"
  $env:EXTRUXY_DATA_DIR      = Join-Path $root "data"
  $env:EXTRUXY_IDLE_EXIT_MIN = "10"
  # May khac cung mang vao duoc giao dien: dat PIN de nguoi la khong mo khoa chuyen dong duoc.
  # $env:EXTRUXY_UNLOCK_PIN  = "1234"
  # Chi ghi LOI khi khoi dong (khong ghi tung yeu cau), ghi de moi lan bat: xem khi server khong len.
  New-Item -ItemType Directory -Force -Path $env:EXTRUXY_DATA_DIR | Out-Null
  $proc = Start-Process $python -PassThru -WindowStyle Hidden -WorkingDirectory (Join-Path $root "backend") `
    -ArgumentList "-m","uvicorn","app.main:app","--host","0.0.0.0","--port",$port,"--no-access-log","--log-level","warning" `
    -RedirectStandardError (Join-Path $root "data\server-loi.txt")
  $up = $false
  for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Milliseconds 500
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) { $up = $true; break }
    if ($proc.HasExited) { break }                 # Python thoat ngay (loi): bao luon, khoi cho
  }
  if (-not $up) {
    # Server khong len (thieu thu vien, cong bi chiem...): bao loi thay vi mo trang trang
    $log = Join-Path $env:EXTRUXY_DATA_DIR "server-loi.txt"
    $tail = ""
    if (Test-Path $log) { $tail = (Get-Content $log -Tail 8) -join "`n" }
    $sh = New-Object -ComObject WScript.Shell
    $sh.Popup("Server khong bat len duoc.`n`n$tail`n`nChi tiet: $log", 0, "VMU PlotterPen", 16) | Out-Null
    exit 1
  }
}
# Server da chay tu truoc ma IP may da doi (doi mang): server khong nhan IP moi -> mo localhost (luon vao duoc tren may nay).
$url = "http://${ip}:${port}"
try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 "$url/api/health" | Out-Null } catch { $url = "http://localhost:${port}" }
Start-Process $url
