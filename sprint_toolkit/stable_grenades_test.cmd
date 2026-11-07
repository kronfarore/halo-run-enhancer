@echo off
rem Stable Grenades in-game test: swap the staged test levels into MCC and back.
rem
rem   stable_grenades_test.cmd vanilla [game]   the level as a normal patch leaves it, no card
rem   stable_grenades_test.cmd stable  [game]   the same level with Stable Grenades on every grenade
rem   stable_grenades_test.cmd itemonly halo2   Halo 2 only: the card's item-flag write alone
rem                                             (does the eqip flag by itself stop the chain?)
rem   stable_grenades_test.cmd accel [game]     Halo 1 / Halo 2: vanilla + "does accelerate" on the
rem                                             placed grenades (is that flag the placed gate?)
rem Halo 1 copies have the grenade kinds swapped: placed pickups plasma, drops frag.
rem   stable_grenades_test.cmd restore [game]   put back the map that was live before the test
rem
rem [game] = halo1 / halo2 / halo3 / halo3odst / haloreach / halo4 (default: all six).
rem Built by stable_grenades_stage.py into E:\HaloBackups\stable_grenades_test.
rem The first vanilla/stable call saves each live map to ...\live_before (once).
rem MCC can stay open; only the level being swapped must not be running (quit to the menu).
rem
rem   Halo 1  a30 Halo               Halo 2  01b Cairo Station    Halo 3  100 The Covenant
rem   ODST    h100 Mombasa Streets   Reach   m60 The Package      Halo 4  m40_invasion Infinity
setlocal EnableDelayedExpansion
set "MCC=C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection"
set "ST=E:\HaloBackups\stable_grenades_test"
set "MODE=%~1"
set "ONLY=%~2"
if /i not "%MODE%"=="vanilla" if /i not "%MODE%"=="stable" if /i not "%MODE%"=="itemonly" if /i not "%MODE%"=="accel" if /i not "%MODE%"=="restore" (
    echo usage: %~nx0 vanilla^|stable^|itemonly^|accel^|restore [halo1^|halo2^|halo3^|halo3odst^|haloreach^|halo4]
    exit /b 1
)
set FAILED=0
for %%M in (
    "halo1\maps\a30.map"
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
set "ONEGAME="
if /i "%MODE%"=="itemonly" set ONEGAME=1
if /i "%MODE%"=="accel" set ONEGAME=1
if defined ONEGAME if not exist "%ST%\%MODE%\%REL%" (
    echo   %REL%: no %MODE% copy for this game, left as it is
    exit /b 0
)
if not exist "%ST%\%MODE%\%REL%" (
    echo   %REL%: not staged - run stable_grenades_stage.py first
    set /a FAILED+=1
    exit /b 0
)
if not exist "%ST%\live_before\%REL%" (
    for %%D in ("%ST%\live_before\%REL%") do if not exist "%%~dpD" mkdir "%%~dpD"
    copy /y "%LIVE%" "%ST%\live_before\%REL%" >nul && echo   %REL%: live map saved to live_before
)
copy /y "%ST%\%MODE%\%REL%" "%LIVE%" >nul || (set /a FAILED+=1 & echo   FAILED %REL% & exit /b 0)
echo   %REL%: %MODE% copy installed
exit /b 0
