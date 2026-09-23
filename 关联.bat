@echo off
rem ============================================================
rem  CathayViewer - per-user file association (HKCU only)
rem  ASCII only. Double-click to run (normal user, no admin).
rem
rem  Windows 10/11 does NOT let a program force the default app.
rem  After this runs, pick CathayViewer once:
rem    Settings > Apps > Default apps > (file type) > CathayViewer
rem  or: right-click a file > Open with > Choose another app >
rem      Always use this app.
rem  This script never touches HKLM and installs no service.
rem ============================================================
setlocal
rem --- Full path of the released exe. Default: next to this script.
set "EXE=%~dp0CathayViewer.exe"
rem If the exe lives somewhere else, edit the next line, e.g.:
rem   set "EXE=D:\CathayViewer\CathayViewer.exe"
set "NAME=CathayViewer Reader"
set "ICON=%EXE%,0"
if not exist "%EXE%" echo [WARN] exe not found: %EXE%  (edit the EXE= line)

rem ---- .pdf ----
reg add "HKCU\Software\Classes\CathayViewer.pdf" /ve /d "%NAME%" /f
reg add "HKCU\Software\Classes\CathayViewer.pdf\DefaultIcon" /ve /d "%ICON%" /f
reg add "HKCU\Software\Classes\CathayViewer.pdf\shell\open\command" /ve /d "\"%EXE%\" \"%%1\"" /f
reg add "HKCU\Software\Classes\.pdf\OpenWithProgids" /v "CathayViewer.pdf" /t REG_NONE /d "" /f

rem ---- .epub ----
reg add "HKCU\Software\Classes\CathayViewer.epub" /ve /d "%NAME%" /f
reg add "HKCU\Software\Classes\CathayViewer.epub\DefaultIcon" /ve /d "%ICON%" /f
reg add "HKCU\Software\Classes\CathayViewer.epub\shell\open\command" /ve /d "\"%EXE%\" \"%%1\"" /f
reg add "HKCU\Software\Classes\.epub\OpenWithProgids" /v "CathayViewer.epub" /t REG_NONE /d "" /f

rem ---- .txt ----
reg add "HKCU\Software\Classes\CathayViewer.txt" /ve /d "%NAME%" /f
reg add "HKCU\Software\Classes\CathayViewer.txt\DefaultIcon" /ve /d "%ICON%" /f
reg add "HKCU\Software\Classes\CathayViewer.txt\shell\open\command" /ve /d "\"%EXE%\" \"%%1\"" /f
reg add "HKCU\Software\Classes\.txt\OpenWithProgids" /v "CathayViewer.txt" /t REG_NONE /d "" /f

rem ---- .md ----
reg add "HKCU\Software\Classes\CathayViewer.md" /ve /d "%NAME%" /f
reg add "HKCU\Software\Classes\CathayViewer.md\DefaultIcon" /ve /d "%ICON%" /f
reg add "HKCU\Software\Classes\CathayViewer.md\shell\open\command" /ve /d "\"%EXE%\" \"%%1\"" /f
reg add "HKCU\Software\Classes\.md\OpenWithProgids" /v "CathayViewer.md" /t REG_NONE /d "" /f

echo.
echo Done. Now open Settings ^> Apps ^> Default apps and pick CathayViewer once.
pause
endlocal
