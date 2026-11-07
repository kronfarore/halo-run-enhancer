@echo off
rem next_map_prefetch.cmd -- ODST / Reach / Halo 4: stop the engine opening the NEXT map
rem while you play, so it can be patched on the summary screen (EXPERIMENTAL).
rem Halo 3 has its own: h3_dll_patch.cmd. Close MCC completely first; restart afterwards.
rem
rem   next_map_prefetch.cmd                  show each game's state
rem   next_map_prefetch.cmd on odst          apply (odst, reach, h4 -- one or several)
rem   next_map_prefetch.cmd off odst         revert

setlocal
set "HERE=%~dp0"
set "PY=%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe"
if not exist "%PY%" set "PY=python"
set "ACT=%~1"
shift
set "GAMES="
:args
if "%~1"=="" goto run
set "GAMES=%GAMES% %~1"
shift
goto args
:run
if /i "%ACT%"=="on"  "%PY%" "%HERE%next_map_prefetch.py" --apply%GAMES%
if /i "%ACT%"=="off" "%PY%" "%HERE%next_map_prefetch.py" --revert%GAMES%
if "%ACT%"=="" "%PY%" "%HERE%next_map_prefetch.py"
pause
