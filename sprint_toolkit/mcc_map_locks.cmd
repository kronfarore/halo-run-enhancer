@echo off
rem mcc_map_locks.cmd -- list the map files MCC holds open right now (READ-ONLY).
rem Writes nothing to MCC or any map; appends one row per open map to
rem reports\mcc_map_locks.jsonl with the note you give it.
rem
rem   mcc_map_locks.cmd "H3 010 mid-mission"
rem   mcc_map_locks.cmd "H3 summary screen after 010"

setlocal
set "HERE=%~dp0"
set "PY=%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" -u "%HERE%mcc_map_locks.py" --scan --note "%~1"
pause
