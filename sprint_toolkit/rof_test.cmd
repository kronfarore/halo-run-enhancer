@echo off
rem Rate-of-fire rule test: swap the staged test levels into MCC and back.
rem
rem   rof_test.cmd rof     [game]   install the test level (plasma weapon at the start, flat 24/s;
rem                                 Halo 2: 30/s), god shield, run x2, the cheat weapon
rem   rof_test.cmd reca    [game]   FIRE RECOVERY test A: a held automatic, 30/s, recovery 5 ticks
rem   rof_test.cmd recb    [game]   FIRE RECOVERY test B: one shot a pull HELD, 30/s, recovery 3.4 ticks
rem   rof_test.cmd restore [game]   put back the map that was live before the test
rem
rem [game] = halo2 / halo3 / halo3odst / haloreach / halo4 (default: all five).
rem Built by rof_test_stage.py into E:\HaloBackups\rof_test (staged.json lists the expected readings).
rem Installing a test copy over YOUR map saves it to ...\live_before first (a marker in ...\installed
rem says a test copy is live, so switching tests keeps your map); restore puts it back.
rem MCC can stay open; only the level being swapped must not be running (quit to the menu).
rem
rem THE TEST: pick up the plasma weapon at your start (Halo 4: the Storm Rifle), hold the trigger
rem from cold, and note the BATTERY number when it overheats -- or "empty, never overheated".
rem   about 72 = the game fires its tag rate      about 46 = a 60 Hz reset rule
rem   empty    = the 30 Hz reset rule (Halo 1 / 2)
rem   Halo 2:  about 71 = Halo 2 fires 30/s       empty    = Halo 2 caps at 15/s
rem   about 91 (any game) = the heat does not drain while firing: tell Claude, the test needs a rework
rem RECA (hold the trigger from cold, battery at the overheat):
rem   about 71 = the recovery does NOT slow a held automatic   about 42 = ignored, but capped at 15/s
rem   empty    = the recovery gates every shot (6/s)            about 80 = heat does not drain while firing
rem RECB (HOLD the trigger from cold, battery at the overheat):
rem   about 78 = rounded down / to nearest (10/s)   about 57 = exact time (8.8/s)
rem   empty    = rounded UP (7.5/s)                 one shot per pull = a held one-shot trigger does not repeat
rem   about 94 = heat does not drain while firing
rem
rem   Halo 2  01b Cairo Station    Halo 3  100 The Covenant    ODST  h100 Mombasa Streets
rem   Reach   m60 The Package      Halo 4  m40_invasion Reclaimer
setlocal EnableDelayedExpansion
set "MCC=C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection"
set "ST=E:\HaloBackups\rof_test"
set "MODE=%~1"
set "ONLY=%~2"
if /i not "%MODE%"=="rof" if /i not "%MODE%"=="reca" if /i not "%MODE%"=="recb" if /i not "%MODE%"=="restore" (
    echo usage: %~nx0 rof^|reca^|recb^|restore [halo2^|halo3^|halo3odst^|haloreach^|halo4]
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
    if exist "%ST%\installed\%REL%.txt" del "%ST%\installed\%REL%.txt"
    echo   %REL%: restored
    exit /b 0
)
if not exist "%ST%\%MODE%\%REL%" (
    echo   %REL%: not staged - run rof_test_stage.py --kind=%MODE% first
    set /a FAILED+=1
    exit /b 0
)
rem no marker = the live map is the user's own (maybe patched since the last test): save it afresh
if not exist "%ST%\installed\%REL%.txt" (
    for %%D in ("%ST%\live_before\%REL%") do if not exist "%%~dpD" mkdir "%%~dpD"
    copy /y "%LIVE%" "%ST%\live_before\%REL%" >nul && echo   %REL%: live map saved to live_before
)
copy /y "%ST%\%MODE%\%REL%" "%LIVE%" >nul || (set /a FAILED+=1 & echo   FAILED %REL% & exit /b 0)
for %%D in ("%ST%\installed\%REL%.txt") do if not exist "%%~dpD" mkdir "%%~dpD"
echo %MODE%> "%ST%\installed\%REL%.txt"
echo   %REL%: %MODE% copy installed
exit /b 0
