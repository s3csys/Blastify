# ChromeDriver Setup Instructions

This directory is used to store ChromeDriver executables for different operating systems. The application will automatically detect your operating system and use the appropriate ChromeDriver executable.

## Setup Instructions

### Automatic Setup

#### For Windows

Run the setup script from the project root directory:
```batch
app_data\chromedriver\setup_chromedriver.bat
```

You can also specify a specific Chrome version (if different from the default):
```batch
app_data\chromedriver\setup_chromedriver.bat 139.0.6045.21
```

#### For Linux/macOS

Run the setup script from the project root directory:
```bash
chmod +x app_data/chromedriver/setup_chromedriver.sh
./app_data/chromedriver/setup_chromedriver.sh
```

You can also specify a specific Chrome version (if different from the default):
```bash
./app_data/chromedriver/setup_chromedriver.sh 139.0.6045.21
```

The setup scripts include robust error handling and will provide detailed output if any issues occur during the download, extraction, or installation process.

### Manual Setup

#### For Windows

1. Download the appropriate ChromeDriver for your Chrome version from:
   - Chrome for Testing: https://googlechromelabs.github.io/chrome-for-testing/
   - Or direct link for Chrome 138: https://storage.googleapis.com/chrome-for-testing-public/138.0.7204.94/win64/chromedriver-win64.zip

2. Extract the ZIP file and place the `chromedriver.exe` file in this directory.

#### For Linux

1. Ensure Chrome or Chromium is installed on your system. If not, you can install it using:
   ```bash
   # For Debian/Ubuntu
   sudo apt install google-chrome-stable
   # OR
   sudo apt install chromium-browser
   
   # For Fedora/RHEL
   sudo dnf install google-chrome-stable
   
   # For Arch Linux
   sudo pacman -S chromium
   ```
   
   Alternatively, you can use the provided installation script:
   ```bash
   sudo ./app_data/chromedriver/install_chrome_linux.sh
   ```

2. Download the appropriate ChromeDriver for your Chrome version from:
   - Chrome for Testing: https://googlechromelabs.github.io/chrome-for-testing/
   - Or direct link for Chrome 138: https://storage.googleapis.com/chrome-for-testing-public/138.0.7204.94/linux64/chromedriver-linux64.zip

3. Extract the ZIP file and place the `chromedriver` file in this directory.

4. Make the ChromeDriver executable:
   ```bash
   chmod +x chromedriver
   ```

#### For macOS

1. Download the appropriate ChromeDriver for your Chrome version from:
   - Chrome for Testing: https://googlechromelabs.github.io/chrome-for-testing/
   - For Intel Macs: https://storage.googleapis.com/chrome-for-testing-public/138.0.7204.94/mac-x64/chromedriver-mac-x64.zip
   - For Apple Silicon (M1/M2) Macs: https://storage.googleapis.com/chrome-for-testing-public/138.0.7204.94/mac-arm64/chromedriver-mac-arm64.zip

2. Extract the ZIP file and place the `chromedriver` file in this directory.

3. Make the ChromeDriver executable:
   ```bash
   chmod +x chromedriver
   ```

## Verifying Your Setup

You can verify that ChromeDriver is properly set up by running the check script:

### For Windows

```batch
python app_data\chromedriver\check_chromedriver.py
```

### For Linux/macOS

```bash
python app_data/chromedriver/check_chromedriver.py
```

This script will check if ChromeDriver exists, is executable, and can successfully start a Chrome browser. It will also report the Chrome and ChromeDriver versions and warn you if they might not be compatible.

## Troubleshooting

If you encounter a "session not created" error, it means your ChromeDriver version doesn't match your Chrome browser version. Download the matching ChromeDriver version and replace the existing one in this directory.

If no specific ChromeDriver is found in this directory, the application will fall back to using webdriver-manager, which will attempt to download the appropriate driver automatically.

### Setup Script Errors

The setup scripts include improved error handling and will provide detailed error messages if something goes wrong:

- **Permission Issues**: If the script cannot write to the destination directory, it will display an error message. You may need to run the script with administrator/sudo privileges.
- **Download Failures**: If the ChromeDriver download fails, the script will check your internet connection and Chrome version.
- **Extraction Problems**: If the ZIP file cannot be extracted, the script will report this error.
- **File Location Issues**: The script will search for the chromedriver executable in multiple locations within the extracted files.
- **Verification Failures**: After installation, the script verifies that the chromedriver is executable and working.

### Common Issues and Solutions

1. **ChromeDriver not found in expected location**:
   - Re-run the setup script
   - Check if your antivirus software is blocking the download or execution

2. **ChromeDriver exists but is not executable** (Linux/macOS):
   - Run `chmod 755 app_data/chromedriver/chromedriver`

3. **Chrome version mismatch**:
   - Check your Chrome version by visiting `chrome://version/` in your browser
   - Run the setup script with your specific Chrome version as a parameter

4. **Chrome not installed or not in PATH**:
   - Install Google Chrome or ensure it's in your system PATH
   - On Linux, you can use the provided script to install Chrome automatically:
     ```bash
     sudo ./app_data/chromedriver/install_chrome_linux.sh
     ```
   - This script will detect your Linux distribution and install the appropriate Chrome package

5. **Temporary directory issues**:
   - The script now handles temporary directory cleanup more robustly
   - If you see errors related to temporary directories, try running the script again

6. **Security or permission errors**:
   - On Windows, try running the script as Administrator
   - On Linux/macOS, try using sudo: `sudo ./app_data/chromedriver/setup_chromedriver.sh`



If you encounter issues with the setup scripts, check the error messages for clues about what went wrong. The scripts also output debugging information like file listings to help diagnose problems.

### Common Issues

1. **ChromeDriver not found**: Make sure you've placed the correct ChromeDriver executable in this directory.

2. **ChromeDriver not executable (Linux/macOS)**: Run `chmod +x chromedriver` to make it executable.

3. **Version mismatch**: Ensure your ChromeDriver version matches your Chrome browser version. The major version numbers should match (e.g., Chrome 138.x.xxxx.xx should use ChromeDriver 138.x.xxxx.xx).

4. **Permission issues**: On some systems, you might need to run the application with elevated privileges or adjust the permissions of the ChromeDriver executable.