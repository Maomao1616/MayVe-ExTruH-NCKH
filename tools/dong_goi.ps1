# VMU PlotterPen - dong goi tren may phat trien (chay: powershell -ExecutionPolicy Bypass -File tools\dong_goi.ps1).
#   -Kieu capnhat : backend + frontend + launcher (vai tram KB) -> dua cho may dung, chay "Cap nhat.bat"
#   -Kieu daydu   : them Python\ (da cai thu vien), "Cap nhat.bat", README (~300-500 MB)
# Bo qua .venv, __pycache__, .pytest_cache, tests. File zip nam trong export\ (khong len Git).
param([ValidateSet("capnhat", "daydu")][string]$Kieu = "capnhat")
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$stamp = Get-Date -Format "yyyyMMdd-HHmm"
$name = "VMU_PlotterPen_$Kieu-$stamp"
$stage = Join-Path $env:TEMP $name
if (Test-Path $stage) { Remove-Item -Recurse -Force $stage }
New-Item -ItemType Directory -Path $stage | Out-Null

$dirs = @("backend", "frontend", "launcher")
if ($Kieu -eq "daydu") {
  if (-not (Test-Path (Join-Path $root "Python\Lib\site-packages\fastapi"))) {
    throw "Python\ chua cai thu vien (thieu Lib\site-packages\fastapi). Xem README muc Dong goi."
  }
  $dirs += "Python"
}
foreach ($d in $dirs) {
  robocopy (Join-Path $root $d) (Join-Path $stage $d) /E /XD .venv __pycache__ .pytest_cache tests /XF *.pyc /NFL /NDL /NJH /NJS /NP | Out-Null
  if ($LASTEXITCODE -ge 8) { throw "Chep $d bi loi (robocopy $LASTEXITCODE)." }
}
if ($Kieu -eq "daydu") {
  Copy-Item (Join-Path $root "Cap nhat.bat"), (Join-Path $root "README.md") $stage
}

$out = Join-Path $root "export"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$zip = Join-Path $out "$name.zip"
if (Test-Path $zip) { Remove-Item -Force $zip }
# Tu ghi tung tep voi ten dung "/" (Compress-Archive va ZipFile cua PowerShell 5.1 ghi "\": giai nen tren Linux bi sai)
Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem
$archive = [IO.Compression.ZipFile]::Open($zip, [IO.Compression.ZipArchiveMode]::Create)
try {
  Get-ChildItem -Path $stage -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($stage.Length + 1).Replace("\", "/")
    [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $_.FullName, $rel, [IO.Compression.CompressionLevel]::Optimal) | Out-Null
  }
} finally { $archive.Dispose() }
Remove-Item -Recurse -Force $stage
Write-Host "Da tao: $zip ($([math]::Round((Get-Item $zip).Length / 1MB, 1)) MB)"
