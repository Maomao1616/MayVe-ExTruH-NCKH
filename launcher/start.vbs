' VMU PlotterPen - bat server (chay an) roi mo trinh duyet. Bam dup icon tren Desktop se chay file nay.
Set sh = CreateObject("WScript.Shell")
here = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
sh.Run "powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & here & "\start.ps1""", 0, False
