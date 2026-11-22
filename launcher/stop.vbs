' VMU PlotterPen - tat server bang tay (thuong khong can: server tu tat sau 10 phut khi da dong het trang).
Set sh = CreateObject("WScript.Shell")
here = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
sh.Run "powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & here & "\stop.ps1""", 0, True
MsgBox "Da tat VMU PlotterPen.", 64, "VMU PlotterPen"
