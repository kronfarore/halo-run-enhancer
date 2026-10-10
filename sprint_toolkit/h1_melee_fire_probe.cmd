@echo off
rem Halo 1 melee + fire probe: logs the player's melee state and the weapon's trigger
rem control to sprint_toolkit\out\melee_fire_probe.jsonl. Start it, then load a30.
rem   h1_melee_fire_probe.cmd [seconds]     default 120 s, counted from the mission load
setlocal
set "SECS=%~1"
if "%SECS%"=="" set "SECS=120"
python "%~dp0h1_melee_fire_probe.py" --seconds %SECS% --note "a30 hammer/sword melee+fire"
pause
