"""Standalone test script for WhatsApp QR code generation."""

import sys
import os
import time
import json
import logging
import base64
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def connect_to_whatsapp(headless=True, timeout=60):
    """Connect to WhatsApp Web and get QR code for authentication.
    
    Args:
        headless: Whether to run the browser in headless mode
        timeout: Timeout in seconds for waiting for QR code
        
    Returns:
        Dictionary with connection status and QR code if available
    """
    driver = None
    try:
        # Set up Chrome options
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1280,800")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # Initialize Chrome driver with cross-platform support
        # Check if we should use a specific ChromeDriver path
        chromedriver_dir = os.path.join(os.getcwd(), 'app_data', 'chromedriver')
        
        # Create the directory if it doesn't exist
        os.makedirs(chromedriver_dir, exist_ok=True)
        
        # Determine the correct chromedriver executable based on OS
        if os.name == 'nt':  # Windows
            chromedriver_name = 'chromedriver.exe'
        else:  # Linux/Mac
            chromedriver_name = 'chromedriver'
            
        chromedriver_path = os.path.join(chromedriver_dir, chromedriver_name)
        
        # Check if the specific chromedriver exists, use it if available
        if os.path.exists(chromedriver_path):
            service = Service(executable_path=chromedriver_path)
            logger.info(f"Using ChromeDriver from: {chromedriver_path}")
        else:
            # Fall back to webdriver-manager if no specific driver is available
            logger.info("No specific ChromeDriver found, using webdriver-manager")
            service = Service(ChromeDriverManager().install())
            
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Navigate to WhatsApp Web
        driver.get("https://web.whatsapp.com/")
        
        # Wait for QR code to appear
        try:
            qr_canvas = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, "//canvas[contains(@aria-label, 'Scan me!')]")),
            )
            
            # Get QR code data
            qr_data = driver.execute_script(
                "return arguments[0].toDataURL('image/png');", qr_canvas
            )
            
            # Save QR code to file
            qr_code_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "whatsapp_qr.txt")
            with open(qr_code_path, "w") as f:
                f.write(qr_data)
            
            logger.info(f"QR code saved to {qr_code_path}")
            
            return {
                "status": "success",
                "message": "QR code generated successfully",
                "qr_code": qr_data
            }
            
        except TimeoutException:
            # Check if we're already logged in
            if "_wa_wam_authenticated" in driver.get_cookies():
                return {
                    "status": "success",
                    "message": "Already authenticated"
                }
            else:
                return {
                    "status": "failed",
                    "error": "Timeout waiting for QR code"
                }
                
    except Exception as e:
        logger.error(f"Error connecting to WhatsApp Web: {str(e)}")
        return {
            "status": "failed",
            "error": str(e)
        }
    finally:
        if driver:
            driver.quit()

def test_qr_generation():
    """Test QR code generation for WhatsApp."""
    logger.info("Testing WhatsApp QR code generation...")
    
    result = connect_to_whatsapp(headless=True)
    logger.info(f"Connection result: {json.dumps(result, indent=2)}")
    
    if result.get("status") == "success":
        logger.info("Successfully generated QR code")
        logger.info(f"QR code available: {result.get('qr_code') is not None}")
        return True
    else:
        logger.error(f"Failed to connect: {result.get('error')}")
        return False

if __name__ == "__main__":
    test_qr_generation()