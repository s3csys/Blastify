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
        logger.info("Please download the appropriate ChromeDriver for your Chrome version and place it in this directory.")
        return False
    
    # Check if ChromeDriver is executable (Linux/Mac)
    if os.name != 'nt' and not os.access(chromedriver_path, os.X_OK):
        logger.error(f"ChromeDriver exists but is not executable: {chromedriver_path}")
        logger.info("Please make it executable with: chmod +x chromedriver")
        return False
    
    # Try to start Chrome browser
    try:
        logger.info(f"Using ChromeDriver from: {chromedriver_path}")
        
        # Set up Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Initialize Chrome driver
        service = Service(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Get Chrome and ChromeDriver versions
        chrome_version = driver.capabilities['browserVersion']
        chromedriver_version = driver.capabilities['chrome']['chromedriverVersion'].split(' ')[0]
        
        logger.info(f"Successfully started Chrome browser")
        logger.info(f"Chrome version: {chrome_version}")
        logger.info(f"ChromeDriver version: {chromedriver_version}")
        
        # Check if versions match
        if not chrome_version.startswith(chromedriver_version.split('.')[0]):
            logger.warning(f"Chrome version ({chrome_version}) and ChromeDriver version ({chromedriver_version}) may not be compatible.")
            logger.warning("For best results, use a ChromeDriver version that matches your Chrome browser version.")
        
        # Clean up
        driver.quit()
        return True
        
    except Exception as e:
        logger.error(f"Failed to start Chrome browser: {str(e)}")
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