@echo off
rem h3_dll_patch.cmd -- halo3.dll patches (verify-before-write, backup to halo3.dll.bak).
rem Close MCC completely first; restart it afterwards.
rem
rem   h3_dll_patch.cmd                 show each patch's state
rem   h3_dll_patch.cmd on              apply no-next-map-prefetch v3 (EXPERIMENTAL),
rem                                    removing the older v1 / v2 if they are there
rem   h3_dll_patch.cmd off             revert all of them
rem
rem no-next-map-prefetch: Halo 3 stops opening the next level while you play the
rem current one, so the next map can be patched on the summary screen.

setlocal
set "HERE=%~dp0"
set "PY=%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe"
if not exist "%PY%" set "PY=python"
if /i "%~1"=="on"  "%PY%" "%HERE%h3_dll_patch.py" --revert v1-worker-skip-BROKEN --revert v2-state2-only --apply no-next-map-prefetch
if /i "%~1"=="off" "%PY%" "%HERE%h3_dll_patch.py" --revert v1-worker-skip-BROKEN --revert v2-state2-only --revert no-next-map-prefetch
"%PY%" "%HERE%h3_dll_patch.py" --list
pause
