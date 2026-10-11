@echo off
rem Grunt Birthday Party in classic graphics (h1_birthday_party.py), the one-boot test.
rem   h1_birthday_party_test.cmd on      halo1.dll patch on (running MCC + file)
rem   h1_birthday_party_test.cmd show    patch state + the effect it spawns
rem   h1_birthday_party_test.cmd off     halo1.dll back to stock
rem Run elevated if it says OpenProcess failed. No parenthesised blocks: "(x86)" in the path.
setlocal
set "PY=%~dp0h1_birthday_party.py"
if /i "%~1"=="on" goto on
if /i "%~1"=="off" goto off
if /i "%~1"=="show" goto show
echo usage: %~nx0 on^|off^|show
exit /b 1

:on
python "%PY%" --on
exit /b %errorlevel%

:off
python "%PY%" --off
exit /b %errorlevel%

:show
python "%PY%" --show
exit /b %errorlevel%
