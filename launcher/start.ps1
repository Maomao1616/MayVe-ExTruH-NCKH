# VMU PlotterPen - bat server (neu chua chay) roi mo trinh duyet.
# Goi tu start.vbs (chay an). Server tu tat khi dong het trang 10 phut (backend/app/idle.py), dang ve thi khong tat.
$root = Split-Path $PSScriptRoot -Parent
$port = 8000
# Python mang theo (Python\, ban embeddable) neu co; khong thi dung venv cua may da cai Python (backend\.venv)
$python = Join-Path $root "Python\python.exe"
if (-not (Test-Path $python)) { $python = Join-Path $root "backend\.venv\Scripts\python.exe" }

# Co server dang nghe cong khong: thu ket noi TCP, cho toi da 100 ms (cong mo tra loi ~1 ms).
# Khong dung Connect() thuong: tren Windows cong dong mat ~2 giay moi lan thu; Get-NetTCPConnection mat ~130 ms.
function Test-Port([int]$p) {
  $c = New-Object Net.Sockets.TcpClient
  try { return $c.ConnectAsync("127.0.0.1", $p).Wait(100) } catch { return $false } finally { $c.Close() }
}

# IP LAN: hoi Windows "di ra Internet thi dung IP nao" bang socket UDP (khong gui goi tin nao, gan nhu tuc thi;
# Windows tu chon card theo do uu tien tuyen, giong khi duyet web). Bo qua 169.254.x.x (card khong nhan duoc IP
# tu router). Khong co mang: dung localhost. Luu y: dang bat VPN thi co the ra IP cua VPN.
$ip = $null
try {
  $u = New-Object Net.Sockets.UdpClient
  $u.Connect("1.1.1.1", 80)
  $a = $u.Client.LocalEndPoint.Address.ToString()
  $u.Close()
  if ($a -notlike "169.254.*" -and $a -ne "0.0.0.0") { $ip = $a }
} catch {}
if (-not $ip) { $ip = "localhost" }

$started = $false
if (-not (Test-Port $port)) {
  if (-not (Test-Path $python)) {
    $sh = New-Object -ComObject WScript.Shell
    $sh.Popup("Khong tim thay Python.`n`nCach 1: giai nen thu muc Python\ canh backend\.`nCach 2 (may da cai Python 3.12): trong backend\ chay`n  py -3.12 -m venv .venv`n  .venv\Scripts\python.exe -m pip install -r requirements.txt", 0, "VMU PlotterPen", 16) | Out-Null
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
  for ($i = 0; $i -lt 200; $i++) {              # toi da ~30 giay
    Start-Sleep -Milliseconds 50
    if (Test-Port $port) { $up = $true; break }
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
  $started = $true
}
# Server da chay tu truoc ma IP may da doi (doi mang): server khong nhan IP moi -> mo localhost (luon vao duoc tren may nay).
# Vua tu bat thi IP chac chan dung, khoi hoi lai.
$url = "http://${ip}:${port}"
if (-not $started) {
  try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 "$url/api/health" | Out-Null } catch { $url = "http://localhost:${port}" }
}
Start-Process $url
