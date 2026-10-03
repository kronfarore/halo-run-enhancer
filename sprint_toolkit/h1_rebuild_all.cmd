@echo off
rem Rebuild all Halo 1 campaign maps (classic, self-contained) from HCEEK and ship
rem each one as the enhancer baseline and into halo1\maps.
rem   h1_rebuild_all.cmd                        all 10 levels
rem   h1_rebuild_all.cmd --maps a10,b30         some of them
rem   h1_rebuild_all.cmd --no-ship              build + check only
rem   h1_rebuild_all.cmd --allow-missing-slots  ship levels with fewer than 20 slots
python "%~dp0h1_rebuild_all.py" %*
pause
