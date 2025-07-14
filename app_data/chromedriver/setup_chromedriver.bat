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

REM Check if download was successful
if not exist chromedriver-win64.zip (
    echo Error: Failed to download ChromeDriver. Please check your internet connection and Chrome version.
    exit /b 1
)

REM Extract the zip file using PowerShell
echo Extracting ChromeDriver...
powershell -Command "& {Expand-Archive -Path 'chromedriver-win64.zip' -DestinationPath '.' -Force}"

REM Check if extraction was successful
if %ERRORLEVEL% NEQ 0 (
    echo Error: Failed to extract ChromeDriver zip file.
    exit /b 1
)

REM List extracted contents for debugging
echo Extracted files:
dir /b

REM Get the script directory
set SCRIPT_DIR=%~dp0

REM Move the chromedriver executable to the app_data/chromedriver directory
echo Moving ChromeDriver to %SCRIPT_DIR%

REM Check if we have write permissions to the destination directory
echo Testing write permissions to %SCRIPT_DIR%
>nul 2>nul (echo test > "%SCRIPT_DIR%test_permission" && del "%SCRIPT_DIR%test_permission") || (
    echo Error: Cannot write to %SCRIPT_DIR%. Please run this script as administrator or check permissions.
    exit /b 1
)

REM Check if the expected path exists
if exist chromedriver-win64\chromedriver.exe (
    copy /Y chromedriver-win64\chromedriver.exe "%SCRIPT_DIR%"
    echo Copied from chromedriver-win64\chromedriver.exe
) else if exist chromedriver-win64\chromedriver-win64\chromedriver.exe (
    copy /Y chromedriver-win64\chromedriver-win64\chromedriver.exe "%SCRIPT_DIR%"
    echo Copied from chromedriver-win64\chromedriver-win64\chromedriver.exe
) else if exist chromedriver.exe (
    copy /Y chromedriver.exe "%SCRIPT_DIR%"
    echo Copied from chromedriver.exe
) else (
    echo Searching for chromedriver.exe in all subdirectories...
    for /r %%i in (chromedriver.exe) do (
        if exist "%%i" (
            echo Found at: %%i
            copy /Y "%%i" "%SCRIPT_DIR%"
            echo Copied from %%i
            goto FoundDriver
        )
    )
    echo Error: Could not find chromedriver.exe in the extracted files
    dir /s chromedriver*.exe
    exit /b 1
)
:FoundDriver

REM Clean up
cd /d %SCRIPT_DIR%
rmdir /S /Q %TMP_DIR%

REM Verify installation
if exist "%SCRIPT_DIR%chromedriver.exe" (
    echo ChromeDriver setup complete. The executable is located at: %SCRIPT_DIR%chromedriver.exe
    echo Version information:
    "%SCRIPT_DIR%chromedriver.exe" --version
    if %ERRORLEVEL% NEQ 0 (
        echo Warning: ChromeDriver was installed but may not be working correctly.
        echo Please check if you have the correct version of Chrome installed.
    )
) else (
    echo Error: ChromeDriver installation failed. The executable was not found.
    echo Checking directory contents:
    dir "%SCRIPT_DIR%"
    exit /b 1
)

pause