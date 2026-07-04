@echo off
REM Build halo_enhancer.exe. Run this from the tool folder on Windows.
setlocal

echo Installing build dependencies...
python -m pip install -r requirements.txt || goto :error

echo Building executable...
python -m PyInstaller --noconfirm halo_enhancer.spec || goto :error

echo.
echo ============================================================
echo  Build complete:  dist\halo_enhancer.exe
echo ============================================================
pause
exit /b 0

:error
echo.
echo Build FAILED. See the messages above.
pause
exit /b 1
