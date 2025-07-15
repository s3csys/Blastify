#!/bin/bash

echo "WhatsApp QR Code Test Utility"
echo "==========================="
echo 

# Create logs directory if it doesn't exist
mkdir -p logs

echo "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "Python is not installed. Please install Python 3.7 or higher."
    exit 1
fi

echo "Checking dependencies..."
if ! python3 -c "import zxingcpp; print('zxingcpp version:', zxingcpp.__version__)" &> /dev/null; then
    echo "zxingcpp is not installed. Installing required dependencies..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Failed to install dependencies. Please run 'pip3 install -r requirements.txt' manually."
        exit 1
    fi
fi

echo 
echo "Running QR code generation test..."
echo 

python3 -m app.utils.qr_test --data="https://web.whatsapp.com" --output="test_qr.png" --scan

echo 
echo "Test completed. Check the logs directory for generated images and test results."
echo "If you're still experiencing issues, please refer to WHATSAPP_QR_TROUBLESHOOTING.md"
echo 

read -p "Press Enter to continue..."