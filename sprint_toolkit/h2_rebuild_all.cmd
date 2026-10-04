@echo off
rem Rebuild the Halo 2 campaign levels from H2EK and ship each one as the enhancer
rem baseline and into halo2\h2_maps_win64_dx11. 01b_spacestation is skipped (reserved).
rem   h2_rebuild_all.cmd                    every level but 01b
rem   h2_rebuild_all.cmd --maps 03a,03b     some of them
rem   h2_rebuild_all.cmd --include-01b      01b as well
rem   h2_rebuild_all.cmd --no-ship          build + check only
python "%~dp0h2_rebuild_all.py" %*
pause
