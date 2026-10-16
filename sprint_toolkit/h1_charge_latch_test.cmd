@echo off
rem Charge weapons wait for the trigger to be released (h1_charge_latch.py), the one-boot test.
rem   h1_charge_latch_test.cmd on         halo1.dll patch on (running MCC + file)
rem   h1_charge_latch_test.cmd rail       in game: the Railgun opts in (live tag write)
rem   h1_charge_latch_test.cmd laser      in game: the Spartan Laser opts in (live tag write)
rem   h1_charge_latch_test.cmd rail off   in game: the Railgun back to stock behaviour
rem   h1_charge_latch_test.cmd show       patch state + the loaded charge weapons
rem   h1_charge_latch_test.cmd off        halo1.dll back to stock
rem Run elevated if it says OpenProcess failed. No parenthesised blocks: "(x86)" in the path.
setlocal
set "PY=%~dp0h1_charge_latch.py"
set "STATE=on"
if /i "%~2"=="off" set "STATE=off"
if /i "%~1"=="on" goto on
if /i "%~1"=="off" goto off
if /i "%~1"=="show" goto show
if /i "%~1"=="rail" goto rail
if /i "%~1"=="laser" goto laser
echo usage: h1_charge_latch_test.cmd on ^| off ^| show ^| rail [off] ^| laser [off]
exit /b 1

:on
python "%PY%" --on
exit /b %errorlevel%

:off
python "%PY%" --off
exit /b %errorlevel%

:show
python "%PY%" --show
python "%PY%" --flag
exit /b %errorlevel%

:rail
python "%PY%" --flag "weapons\railgun\railgun" %STATE%
exit /b %errorlevel%

:laser
python "%PY%" --flag "weapons\spartan laser\spartan laser" %STATE%
exit /b %errorlevel%
