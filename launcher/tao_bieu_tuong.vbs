' VMU PlotterPen - chay MOT LAN tren may moi: tao icon "VMU PlotterPen" ngoai Desktop.
' Tao tai cho vi file .lnk ghi duong dan tuyet doi (giai nen o dau cung dung).
Set sh = CreateObject("WScript.Shell")
here = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
Set lnk = sh.CreateShortcut(sh.SpecialFolders("Desktop") & "\VMU PlotterPen.lnk")
lnk.TargetPath = "wscript.exe"
lnk.Arguments = """" & here & "\start.vbs"""
' icon.ico phai la file .ico that (doi duoi tu .png se khong hien): xem docs/DONG_GOI.md muc 4
lnk.IconLocation = here & "\icon.ico,0"
lnk.WorkingDirectory = here
lnk.Description = "Bat VMU PlotterPen"
lnk.Save
' Windows nho icon cu trong bo dem: lam moi de icon moi hien ngay
sh.Run "ie4uinit.exe -show", 0, False
MsgBox "Da tao icon VMU PlotterPen ngoai Desktop.", 64, "VMU PlotterPen"
