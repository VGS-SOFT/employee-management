Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd.exe /c F:\employee_management\start_django.bat", 0, False
Set WshShell = Nothing
