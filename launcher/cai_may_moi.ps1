# VMU PlotterPen - cai may moi: tao lai backend\.venv bang Python 3.12 cua MAY NAY roi cai thu vien (can Internet, vai phut).
# Goi tu "Cai may moi.bat" o thu muc goc. Khi nao can: sang may khac (venv ghi cung duong dan Python cua may cu nen hong),
# hoac venv bi loi. Dang chay duoc thi khong lam gi (khong xoa venv tot).
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$venv = Join-Path $root "backend\.venv"
$venvPy = Join-Path $venv "Scripts\python.exe"
function Fail($msg) { Write-Host ""; Write-Host "LOI: $msg" -ForegroundColor Red; exit 1 }

function Test-Python([string]$p) {
  if (-not (Test-Path $p)) { return $false }
  try {
    $pr = Start-Process $p -ArgumentList "-c","`"import fastapi, uvicorn`"" -Wait -PassThru -WindowStyle Hidden
    return ($pr.ExitCode -eq 0)
  } catch { return $false }
}

Write-Host "1/4 Kiem tra moi truong hien tai..."
if (Test-Python $venvPy) { Write-Host "backend\.venv dang chay duoc. Khong can lam gi." -ForegroundColor Green; exit 0 }
$embedded = Join-Path $root "Python\python.exe"
if (Test-Python $embedded) { Write-Host "Python\ (ban mang theo) dang chay duoc. Khong can lam gi." -ForegroundColor Green; exit 0 }

Write-Host "2/4 Tim Python 3.12 64-bit tren may..."
# cmd /c de loi cua py.exe (khong co Python 3.12) khong lam PowerShell dung
$exe = (cmd /c 'py -3.12-64 -c "import sys; print(sys.executable)" 2>nul') | Select-Object -First 1
if (-not $exe -or -not (Test-Path $exe)) {
  $exe = (cmd /c 'python -c "import sys; print(sys.executable if sys.version_info[:2]==(3,12) else chr(0))" 2>nul') | Select-Object -First 1
}
if (-not $exe -or -not (Test-Path $exe)) { Fail "May nay chua co Python 3.12 (64-bit). Cai tu python.org (chon 'Add python.exe to PATH') roi chay lai." }
Write-Host "Dung: $exe"

Write-Host "3/4 Tao backend\.venv (xoa ban hong neu co)..."
if (Test-Path $venv) { Remove-Item -Recurse -Force $venv }
& $exe -m venv $venv
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $venvPy)) { Fail "Khong tao duoc backend\.venv." }

Write-Host "4/4 Cai thu vien (can Internet, vai phut)..."
& $venvPy -m pip install --disable-pip-version-check -r (Join-Path $root "backend\requirements.txt")
if ($LASTEXITCODE -ne 0) { Fail "Cai thu vien that bai (kiem tra Internet roi chay lai)." }
# Cong cu chay test (pytest...): nho, can khi sua ma tren may nay. Loi o buoc nay khong chan viec chay phan mem.
$dev = Join-Path $root "backend\requirements-dev.txt"
if (Test-Path $dev) {
  & $venvPy -m pip install --disable-pip-version-check -r $dev
  if ($LASTEXITCODE -ne 0) { Write-Host "Canh bao: khong cai duoc cong cu test (requirements-dev.txt). Phan mem van chay." -ForegroundColor Yellow }
}

if (-not (Test-Python $venvPy)) { Fail "Da cai xong nhung chua chay duoc. Gui thong bao loi cho nguoi ho tro." }
Write-Host ""
Write-Host "XONG. Bam icon VMU PlotterPen de bat." -ForegroundColor Green
