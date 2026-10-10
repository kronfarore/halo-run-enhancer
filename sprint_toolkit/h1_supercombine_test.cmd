@echo off
rem Supercombine count per projectile (h1_supercombine_count.py), the one-boot test.
rem   h1_supercombine_test.cmd on       halo1.dll patch on (running MCC + file)
rem   h1_supercombine_test.cmd 3        in game: the needler's needle supercombines at 3
rem   h1_supercombine_test.cmd 0        in game: back to the engine's 7
rem   h1_supercombine_test.cmd show     patch state + the loaded level's counts
rem   h1_supercombine_test.cmd off      halo1.dll back to stock
rem Run elevated if it says OpenProcess failed. No parenthesised blocks: "(x86)" in the path.
setlocal
set "PY=%~dp0h1_supercombine_count.py"
if /i "%~1"=="on" goto on
if /i "%~1"=="off" goto off
if /i "%~1"=="show" goto show
if "%~1"=="" goto usage
python "%PY%" --count "weapons\needler\needle" %~1
exit /b %errorlevel%

:on
python "%PY%" --on
exit /b %errorlevel%

:off
python "%PY%" --off
exit /b %errorlevel%

:show
python "%PY%" --show
python "%PY%" --count
exit /b %errorlevel%

:usage
echo usage: %~nx0 on^|off^|show^|^<count^>
exit /b 1
