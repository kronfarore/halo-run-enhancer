@echo off
rem ODST Armed-card test map (odst_armed_test.py: the test cases at the start, god shield, carbine cheat, run x2).
rem   h3_armed_test.cmd deploy  [level]   put <level>_armed_test.map in place
rem   h3_armed_test.cmd restore [level]   put the live map back
rem Level defaults to sc120 (Kizingo Boulevard). The live map is kept aside as <level>.map.pre_armed.
rem No parenthesised blocks: the path contains "(x86)", whose ")" would end one.
setlocal
set "LVL=%~2"
if "%LVL%"=="" set "LVL=sc120"
set "MAPS=%~dp0..\..\halo3odst\maps"
if /i "%~1"=="deploy" goto deploy
if /i "%~1"=="restore" goto restore
echo usage: %~nx0 deploy^|restore [level]
exit /b 1

:deploy
if not exist "%MAPS%\%LVL%_armed_test.map" goto notest
if not exist "%MAPS%\%LVL%.map.pre_armed" copy /y "%MAPS%\%LVL%.map" "%MAPS%\%LVL%.map.pre_armed" >nul
copy /y "%MAPS%\%LVL%_armed_test.map" "%MAPS%\%LVL%.map" >nul
echo Test map deployed. Live %LVL% saved as %LVL%.map.pre_armed
exit /b 0

:restore
if not exist "%MAPS%\%LVL%.map.pre_armed" goto norestore
copy /y "%MAPS%\%LVL%.map.pre_armed" "%MAPS%\%LVL%.map" >nul
del "%MAPS%\%LVL%.map.pre_armed"
echo Live %LVL% restored.
exit /b 0

:notest
echo Test map missing: %LVL%_armed_test.map
exit /b 1

:norestore
echo Nothing to restore - %LVL%.map.pre_armed not found.
exit /b 1
