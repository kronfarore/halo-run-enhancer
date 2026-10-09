@echo off
rem Explosion visual-size test (fx_visual_test.py): the frag grenade's explosion drawn x3.
rem   fx_visual_test.cmd deploy  h2^|h3^|odst^|reach^|h4   build from the live map, put it in place
rem   fx_visual_test.cmd restore h2^|h3^|odst^|reach^|h4   put the live map back
rem Levels: h2 03a_oldmombasa, h3 010_jungle, odst sc100, reach m10, h4 m10_crash.
rem The live map is kept aside as <level>.map.pre_fxscale.
rem No parenthesised blocks: the path contains "(x86)", whose ")" would end one.
setlocal
set "MCC=%~dp0..\.."
if /i "%~2"=="h2" set "GAME=Halo 2" & set "DIR=%MCC%\halo2\h2_maps_win64_dx11" & set "LVL=03a_oldmombasa"
if /i "%~2"=="h3" set "GAME=Halo 3" & set "DIR=%MCC%\halo3\maps" & set "LVL=010_jungle"
if /i "%~2"=="odst" set "GAME=Halo 3: ODST" & set "DIR=%MCC%\halo3odst\maps" & set "LVL=sc100"
if /i "%~2"=="reach" set "GAME=Halo Reach" & set "DIR=%MCC%\haloreach\maps" & set "LVL=m10"
if /i "%~2"=="h4" set "GAME=Halo 4" & set "DIR=%MCC%\halo4\maps" & set "LVL=m10_crash"
if not defined GAME goto usage
if /i "%~1"=="deploy" goto deploy
if /i "%~1"=="restore" goto restore
:usage
echo usage: %~nx0 deploy^|restore h2^|h3^|odst^|reach^|h4
exit /b 1

:deploy
python "%~dp0fx_visual_test.py" build "%GAME%"
if errorlevel 1 goto failed
if not exist "%DIR%\%LVL%.map.pre_fxscale" copy /y "%DIR%\%LVL%.map" "%DIR%\%LVL%.map.pre_fxscale" >nul
copy /y "%DIR%\%LVL%_fxscale_test.map" "%DIR%\%LVL%.map" >nul
echo Test map deployed (%GAME% %LVL%). Live map saved as %LVL%.map.pre_fxscale
exit /b 0

:restore
if not exist "%DIR%\%LVL%.map.pre_fxscale" goto nothing
copy /y "%DIR%\%LVL%.map.pre_fxscale" "%DIR%\%LVL%.map" >nul
del "%DIR%\%LVL%.map.pre_fxscale"
echo Live %LVL% restored.
exit /b 0

:nothing
echo No test deployed for %LVL%.
exit /b 0

:failed
echo Build failed -- nothing deployed.
exit /b 1
