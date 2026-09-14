@echo off
rem rebuild_reach.cmd -- rebuild the Reach campaign maps with the HREK and finish the
rem recipe: build, install, residency fix, pool-cache warm, publish the baseline.
rem Roughly an hour for all ten; builds have long silent stretches and look hung when
rem they are not. Stay out of Reach in MCC while it runs.
rem
rem   rebuild_reach.cmd              every mission
rem   rebuild_reach.cmd m20,m45      just these (comma separated, no spaces)
rem
rem To keep a log instead of watching the console:
rem   rebuild_reach.cmd > rebuild_reach.log 2>&1

setlocal
set "HERE=%~dp0"
set "PY=%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe"
if not exist "%PY%" set "PY=python"
set "PYTHONUNBUFFERED=1"
set "QT_QPA_PLATFORM=offscreen"

if "%~1"=="" (
    echo ==== rebuilding every Reach mission
    "%PY%" "%HERE%sprint_toolkit\reach_ek_build.py" --all
) else (
    echo ==== rebuilding %~1
    "%PY%" "%HERE%sprint_toolkit\reach_ek_build.py" --all --maps %~1
)
set "RC=%ERRORLEVEL%"
echo ==== build finished, exit code %RC%

rem The standing residency check: anything the rebuild left half-loaded shows here.
"%PY%" "%HERE%sprint_toolkit\reach_pools.py" --audit
exit /b %RC%
