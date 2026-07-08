@echo off
rem ---- Creates a "Mission Control" shortcut on your Desktop (VBScript method) ----
rem Run this ONCE from inside the mission-control folder.
cd /d "%~dp0"
set VBS=%TEMP%\mc_shortcut.vbs
> "%VBS%" echo Set ws = CreateObject("WScript.Shell")
>>"%VBS%" echo desktop = ws.SpecialFolders("Desktop")
>>"%VBS%" echo Set lnk = ws.CreateShortcut(desktop ^& "\Mission Control.lnk")
>>"%VBS%" echo lnk.TargetPath = "%~dp0start_dashboard.bat"
>>"%VBS%" echo lnk.WorkingDirectory = "%~dp0"
>>"%VBS%" echo lnk.IconLocation = "%~dp0mission_control.ico"
>>"%VBS%" echo lnk.WindowStyle = 7
>>"%VBS%" echo lnk.Description = "Mission Control Dashboard"
>>"%VBS%" echo lnk.Save
>>"%VBS%" echo WScript.Echo "Desktop shortcut created: " ^& desktop ^& "\Mission Control.lnk"
cscript //nologo "%VBS%"
del "%VBS%" >nul 2>nul
pause
