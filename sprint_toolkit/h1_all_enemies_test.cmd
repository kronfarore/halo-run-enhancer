@echo off
rem Halo 1 ALL-ENEMIES test map (every Covenant squad cycled over all 40 enemy variants, god shield; h1_all_enemies.py test).
rem   h1_all_enemies_test.cmd deploy  [level]   put <level>_allenemies_test.map in place
rem   h1_all_enemies_test.cmd restore [level]   put the live map back
rem Level defaults to a10. The live map is kept aside as <level>.map.pre_allenemies.
rem No parenthesised blocks: the path contains "(x86)", whose ")" would end one.
setlocal
set "LVL=%~2"
if "%LVL%"=="" set "LVL=a10"
set "MAPS=%~dp0..\..\halo1\maps"
if /i "%~1"=="deploy" goto deploy
if /i "%~1"=="restore" goto restore
echo usage: %~nx0 deploy^|restore [level]
exit /b 1

:deploy
if not exist "%MAPS%\%LVL%_allenemies_test.map" goto notest
if not exist "%MAPS%\%LVL%.map.pre_allenemies" copy /y "%MAPS%\%LVL%.map" "%MAPS%\%LVL%.map.pre_allenemies" >nul
copy /y "%MAPS%\%LVL%_allenemies_test.map" "%MAPS%\%LVL%.map" >nul
echo Test map deployed. Live %LVL% saved as %LVL%.map.pre_allenemies
exit /b 0

:restore
if not exist "%MAPS%\%LVL%.map.pre_allenemies" goto norestore
copy /y "%MAPS%\%LVL%.map.pre_allenemies" "%MAPS%\%LVL%.map" >nul
del "%MAPS%\%LVL%.map.pre_allenemies"
echo Live %LVL% restored.
exit /b 0

:notest
echo Test map missing: %LVL%_allenemies_test.map
exit /b 1

:norestore
echo Nothing to restore - %LVL%.map.pre_allenemies not found.
exit /b 1
