@echo off
rem Halo 3 Armed-card test map (h3_armed_test.py: the test cases at the start, god shield, carbine cheat, run x2).
rem   h3_armed_test.cmd deploy  [level]   put <level>_armed_test.map in place
rem   h3_armed_test.cmd restore [level]   put the live map back
rem Level defaults to 010_jungle. The live map is kept aside as <level>.map.pre_armed.
rem No parenthesised blocks: the path contains "(x86)", whose ")" would end one.
setlocal
set "LVL=%~2"
if "%LVL%"=="" set "LVL=010_jungle"
set "MAPS=%~dp0..\..\halo3\maps"
if /i "%~1"=="deploy" goto deploy
if /i "%~1"=="restore" goto restore
echo usage: %~nx0 deploy^|restore [level]
exit /b 1

:deploy
if not exist "%MAPS%\%LVL%_armed_test.map" goto notest
if not exist "%MAPS%\%LVL%.map.pre_armed" copy /y "%MAPS%\%LVL%.map" "%MAPS%\%LVL%.map.pre_armed" >nul
copy /y "%MAPS%\%LVL%_armed_test.map" "%MAPS%\%LVL%.map" >nul || goto locked
echo Test map deployed. Live %LVL% saved as %LVL%.map.pre_armed
exit /b 0

:restore
if not exist "%MAPS%\%LVL%.map.pre_armed" goto norestore
copy /y "%MAPS%\%LVL%.map.pre_armed" "%MAPS%\%LVL%.map" >nul || goto locked
del "%MAPS%\%LVL%.map.pre_armed"
echo Live %LVL% restored.
exit /b 0

:locked
echo The map is in use (a level is open in MCC): leave the level, then run this again. Nothing was deleted.
exit /b 1

:notest
echo Test map missing: %LVL%_armed_test.map
exit /b 1

:norestore
echo Nothing to restore - %LVL%.map.pre_armed not found.
exit /b 1
