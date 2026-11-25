# VMU PlotterPen - bat server (neu chua chay) roi mo trinh duyet.
# Goi tu start.vbs (chay an). Server tu tat khi dong het trang 10 phut (backend/app/idle.py), dang ve thi khong tat.
$root = Split-Path $PSScriptRoot -Parent
$port = 8000
# Chon Python CHAY DUOC (thu that, khong chi kiem tep ton tai): backend\.venv truoc, roi Python\ (ban mang theo).
# .venv ghi cung duong dan Python cua may da tao no: sang may khac se hong -> bo qua, chay "Cai may moi.bat" de tao lai.
function Test-Python([string]$p) {
  if (-not (Test-Path $p)) { return $false }
  try {
    $pr = Start-Process $p -ArgumentList "-c","`"import fastapi, uvicorn`"" -Wait -PassThru -WindowStyle Hidden
    return ($pr.ExitCode -eq 0)
  } catch { return $false }
}
function Find-Python {
  foreach ($c in @((Join-Path $root "backend\.venv\Scripts\python.exe"), (Join-Path $root "Python\python.exe"))) {
    if (Test-Python $c) { return $c }
  }
  return $null
}

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
  $python = Find-Python
  if (-not $python) {
    $sh = New-Object -ComObject WScript.Shell
    $sh.Popup("Khong co Python chay duoc tren may nay.`n`nBam dup 'Cai may moi.bat' o thu muc goc (can Python 3.12 va Internet, mat vai phut), roi bam icon lai.", 0, "VMU PlotterPen", 16) | Out-Null
    exit 1
  }
  $env:EXTRUXY_ALLOWED_HOSTS = "localhost,127.0.0.1,$ip"
  $env:EXTRUXY_DATA_DIR      = Join-Path $root "data"
  $env:EXTRUXY_IDLE_EXIT_MIN = "10"
  # PIN doc tu data\pin.txt (data\ khong len Git, khong vao ban dong goi, Cap nhat.bat giu nguyen). Moi dong mot PIN:
  #   admin=<so>    PIN QUAN LY: khach (khong dang nhap) chi xem trang thai, xem truoc G-code va anh. Khong dat = ai vao cung la quan ly.
  #   unlock=<so>   PIN mo khoa chuyen dong (may duoc phep chay). Khong dat = khong doi PIN.
  # May khac cung mang vao duoc giao dien thi nen dat ca hai.
  $pinFile = Join-Path $root "data\pin.txt"
  if (Test-Path $pinFile) {
    foreach ($line in Get-Content $pinFile) {
      if ($line -match '^\s*(admin|unlock)\s*=\s*(\S+)\s*$') {
        if ($Matches[1] -eq "admin") { $env:EXTRUXY_ADMIN_PIN = $Matches[2] } else { $env:EXTRUXY_UNLOCK_PIN = $Matches[2] }
      }
    }
  }
  # MO RA NGOAI (tuy chon): data\mang.txt (khong len Git), moi dong mot muc:
  #   host=plotter.tenmien.com   them ten mien vao danh sach Host duoc phep (nhieu dong duoc)
  #   giu_bat=1                  server khong tu tat khi dong het trang (de may khac van vao duoc)
  #   tunnel=plotter             chay "cloudflared tunnel run plotter" cung server (da cai cloudflared, xem docs/13)
  #   url=https://plotter.tenmien.com   dia chi hien o nut QR tren header
  # Luu y: chua dat PIN quan ly (admin=) thi ai vao duoc dia chi nay cung la quan ly (chu du an da chon khong bat buoc PIN).
  $netHosts = @(); $tunnel = $null
  $netFile = Join-Path $root "data\mang.txt"
  if (Test-Path $netFile) {
    foreach ($line in Get-Content $netFile) {
      if ($line -match '^\s*host\s*=\s*([A-Za-z0-9.-]+)\s*$') { $netHosts += $Matches[1] }
      elseif ($line -match '^\s*giu_bat\s*=\s*1\s*$') { $env:EXTRUXY_IDLE_EXIT_MIN = "0" }
      elseif ($line -match '^\s*tunnel\s*=\s*([A-Za-z0-9._-]+)\s*$') { $tunnel = $Matches[1] }
      elseif ($line -match '^\s*url\s*=\s*(https?://\S+)\s*$') { $env:EXTRUXY_PUBLIC_URL = $Matches[1] }   # dia chi hien o ma QR tren header
    }
  }
  if ($ip -ne "localhost") { $env:EXTRUXY_LAN_URL = "http://${ip}:${port}" }                              # ma QR thu hai: dia chi trong mang nha
  if ($tunnel) { $env:EXTRUXY_IDLE_EXIT_MIN = "0" }     # co duong ham thi server khong tu tat (neu tat, cloudflared mo coi); tat bang icon Tat
  if ($netHosts.Count -gt 0) { $env:EXTRUXY_ALLOWED_HOSTS = $env:EXTRUXY_ALLOWED_HOSTS + "," + ($netHosts -join ",") }
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
  # Duong ham Cloudflare: chay an cung server, ghi loi vao data\tunnel-loi.txt. Khong co cloudflared thi bo qua (van chay trong LAN).
  # May mang theo (SSD): launcher\cloudflared.exe + chia khoa data\cloudflared\*.json -> chay thang bang chia khoa, khong can config.yml.
  # May chinh: cloudflared da cai + config.yml o thu muc nguoi dung (cach cu, giu lam du phong).
  if ($tunnel) {
    $cf = Join-Path $PSScriptRoot "cloudflared.exe"
    if (-not (Test-Path $cf)) { $g = Get-Command cloudflared -ErrorAction SilentlyContinue; $cf = if ($g) { $g.Source } else { $null } }
    $key = Get-ChildItem (Join-Path $root "data\cloudflared") -Filter *.json -File -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($cf) {
      $cfArgs = if ($key) { @("tunnel","--no-autoupdate","run","--cred-file",$key.FullName,"--url","http://localhost:$port",$tunnel) } else { @("tunnel","run",$tunnel) }
      Start-Process $cf -WindowStyle Hidden -ArgumentList $cfArgs -RedirectStandardError (Join-Path $root "data\tunnel-loi.txt")
    }
  }
}
# Server da chay tu truoc ma IP may da doi (doi mang): server khong nhan IP moi -> mo localhost (luon vao duoc tren may nay).
# Vua tu bat thi IP chac chan dung, khoi hoi lai.
$url = "http://${ip}:${port}"
if (-not $started) {
  try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 "$url/api/health" | Out-Null } catch { $url = "http://localhost:${port}" }
}
Start-Process $url
