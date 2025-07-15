@echo off
echo WhatsApp QR Code Test Utility
echo ===========================
echo.

REM Create logs directory if it doesn't exist
if not exist logs mkdir logs

echo Checking Python installation...
python --version > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Python is not installed or not in PATH. Please install Python 3.7 or higher.
    exit /b 1
)

echo Checking dependencies...
python -c "import zxingcpp; print('zxingcpp version:', zxingcpp.__version__)" > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo zxingcpp is not installed. Installing required dependencies...
    pip install -r requirements.txt
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to install dependencies. Please run 'pip install -r requirements.txt' manually.
        exit /b 1
    )
)

echo.
echo Running QR code generation test...
echo.

python -m app.utils.qr_test --data="https://web.whatsapp.com" --output="test_qr.png" --scan

echo.
echo Test completed. Check the logs directory for generated images and test results.
echo If you're still experiencing issues, please refer to WHATSAPP_QR_TROUBLESHOOTING.md
echo.

pause