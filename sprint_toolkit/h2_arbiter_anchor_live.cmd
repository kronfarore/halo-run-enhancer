@echo off
rem Arbiter flashlight anchor, live (h2_arbiter_anchor_live.py). Patch the level with the
rem Arbiter flashlight option on, start it, then run this ELEVATED:
rem   h2_arbiter_anchor_live.cmd                 04b_floodlab
rem   h2_arbiter_anchor_live.cmd 06a_sentinelwalls
rem In game: F7 next anchor, F8 previous, F9 pick this one, F11 quit.
setlocal
set "LEVEL=%~1"
if "%LEVEL%"=="" set "LEVEL=04b_floodlab"
python "%~dp0h2_arbiter_anchor_live.py" --map "%~dp0..\..\halo2\h2_maps_win64_dx11\%LEVEL%.map"
pause
