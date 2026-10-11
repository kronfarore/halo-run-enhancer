@echo off
rem Grunt Birthday Party live probe (h1_gbp_probe.py), the one-boot test. In a Halo 1 level:
rem   h1_gbp_probe.cmd table     read-only: what the effect hook maps "impact grunt" effects to
rem   h1_gbp_probe.cmd on        log kills / impacts / effects (running MCC only, never the file)
rem   h1_gbp_probe.cmd dump      print the log (also appended to reports\gbp_probe.jsonl)
rem   h1_gbp_probe.cmd clear     empty the log
rem   h1_gbp_probe.cmd off       restore halo1.dll's code in memory
rem Run elevated if it says OpenProcess failed. No parenthesised blocks: "(x86)" in the path.
setlocal
set "PY=%~dp0h1_gbp_probe.py"
if /i "%~1"=="table" goto table
if /i "%~1"=="on" goto on
if /i "%~1"=="off" goto off
if /i "%~1"=="dump" goto dump
if /i "%~1"=="clear" goto clear
echo usage: %~nx0 table^|on^|dump^|clear^|off
exit /b 1

:table
python "%PY%" --table "impact grunt"
python "%PY%" --table "needle"
exit /b %errorlevel%

:on
python "%PY%" --on
exit /b %errorlevel%

:off
python "%PY%" --off
exit /b %errorlevel%

:dump
python "%PY%" --dump
exit /b %errorlevel%

:clear
python "%PY%" --clear
exit /b %errorlevel%
