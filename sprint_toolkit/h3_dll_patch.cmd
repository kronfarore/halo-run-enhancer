@echo off
rem h3_dll_patch.cmd -- halo3.dll patches (verify-before-write, backup to halo3.dll.bak).
rem Close MCC completely first; restart it afterwards.
rem
rem   h3_dll_patch.cmd                 show each patch's state
rem   h3_dll_patch.cmd on              apply no-next-map-prefetch (EXPERIMENTAL)
rem   h3_dll_patch.cmd off             revert it
rem
rem no-next-map-prefetch: Halo 3 stops opening the next level while you play the
rem current one, so the next map can be patched on the summary screen.

setlocal
set "HERE=%~dp0"
set "PY=%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe"
if not exist "%PY%" set "PY=python"
if /i "%~1"=="on"  "%PY%" "%HERE%h3_dll_patch.py" --apply no-next-map-prefetch
if /i "%~1"=="off" "%PY%" "%HERE%h3_dll_patch.py" --revert no-next-map-prefetch
"%PY%" "%HERE%h3_dll_patch.py" --list
pause
