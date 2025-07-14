#!/bin/bash

# Script to download and set up ChromeDriver for Linux

# Default to Chrome 138 if no version specified
CHROME_VERSION=${1:-"138.0.7204.94"}
echo "Setting up ChromeDriver for Chrome version $CHROME_VERSION"

# Create temporary directory
TMP_DIR=$(mktemp -d)
cd $TMP_DIR

# Download ChromeDriver
echo "Downloading ChromeDriver $CHROME_VERSION for Linux..."
wget https://storage.googleapis.com/chrome-for-testing-public/$CHROME_VERSION/linux64/chromedriver-linux64.zip

# Extract the zip file
echo "Extracting ChromeDriver..."
unzip chromedriver-linux64.zip

# Move the chromedriver executable to the app_data/chromedriver directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "Moving ChromeDriver to $SCRIPT_DIR"
cp chromedriver-linux64/chromedriver "$SCRIPT_DIR/"

# Make it executable
chmod +x "$SCRIPT_DIR/chromedriver"

# Clean up
cd -
rm -rf $TMP_DIR

echo "ChromeDriver setup complete. The executable is located at: $SCRIPT_DIR/chromedriver"