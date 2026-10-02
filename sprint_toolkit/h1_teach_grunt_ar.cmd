@echo off
rem Teach the Grunt's animation graph the assault rifle ('ar', copied from its plasma
rem rifle 'pr' set) in a BUILT Halo 1 level. Run after building the level with the
rem grunt "... with assault rifle" variants in Sapien. Default level: b30.
rem   h1_teach_grunt_ar.cmd          -> halo1\maps\b30.map
rem   h1_teach_grunt_ar.cmd c10      -> halo1\maps\c10.map
rem No parenthesised blocks: the path contains "(x86)", whose ")" would end one.
setlocal
set "LVL=%~1"
if "%LVL%"=="" set "LVL=b30"
set "MAP=%~dp0..\..\halo1\maps\%LVL%.map"
if not exist "%MAP%" goto missing
"%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe" "%~dp0h1_teach_weapon.py" --map "%MAP%" --out "%MAP%" --antr "*grunt*" --donor pr --label ar
exit /b %errorlevel%

:missing
echo No such map: "%MAP%"
exit /b 1
