@echo off
rem Dropped items stay longer + longer flashlight (h1_drops_flashlight.py / h2_drops_flashlight.py).
rem All test writes go to the RUNNING MCC only (live); the dll files stay stock.
rem   drops_flashlight_test.cmd h1 short   Halo 1: cleanup at 3 garbage, battery 20 s
rem   drops_flashlight_test.cmd h1 keep    Halo 1: cleanup at 127 garbage, battery 360 s
rem   drops_flashlight_test.cmd h2 short   Halo 2: cleanup at 3, grace 5 s, light on 20 s
rem   drops_flashlight_test.cmd h2 keep    Halo 2: cleanup at 127, grace 120 s, light forever
rem   drops_flashlight_test.cmd h1 probe "note"   log 30 s of live values (one per second)
rem   drops_flashlight_test.cmd h1 show    patch state (file + running MCC)
rem   drops_flashlight_test.cmd h1 off     back to stock (running MCC + file)
rem Run elevated if it says OpenProcess failed. No parenthesised blocks: "(x86)" in the path.
setlocal
set "PY=%~dp0h1_drops_flashlight.py"
if /i "%~1"=="h2" set "PY=%~dp0h2_drops_flashlight.py"
if /i not "%~1"=="h1" if /i not "%~1"=="h2" goto usage
if /i "%~1%~2"=="h1short" goto h1short
if /i "%~1%~2"=="h1keep" goto h1keep
if /i "%~1%~2"=="h2short" goto h2short
if /i "%~1%~2"=="h2keep" goto h2keep
if /i "%~2"=="probe" goto probe
if /i "%~2"=="show" goto show
if /i "%~2"=="off" goto off
:usage
echo usage: drops_flashlight_test.cmd h1^|h2 short ^| keep ^| probe "note" ^| show ^| off
exit /b 1

:h1short
python "%PY%" --live --drop-limit 3 --flashlight 20
exit /b %errorlevel%

:h1keep
python "%PY%" --live --drop-limit 127 --flashlight 360
exit /b %errorlevel%

:h2short
python "%PY%" --live --drop-limit 3 --grace 5 --flashlight 20
exit /b %errorlevel%

:h2keep
python "%PY%" --live --drop-limit 127 --grace 120 --flashlight 0
exit /b %errorlevel%

:probe
python "%PY%" --probe --watch 30 --note "%~3"
exit /b %errorlevel%

:show
python "%PY%" --show
exit /b %errorlevel%

:off
python "%PY%" --off
exit /b %errorlevel%
