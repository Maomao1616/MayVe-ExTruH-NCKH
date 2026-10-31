' VMU PlotterPen - chay MOT LAN tren may moi: tao icon "VMU PlotterPen" ngoai Desktop.
' Tao tai cho vi file .lnk ghi duong dan tuyet doi (giai nen o dau cung dung).
Set sh = CreateObject("WScript.Shell")
here = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
Set lnk = sh.CreateShortcut(sh.SpecialFolders("Desktop") & "\VMU PlotterPen.lnk")
lnk.TargetPath = "wscript.exe"
lnk.Arguments = """" & here & "\start.vbs"""
lnk.IconLocation = here & "\icon.ico"
lnk.WorkingDirectory = here
lnk.Description = "Bat VMU PlotterPen"
lnk.Save
MsgBox "Da tao icon VMU PlotterPen ngoai Desktop.", 64, "VMU PlotterPen"
