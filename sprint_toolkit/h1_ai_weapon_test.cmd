@echo off
rem Halo 1 AI-weapon test on b30 (The Silent Cartographer).
rem   h1_ai_weapon_test.cmd deploy    put the test map in place (live b30 kept aside)
rem   h1_ai_weapon_test.cmd restore   put the live b30 back
rem Close MCC first is NOT required for maps, but load the level fresh after deploying.
setlocal
set MAPS=%~dp0..\..\halo1\maps
if /i "%~1"=="deploy" goto deploy
if /i "%~1"=="restore" goto restore
echo usage: %~nx0 deploy ^| restore
exit /b 1

:deploy
if not exist "%MAPS%\b30_aiweapon_test.map" (
  echo Test map missing - build it first: python h1_ai_weapon_test.py
  exit /b 1
)
if not exist "%MAPS%\b30.map.pre_aiweapon" copy /y "%MAPS%\b30.map" "%MAPS%\b30.map.pre_aiweapon" >nul
copy /y "%MAPS%\b30_aiweapon_test.map" "%MAPS%\b30.map" >nul
echo Test map deployed. Live b30 saved as b30.map.pre_aiweapon
exit /b 0

:restore
if not exist "%MAPS%\b30.map.pre_aiweapon" (
  echo Nothing to restore - b30.map.pre_aiweapon not found.
  exit /b 1
)
copy /y "%MAPS%\b30.map.pre_aiweapon" "%MAPS%\b30.map" >nul
del "%MAPS%\b30.map.pre_aiweapon"
echo Live b30 restored.
exit /b 0
