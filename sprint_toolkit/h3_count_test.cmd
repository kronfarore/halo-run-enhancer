@echo off
rem Halo 3 enemy-count test map (010: every enemy fire-team the cards would grow x2 actors).
rem   h3_count_test.cmd deploy  [level]   put <level>_count_test.map in place
rem   h3_count_test.cmd restore [level]   put the live map back
rem Level defaults to 010_jungle. The live map is kept aside as <level>.map.pre_count.
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
if not exist "%MAPS%\%LVL%_count_test.map" goto notest
if not exist "%MAPS%\%LVL%.map.pre_count" copy /y "%MAPS%\%LVL%.map" "%MAPS%\%LVL%.map.pre_count" >nul
copy /y "%MAPS%\%LVL%_count_test.map" "%MAPS%\%LVL%.map" >nul
echo Test map deployed. Live %LVL% saved as %LVL%.map.pre_count
exit /b 0

:restore
if not exist "%MAPS%\%LVL%.map.pre_count" goto norestore
copy /y "%MAPS%\%LVL%.map.pre_count" "%MAPS%\%LVL%.map" >nul
del "%MAPS%\%LVL%.map.pre_count"
echo Live %LVL% restored.
exit /b 0

:notest
echo Test map missing: %LVL%_count_test.map
exit /b 1

:norestore
echo Nothing to restore - %LVL%.map.pre_count not found.
exit /b 1
