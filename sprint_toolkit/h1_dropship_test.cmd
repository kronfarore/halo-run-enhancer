@echo off
rem Halo 1 DROPSHIP test map (a30 opening dropship carries 8 species, one per seat; h1_dropship_test.py).
rem   h1_dropship_test.cmd deploy  [level]   put <level>_dropship_test.map in place
rem   h1_dropship_test.cmd restore [level]   put the live map back
rem Level defaults to a30. The live map is kept aside as <level>.map.pre_dropship.
rem No parenthesised blocks: the path contains "(x86)", whose ")" would end one.
setlocal
set "LVL=%~2"
if "%LVL%"=="" set "LVL=a30"
set "MAPS=%~dp0..\..\halo1\maps"
if /i "%~1"=="deploy" goto deploy
if /i "%~1"=="restore" goto restore
echo usage: %~nx0 deploy^|restore [level]
exit /b 1

:deploy
if not exist "%MAPS%\%LVL%_dropship_test.map" goto notest
if not exist "%MAPS%\%LVL%.map.pre_dropship" copy /y "%MAPS%\%LVL%.map" "%MAPS%\%LVL%.map.pre_dropship" >nul
copy /y "%MAPS%\%LVL%_dropship_test.map" "%MAPS%\%LVL%.map" >nul
echo Test map deployed. Live %LVL% saved as %LVL%.map.pre_dropship
exit /b 0

:restore
if not exist "%MAPS%\%LVL%.map.pre_dropship" goto norestore
copy /y "%MAPS%\%LVL%.map.pre_dropship" "%MAPS%\%LVL%.map" >nul
del "%MAPS%\%LVL%.map.pre_dropship"
echo Live %LVL% restored.
exit /b 0

:notest
echo Test map missing: %LVL%_dropship_test.map
exit /b 1

:norestore
echo Nothing to restore - %LVL%.map.pre_dropship not found.
exit /b 1
