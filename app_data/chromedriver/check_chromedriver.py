#!/usr/bin/env python
"""
Script to check if ChromeDriver is properly set up and working.

This script will:
1. Check if ChromeDriver exists in the expected location
2. Try to start a Chrome browser using the ChromeDriver
3. Report success or failure
"""

import os
import sys
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_chromedriver():
    """Check if ChromeDriver is properly set up and working."""
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Determine the correct chromedriver executable based on OS
    if os.name == 'nt':  # Windows
        chromedriver_name = 'chromedriver.exe'
    else:  # Linux/Mac
        chromedriver_name = 'chromedriver'
    
    chromedriver_path = os.path.join(script_dir, chromedriver_name)
    
    # Check if ChromeDriver exists
    if not os.path.exists(chromedriver_path):
        logger.error(f"ChromeDriver not found at: {chromedriver_path}")
        logger.info("Please run the setup_chromedriver script to download and install ChromeDriver.")
        
        # Check if setup script exists
        if os.name == 'nt':
            setup_script = os.path.join(script_dir, 'setup_chromedriver.bat')
        else:
            setup_script = os.path.join(script_dir, 'setup_chromedriver.sh')
            
        if os.path.exists(setup_script):
            logger.info(f"You can run: {setup_script}")
        else:
            logger.error(f"Setup script not found: {setup_script}")
            logger.info("Please download the appropriate ChromeDriver for your Chrome version manually.")
        
        return False
    
    # Check if ChromeDriver is executable (Linux/Mac)
    if os.name != 'nt' and not os.access(chromedriver_path, os.X_OK):
        logger.error(f"ChromeDriver exists but is not executable: {chromedriver_path}")
        logger.info("Please make it executable with: chmod +x chromedriver")
        return False
        
    # Check file size to ensure it's not empty or corrupted
    file_size = os.path.getsize(chromedriver_path)
    if file_size < 1000:  # Arbitrary small size that's definitely too small for a valid chromedriver
        logger.error(f"ChromeDriver file exists but appears to be invalid (size: {file_size} bytes)")
        logger.info("Please re-run the setup script to download a valid ChromeDriver.")
        return False
    
    # Try to start Chrome browser
    try:
        logger.info(f"Using ChromeDriver from: {chromedriver_path}")
        
        # Set up Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-gpu")
        
        # Set Chrome binary location for Linux
        if os.name != 'nt':
            # Common Chrome binary locations on Linux
            chrome_locations = [
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/usr/bin/chromium",
                "/usr/bin/chromium-browser",
                "/snap/bin/chromium",
                "/snap/bin/google-chrome"
            ]
            
            for location in chrome_locations:
                if os.path.exists(location):
                    logger.info(f"Found Chrome binary at: {location}")
                    chrome_options.binary_location = location
                    break
            else:
                logger.warning("Could not find Chrome binary in common locations.")
                logger.info("If Chrome is installed in a non-standard location, please specify it manually.")
                # Continue anyway, as Chrome might be in PATH
        
        # Initialize Chrome driver
        service = Service(executable_path=chromedriver_path)
        
        logger.info("Attempting to start Chrome browser...")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Get Chrome and ChromeDriver versions
        chrome_version = driver.capabilities.get('browserVersion', 'unknown')
        chromedriver_version = driver.capabilities.get('chrome', {}).get('chromedriverVersion', 'unknown')
        if chromedriver_version != 'unknown':
            chromedriver_version = chromedriver_version.split(' ')[0]
        
        logger.info(f"Successfully started Chrome browser")
        logger.info(f"Chrome version: {chrome_version}")
        logger.info(f"ChromeDriver version: {chromedriver_version}")
        
        # Check if versions match
        if chrome_version != 'unknown' and chromedriver_version != 'unknown':
            if not chrome_version.startswith(chromedriver_version.split('.')[0]):
                logger.warning(f"Chrome version ({chrome_version}) and ChromeDriver version ({chromedriver_version}) may not be compatible.")
                logger.warning("For best results, use a ChromeDriver version that matches your Chrome browser version.")
                logger.info(f"You can download the appropriate ChromeDriver from: https://googlechromelabs.github.io/chrome-for-testing/")
        
        # Test navigation to a simple page
        logger.info("Testing navigation to a simple page...")
        driver.get("about:blank")
        logger.info("Navigation successful")
        
        # Clean up
        driver.quit()
        return True
        
    except Exception as e:
        logger.error(f"Failed to start Chrome browser: {str(e)}")
        
        # Provide more detailed error messages based on common issues
        error_str = str(e).lower()
        if "chromedriver" in error_str and "executable" in error_str:
            logger.error("The ChromeDriver executable may be corrupted or incompatible with your system.")
            logger.info("Try re-running the setup script to download a fresh copy.")
        elif "chrome not reachable" in error_str or "chrome failed to start" in error_str:
            logger.error("Chrome browser failed to start. This could be due to:")
            logger.info("1. Chrome is not installed on this system")
            logger.info("2. The installed Chrome version is incompatible with this ChromeDriver")
            logger.info("3. System security settings are preventing Chrome from starting")
        elif "session not created" in error_str and "version" in error_str:
            logger.error("Chrome version mismatch detected.")
            logger.info("Please download a ChromeDriver version that matches your Chrome browser version.")
            logger.info("Run 'chrome://version' in your Chrome browser to check your version.")
        elif "cannot find chrome binary" in error_str:
            logger.error("Chrome browser binary not found. Please ensure Chrome is installed.")
            logger.info("On Linux, install Chrome with one of the following commands:")
            logger.info("  - sudo apt install google-chrome-stable  # For Debian/Ubuntu")
            logger.info("  - sudo apt install chromium-browser      # For Debian/Ubuntu Chromium")
            logger.info("  - sudo dnf install google-chrome-stable  # For Fedora/RHEL")
            logger.info("  - sudo pacman -S chromium               # For Arch Linux")
            logger.info("After installation, run this script again.")
            logger.info("If Chrome is already installed but in a non-standard location, edit this script to specify the binary location.")

        
        return False

def main():
    """Main function."""
    logger.info("Checking ChromeDriver setup...")
    
    if check_chromedriver():
        logger.info("ChromeDriver is properly set up and working!")
        return 0
    else:
        logger.error("ChromeDriver setup check failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())