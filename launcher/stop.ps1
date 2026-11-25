# VMU PlotterPen - tat server dang nghe cong 8000 (kem tien trinh con xu ly anh) va duong ham Cloudflare (neu co).
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue |
  ForEach-Object { taskkill /PID $_.OwningProcess /T /F | Out-Null }
# Chi tat cloudflared chay DUNG ten duong ham trong data\mang.txt (dong tunnel=...), khong dung tien trinh khac.
$netFile = Join-Path (Split-Path $PSScriptRoot -Parent) "data\mang.txt"
$tunnel = $null
if (Test-Path $netFile) {
  foreach ($line in Get-Content $netFile) { if ($line -match '^\s*tunnel\s*=\s*([A-Za-z0-9._-]+)\s*$') { $tunnel = $Matches[1] } }
}
if ($tunnel) {
  Get-CimInstance Win32_Process -Filter "Name='cloudflared.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match ('\btunnel\b.*\brun\b.*\b' + [regex]::Escape($tunnel) + '(\s|$)') } |
    ForEach-Object { taskkill /PID $_.ProcessId /T /F | Out-Null }
}
