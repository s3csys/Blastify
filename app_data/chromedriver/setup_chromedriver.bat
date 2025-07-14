@echo off
setlocal enabledelayedexpansion

REM Script to download and set up ChromeDriver for Windows

REM Default to Chrome 138 if no version specified
if "%~1"=="" (
    set CHROME_VERSION=138.0.7204.94
) else (
    set CHROME_VERSION=%~1
)

echo Setting up ChromeDriver for Chrome version %CHROME_VERSION%

REM Create temporary directory
set TMP_DIR=%TEMP%\chromedriver_setup
mkdir %TMP_DIR% 2>nul
cd /d %TMP_DIR%

REM Download ChromeDriver using PowerShell
echo Downloading ChromeDriver %CHROME_VERSION% for Windows...
powershell -Command "& {Invoke-WebRequest -Uri 'https://storage.googleapis.com/chrome-for-testing-public/%CHROME_VERSION%/win64/chromedriver-win64.zip' -OutFile 'chromedriver-win64.zip'}"

REM Extract the zip file using PowerShell
echo Extracting ChromeDriver...
powershell -Command "& {Expand-Archive -Path 'chromedriver-win64.zip' -DestinationPath '.' -Force}"

REM Get the script directory
set SCRIPT_DIR=%~dp0

REM Move the chromedriver executable to the app_data/chromedriver directory
echo Moving ChromeDriver to %SCRIPT_DIR%
copy /Y chromedriver-win64\chromedriver.exe "%SCRIPT_DIR%"

REM Clean up
cd /d %SCRIPT_DIR%
rmdir /S /Q %TMP_DIR%

echo ChromeDriver setup complete. The executable is located at: %SCRIPT_DIR%chromedriver.exe

pause