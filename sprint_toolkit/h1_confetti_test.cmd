@echo off
rem Grunt Birthday Party CONFETTI test (h1_confetti_effect.py), a30, classic graphics.
rem   h1_confetti_test.cmd show       halo1.dll patch state (must say on) + the effect it prefers
rem   h1_confetti_test.cmd restore    put the live a30 back (the map the test copy replaced)
rem The test copy is a fresh a30 build carrying effects\grunt birthday party; it is staged
rem already. Patch a run in the enhancer afterwards as usual.
setlocal
if /i "%~1"=="show" goto show
if /i "%~1"=="restore" goto restore
echo usage: %~nx0 show^|restore
exit /b 1

:show
python "%~dp0h1_birthday_party.py" --show
exit /b %errorlevel%

:restore
python "%~dp0h1_port_test_map.py" --restore a30
exit /b %errorlevel%
