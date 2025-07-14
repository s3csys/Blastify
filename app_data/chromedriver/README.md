# ChromeDriver Setup Instructions

This directory is used to store ChromeDriver executables for different operating systems. The application will automatically detect your operating system and use the appropriate ChromeDriver executable.

## Setup Instructions

### Automatic Setup

#### For Windows

Run the setup script from the project root directory:
```batch
app_data\chromedriver\setup_chromedriver.bat
```

#### For Linux/macOS

Run the setup script from the project root directory:
```bash
chmod +x app_data/chromedriver/setup_chromedriver.sh
./app_data/chromedriver/setup_chromedriver.sh
```

### Manual Setup

#### For Windows

1. Download the appropriate ChromeDriver for your Chrome version from:
   - Chrome for Testing: https://googlechromelabs.github.io/chrome-for-testing/
   - Or direct link for Chrome 138: https://storage.googleapis.com/chrome-for-testing-public/138.0.7204.94/win64/chromedriver-win64.zip

2. Extract the ZIP file and place the `chromedriver.exe` file in this directory.

#### For Linux

1. Download the appropriate ChromeDriver for your Chrome version from:
   - Chrome for Testing: https://googlechromelabs.github.io/chrome-for-testing/
   - Or direct link for Chrome 138: https://storage.googleapis.com/chrome-for-testing-public/138.0.7204.94/linux64/chromedriver-linux64.zip

2. Extract the ZIP file and place the `chromedriver` file in this directory.

3. Make the ChromeDriver executable:
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

### Common Issues

1. **ChromeDriver not found**: Make sure you've placed the correct ChromeDriver executable in this directory.

2. **ChromeDriver not executable (Linux/macOS)**: Run `chmod +x chromedriver` to make it executable.

3. **Version mismatch**: Ensure your ChromeDriver version matches your Chrome browser version. The major version numbers should match (e.g., Chrome 138.x.xxxx.xx should use ChromeDriver 138.x.xxxx.xx).

4. **Permission issues**: On some systems, you might need to run the application with elevated privileges or adjust the permissions of the ChromeDriver executable.