Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & WshShell.CurrentDirectory & "\.venv\Scripts\pythonw.exe" & chr(34) & " -m voxtype.app", 0, False
