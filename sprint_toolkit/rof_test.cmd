@echo off
rem Rate-of-fire rule test: swap the staged test levels into MCC and back.
rem
rem   rof_test.cmd rof     [game]   install the test level (plasma weapon at the start, flat 24/s;
rem                                 Halo 2: 30/s), god shield, run x2, the cheat weapon
rem   rof_test.cmd restore [game]   put back the map that was live before the test
rem
rem [game] = halo2 / halo3 / halo3odst / haloreach / halo4 (default: all five).
rem Built by rof_test_stage.py into E:\HaloBackups\rof_test (staged.json lists the expected readings).
rem The first rof call saves each live map to ...\live_before (once).
rem MCC can stay open; only the level being swapped must not be running (quit to the menu).
rem
rem THE TEST: pick up the plasma weapon at your start (Halo 4: the Storm Rifle), hold the trigger
rem from cold, and note the BATTERY number when it overheats -- or "empty, never overheated".
rem   about 72 = the game fires its tag rate      about 46 = a 60 Hz reset rule
rem   empty    = the 30 Hz reset rule (Halo 1 / 2)
rem   Halo 2:  about 71 = Halo 2 fires 30/s       empty    = Halo 2 caps at 15/s
rem   about 91 (any game) = the heat does not drain while firing: tell Claude, the test needs a rework
rem
rem   Halo 2  01b Cairo Station    Halo 3  100 The Covenant    ODST  h100 Mombasa Streets
rem   Reach   m60 The Package      Halo 4  m40_invasion Reclaimer
setlocal EnableDelayedExpansion
set "MCC=C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection"
set "ST=E:\HaloBackups\rof_test"
set "MODE=%~1"
set "ONLY=%~2"
if /i not "%MODE%"=="rof" if /i not "%MODE%"=="restore" (
    echo usage: %~nx0 rof^|restore [halo2^|halo3^|halo3odst^|haloreach^|halo4]
    exit /b 1
)
set FAILED=0
for %%M in (
    "halo2\h2_maps_win64_dx11\01b_spacestation.map"
    "halo3\maps\100_citadel.map"
    "halo3odst\maps\h100.map"
    "haloreach\maps\m60.map"
    "halo4\maps\m40_invasion.map"
) do (
    for /f "tokens=1 delims=\" %%G in ("%%~M") do set "GAME=%%G"
    if "%ONLY%"=="" (set DO=1) else (if /i "!GAME!"=="%ONLY%" (set DO=1) else (set DO=0))
    if "!DO!"=="1" call :one "%%~M"
)
if "%FAILED%"=="0" (echo Done: %MODE%.) else (echo %FAILED% map^(s^) failed - is that level running? Quit to the menu and run again.)
exit /b %FAILED%

:one
set "REL=%~1"
set "LIVE=%MCC%\%REL%"
if /i "%MODE%"=="restore" (
    if not exist "%ST%\live_before\%REL%" (
        echo   %REL%: nothing saved, left as it is
        exit /b 0
    )
    copy /y "%ST%\live_before\%REL%" "%LIVE%" >nul || (set /a FAILED+=1 & echo   FAILED %REL% & exit /b 0)
    echo   %REL%: restored
    exit /b 0
)
if not exist "%ST%\rof\%REL%" (
    echo   %REL%: not staged - run rof_test_stage.py first
    set /a FAILED+=1
    exit /b 0
)
if not exist "%ST%\live_before\%REL%" (
    for %%D in ("%ST%\live_before\%REL%") do if not exist "%%~dpD" mkdir "%%~dpD"
    copy /y "%LIVE%" "%ST%\live_before\%REL%" >nul && echo   %REL%: live map saved to live_before
)
copy /y "%ST%\rof\%REL%" "%LIVE%" >nul || (set /a FAILED+=1 & echo   FAILED %REL% & exit /b 0)
echo   %REL%: rof copy installed
exit /b 0
