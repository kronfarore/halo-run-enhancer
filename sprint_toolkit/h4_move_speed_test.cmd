@echo off
rem Halo 4 enemy move-speed test maps (m10_crash: Covenant x2; m30_cryptum: Knight/Crawler x2; shield x5, grunts green).
rem   h4_move_speed_test.cmd deploy  [level]   put <level>_movespeed_test.map in place
rem   h4_move_speed_test.cmd restore [level]   put the live map back
rem Level defaults to m10_crash (pass m30_cryptum for the other). The live map is kept aside as <level>.map.pre_movespeed.
rem No parenthesised blocks: the path contains "(x86)", whose ")" would end one.
setlocal
set "LVL=%~2"
if "%LVL%"=="" set "LVL=m10_crash"
set "MAPS=%~dp0..\..\halo4\maps"
if /i "%~1"=="deploy" goto deploy
if /i "%~1"=="restore" goto restore
echo usage: %~nx0 deploy^|restore [level]
exit /b 1

:deploy
if not exist "%MAPS%\%LVL%_movespeed_test.map" goto notest
if not exist "%MAPS%\%LVL%.map.pre_movespeed" copy /y "%MAPS%\%LVL%.map" "%MAPS%\%LVL%.map.pre_movespeed" >nul
copy /y "%MAPS%\%LVL%_movespeed_test.map" "%MAPS%\%LVL%.map" >nul
echo Test map deployed. Live %LVL% saved as %LVL%.map.pre_movespeed
exit /b 0

:restore
if not exist "%MAPS%\%LVL%.map.pre_movespeed" goto norestore
copy /y "%MAPS%\%LVL%.map.pre_movespeed" "%MAPS%\%LVL%.map" >nul
del "%MAPS%\%LVL%.map.pre_movespeed"
echo Live %LVL% restored.
exit /b 0

:notest
echo Test map missing: %LVL%_movespeed_test.map
exit /b 1

:norestore
echo Nothing to restore - %LVL%.map.pre_movespeed not found.
exit /b 1
