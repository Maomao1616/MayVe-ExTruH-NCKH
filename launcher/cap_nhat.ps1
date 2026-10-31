# VMU PlotterPen - cap nhat: chi thay backend/, frontend/, launcher/; giu nguyen Python/ va data/.
# Goi tu "Cap nhat.bat" o thu muc goc. Ban cap nhat = file .zip moi nhat dat canh "Cap nhat.bat"
# (tao bang tools/dong_goi.ps1 -Kieu capnhat). Ban cu duoc cat vao _ban_cu/ de quay lai neu can.
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
function Fail($msg) { Write-Host ""; Write-Host "LOI: $msg" -ForegroundColor Red; exit 1 }

$zip = Get-ChildItem -Path $root -Filter *.zip -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $zip) { Fail "Khong thay file .zip ban cap nhat trong $root. Chep file zip vao day roi chay lai." }
Write-Host "Ban cap nhat: $($zip.Name)"

Write-Host "1/5 Tat server..."
& (Join-Path $PSScriptRoot "stop.ps1")
Start-Sleep -Seconds 1

Write-Host "2/5 Giai nen..."
$tmp = Join-Path $env:TEMP "vmu_plotterpen_capnhat"
if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
Expand-Archive -Path $zip.FullName -DestinationPath $tmp
$main = Get-ChildItem -Path $tmp -Recurse -Filter main.py -File |
        Where-Object { $_.Directory.Name -eq "app" -and $_.Directory.Parent.Name -eq "backend" } | Select-Object -First 1
if (-not $main) { Fail "File zip khong co backend\app\main.py: khong phai ban cap nhat VMU PlotterPen." }
$src = $main.Directory.Parent.Parent.FullName
if (-not (Test-Path (Join-Path $src "frontend\index.html"))) { Fail "File zip thieu frontend\index.html." }

Write-Host "3/5 Cat ban cu vao _ban_cu\ ..."
$bak = Join-Path $root "_ban_cu"
if (Test-Path $bak) { Remove-Item -Recurse -Force $bak }
New-Item -ItemType Directory -Path $bak | Out-Null
$oldReq = ""
$reqPath = Join-Path $root "backend\requirements.txt"
if (Test-Path $reqPath) { $oldReq = Get-Content $reqPath -Raw }

Write-Host "4/5 Thay backend, frontend, launcher..."
foreach ($d in "backend", "frontend", "launcher") {
  $from = Join-Path $src $d
  $to = Join-Path $root $d
  if (-not (Test-Path $from)) { continue }
  if (Test-Path $to) {
    robocopy $to (Join-Path $bak $d) /E /XD .venv __pycache__ /NFL /NDL /NJH /NJS /NP | Out-Null
  }
  # /MIR: thu muc dich giong het ban moi (xoa tep thua); .venv va __pycache__ khong bi dung toi
  robocopy $from $to /MIR /XD .venv __pycache__ /NFL /NDL /NJH /NJS /NP | Out-Null
  if ($LASTEXITCODE -ge 8) { Fail "Chep $d bi loi (robocopy $LASTEXITCODE). Ban cu con nguyen trong _ban_cu\$d." }
}
Move-Item -Force $zip.FullName (Join-Path $bak $zip.Name)
Remove-Item -Recurse -Force $tmp

Write-Host "5/5 Kiem tra thu vien..."
$newReq = Get-Content $reqPath -Raw
if ($newReq -ne $oldReq) {
  Write-Host "    requirements.txt da doi: cai them thu vien (can Internet)..."
  # cung Python ma start.ps1 dung: Python\ mang theo, khong co thi backend\.venv
  $python = Join-Path $root "Python\python.exe"
  if (-not (Test-Path $python)) { $python = Join-Path $root "backend\.venv\Scripts\python.exe" }
  if (-not (Test-Path $python)) { Fail "Khong tim thay Python (Python\ hoac backend\.venv) de cai thu vien." }
  & $python -m pip install --no-warn-script-location -r $reqPath
  if ($LASTEXITCODE -ne 0) { Fail "Cai thu vien bi loi. Kiem tra Internet roi chay lai Cap nhat (ban moi da chep xong)." }
} else {
  Write-Host "    Thu vien khong doi."
}
Write-Host ""
Write-Host "XONG. Bam icon VMU PlotterPen de chay ban moi." -ForegroundColor Green
Write-Host "Ban cu va file zip da dung nam trong _ban_cu\ (xoa duoc khi ban moi chay on)."
