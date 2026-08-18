@echo off
REM Launch the Halo Run Enhancer from wherever this file sits, so it works from a
REM shortcut or a double-click without the working directory having to be right --
REM the tool resolves halo.json and the maps relative to its own folder.
cd /d "%~dp0"

python halo_enhancer.py
if errorlevel 1 (
    echo.
    echo The enhancer exited with an error ^(code %errorlevel%^).
    echo If this says "python is not recognized", install Python and tick
    echo "Add python.exe to PATH", or run:  py halo_enhancer.py
    echo.
    pause
)
