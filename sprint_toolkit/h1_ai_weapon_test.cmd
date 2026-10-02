@echo off
rem Halo 1 AI-weapon test maps.
rem   h1_ai_weapon_test.cmd deploy  [level]   put <level>_aiweapon_test.map in place
rem   h1_ai_weapon_test.cmd restore [level]   put the live map back
rem Level defaults to b30. The live map is kept aside as <level>.map.pre_aiweapon.
rem No parenthesised blocks: the path contains "(x86)", whose ")" would end one.
setlocal
set "LVL=%~2"
if "%LVL%"=="" set "LVL=b30"
set "MAPS=%~dp0..\..\halo1\maps"
if /i "%~1"=="deploy" goto deploy
if /i "%~1"=="restore" goto restore
echo usage: %~nx0 deploy^|restore [level]
exit /b 1

:deploy
if not exist "%MAPS%\%LVL%_aiweapon_test.map" goto notest
if not exist "%MAPS%\%LVL%.map.pre_aiweapon" copy /y "%MAPS%\%LVL%.map" "%MAPS%\%LVL%.map.pre_aiweapon" >nul
copy /y "%MAPS%\%LVL%_aiweapon_test.map" "%MAPS%\%LVL%.map" >nul
echo Test map deployed. Live %LVL% saved as %LVL%.map.pre_aiweapon
exit /b 0

:restore
if not exist "%MAPS%\%LVL%.map.pre_aiweapon" goto norestore
copy /y "%MAPS%\%LVL%.map.pre_aiweapon" "%MAPS%\%LVL%.map" >nul
del "%MAPS%\%LVL%.map.pre_aiweapon"
echo Live %LVL% restored.
exit /b 0

:notest
echo Test map missing: %LVL%_aiweapon_test.map
exit /b 1

:norestore
echo Nothing to restore - %LVL%.map.pre_aiweapon not found.
exit /b 1
