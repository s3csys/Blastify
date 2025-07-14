#!/bin/bash

# Script to download and set up ChromeDriver for Linux
# Ensure script is run from its directory
cd "$(dirname "$0")" 2>/dev/null || true

# Default to Chrome 138 if no version specified
CHROME_VERSION=${1:-"138.0.7204.94"}
echo "Setting up ChromeDriver for Chrome version $CHROME_VERSION"

# Create temporary directory
TMP_DIR=$(mktemp -d)
cd $TMP_DIR

# Download ChromeDriver
echo "Downloading ChromeDriver $CHROME_VERSION for Linux..."
wget https://storage.googleapis.com/chrome-for-testing-public/$CHROME_VERSION/linux64/chromedriver-linux64.zip

# Check if download was successful
if [ $? -ne 0 ]; then
    echo "Error: Failed to download ChromeDriver. Please check your internet connection and Chrome version."
    exit 1
fi

# Extract the zip file
echo "Extracting ChromeDriver..."
unzip chromedriver-linux64.zip

# Check if extraction was successful
if [ $? -ne 0 ]; then
    echo "Error: Failed to extract ChromeDriver zip file."
    exit 1
fi

# List extracted contents for debugging
echo "Extracted files:"
ls -la

# Move the chromedriver executable to the app_data/chromedriver directory
# Get the absolute path to the script directory - ensure we're using the correct path
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Double check that SCRIPT_DIR is not a temporary directory
if [[ "$SCRIPT_DIR" == *"/tmp/"* ]]; then
    # If it's a temp directory, try to find the actual app_data/chromedriver directory
    if [ -d "/home/blastify/htdocs/blastify.secsys.site/app_data/chromedriver" ]; then
        SCRIPT_DIR="/home/blastify/htdocs/blastify.secsys.site/app_data/chromedriver"
    fi
fi

# Check if we have write permissions to the destination directory
if [ ! -w "$SCRIPT_DIR" ]; then
    echo "Warning: No write permission to $SCRIPT_DIR"
    # Try to create a test file to verify permissions
    touch "$SCRIPT_DIR/test_permission" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "Error: Cannot write to $SCRIPT_DIR. Please check permissions."
        echo "You may need to run this script with sudo or as a user with write permissions."
        exit 1
    else
        rm "$SCRIPT_DIR/test_permission"
    fi
fi

echo "Moving ChromeDriver to $SCRIPT_DIR"

# Check if the expected path exists
if [ -f "chromedriver-linux64/chromedriver" ]; then
    cp chromedriver-linux64/chromedriver "$SCRIPT_DIR/"
elif [ -d "chromedriver-linux64" ] && [ -f "$(find chromedriver-linux64 -name chromedriver -type f | head -1)" ]; then
    # If directory exists but file is in a subdirectory
    cp "$(find chromedriver-linux64 -name chromedriver -type f | head -1)" "$SCRIPT_DIR/"
elif [ -f "chromedriver" ]; then
    # If chromedriver is directly in the current directory
    cp chromedriver "$SCRIPT_DIR/"
else
    echo "Error: Could not find chromedriver executable in the extracted files"
    exit 1
fi

# Make it executable and ensure proper permissions
chmod 755 "$SCRIPT_DIR/chromedriver"
# Ensure the user has ownership of the file
if [ -x "$(command -v chown)" ]; then
    # Get the current user
    CURRENT_USER=$(whoami)
    chown $CURRENT_USER:$CURRENT_USER "$SCRIPT_DIR/chromedriver" 2>/dev/null || true
fi

# Clean up
# Store the current directory before removing the temp directory
CURRENT_DIR=$(pwd)
cd /
rm -rf $TMP_DIR
# Return to the original directory if needed
cd "$CURRENT_DIR" 2>/dev/null || cd "$SCRIPT_DIR"

# Verify installation
if [ -f "$SCRIPT_DIR/chromedriver" ] && [ -x "$SCRIPT_DIR/chromedriver" ]; then
    echo "ChromeDriver setup complete. The executable is located at: $SCRIPT_DIR/chromedriver"
    echo "Version information:"
    "$SCRIPT_DIR/chromedriver" --version
    exit 0
else
    echo "Error: ChromeDriver installation failed. The executable was not found or is not executable."
    exit 1
fi