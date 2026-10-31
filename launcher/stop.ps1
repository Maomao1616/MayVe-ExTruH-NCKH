# VMU PlotterPen - tat server dang nghe cong 8000 (kem tien trinh con xu ly anh).
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue |
  ForEach-Object { taskkill /PID $_.OwningProcess /T /F | Out-Null }
