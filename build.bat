@echo off
chcp 65001 >nul
echo ============================================
echo WMS Stock Scheduler Build and Deploy
echo ============================================
echo.

set DEPLOY_DIR=deploy

echo [1/6] Cleaning previous build...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "%DEPLOY_DIR%" rmdir /s /q "%DEPLOY_DIR%"
echo Done
echo.

echo [2/6] Building with PyInstaller...
pyinstaller --clean wms-stock-scheduler.spec
if %errorlevel% neq 0 (
    echo Build failed!
    pause
    exit /b 1
)
echo Build completed
echo.

echo [3/6] Creating deploy folder...
mkdir "%DEPLOY_DIR%"
mkdir "%DEPLOY_DIR%\repository"
echo Done
echo.

echo [4/6] Copying executable...
if exist "dist\WMS-Stock-Scheduler.exe" (
    copy "dist\WMS-Stock-Scheduler.exe" "%DEPLOY_DIR%\" >nul
    echo WMS-Stock-Scheduler.exe copied
) else (
    echo ERROR: Executable not found!
    pause
    exit /b 1
)
echo.

echo [5/6] Copying files...
if exist "config.env" (
    copy "config.env" "%DEPLOY_DIR%\config.env" >nul
    echo config.env copied
)
if exist "repository\stock_export.sql" (
    copy "repository\stock_export.sql" "%DEPLOY_DIR%\repository\" >nul
    echo stock_export.sql copied
)
echo.

echo [6/6] Creating guide...
echo WMS Stock Scheduler Usage Guide > "%DEPLOY_DIR%\README.txt"
echo ============================== >> "%DEPLOY_DIR%\README.txt"
echo. >> "%DEPLOY_DIR%\README.txt"
echo 1. Edit config.env file >> "%DEPLOY_DIR%\README.txt"
echo 2. Run: WMS-Stock-Scheduler.exe >> "%DEPLOY_DIR%\README.txt"
echo Done
echo.

echo ============================================
echo Build and Deploy Complete!
echo ============================================
echo.
echo Deploy folder: %DEPLOY_DIR%\
echo.
pause
