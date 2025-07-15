"""WhatsApp Web client implementation."""

import json
import time
import logging
import base64
import threading
import os
import io
import platform
import subprocess
import sys
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any, Union, Tuple

import websocket
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement

# Try to import optional dependencies
try:
    import numpy as np
except ImportError:
    pass

try:
    from PIL import Image
except ImportError:
    pass

try:
    import cv2
except ImportError:
    pass

try:
    import zxingcpp
except ImportError:
    pass

from app import db
from app.models.whatsapp_session import WhatsAppSession, WhatsAppDevice
from app.utils.qr_generator import generate_qr_code

# Configure logger
logger = logging.getLogger(__name__)


def setup_logger():
    """Set up logger with file handler."""
    try:
        # Create logs directory if it doesn't exist
        log_dir = os.path.join(os.getcwd(), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # Create a file handler
        log_file = os.path.join(log_dir, 'whatsapp_client.log')
        file_handler = logging.FileHandler(log_file)
        
        # Set the formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # Set the level
        file_handler.setLevel(logging.DEBUG)
        
        # Add the handler to the logger
        logger.addHandler(file_handler)
        
        # Set the logger level
        logger.setLevel(logging.DEBUG)
        
        logger.info(f"Logger initialized. Log file: {log_file}")
    except Exception as e:
        print(f"Error setting up logger: {str(e)}")


# Set up the logger
setup_logger()


class WhatsAppClient:
    """Client for interacting with WhatsApp Web."""
    
    def __init__(self, session_id: str = None, session_name: str = None):
        """Initialize the WhatsApp client.
        
        Args:
            session_id: The session ID to use (if None, a new session will be created)
            session_name: The name for the session (required if session_id is None)
        """
        # Create logs directory if it doesn't exist
        log_dir = os.path.join(os.getcwd(), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        self.session_id = session_id
        self.session_name = session_name
        self.driver = None
        self.ws = None
        self.ws_thread = None
        self.is_connected = False
        self.qr_code = None
        self.session_data = None
        self.message_callbacks = []
        
        # Load or create session
        self._initialize_session()
    
    def _initialize_session(self):
        """Initialize or load an existing session."""
        if self.session_id:
            self.session = WhatsAppSession.get_session_by_id(self.session_id)
            if not self.session:
                raise ValueError(f"Session with ID {self.session_id} not found")
            self.session_name = self.session.name
        elif self.session_name:
            # Create a new session
            self.session = WhatsAppSession(
                name=self.session_name,
                session_id=f"session_{int(time.time())}",
                status="disconnected"
            )
            db.session.add(self.session)
            db.session.commit()
            self.session_id = self.session.session_id
        else:
            raise ValueError("Either session_id or session_name must be provided")
    
    def _check_chrome_installed(self) -> bool:
        """Check if Chrome is installed on the system.
        
        Returns:
            True if Chrome is installed, False otherwise
        """
        chrome_paths = [
            # Windows paths
            "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
            # Linux paths
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            # macOS paths
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        ]
        
        for path in chrome_paths:
            if os.path.exists(path):
                logger.info(f"Chrome found at: {path}")
                return True
        
        logger.error("Chrome not found in common installation paths")
        return False
    
    def _check_dependencies(self) -> Dict[str, bool]:
        """Check if required dependencies are installed.
        
        Returns:
            Dictionary with dependency status
        """
        dependencies = {
            "PIL": False,
            "cv2": False,
            "zxingcpp": False,
            "numpy": False
        }
        
        # Check PIL/Pillow
        try:
            import PIL
            dependencies["PIL"] = True
            logger.info("PIL/Pillow is installed")
        except ImportError:
            logger.warning("PIL/Pillow is not installed")
        
        # Check OpenCV
        try:
            import cv2
            dependencies["cv2"] = True
            logger.info("OpenCV is installed")
        except ImportError:
            logger.warning("OpenCV is not installed")
        
        # Check zxingcpp
        try:
            import zxingcpp
            dependencies["zxingcpp"] = True
            logger.info("zxingcpp is installed")
        except ImportError:
            logger.warning("zxingcpp is not installed")
        
        # Check numpy
        try:
            import numpy
            dependencies["numpy"] = True
            logger.info("numpy is installed")
        except ImportError:
            logger.warning("numpy is not installed")
        
        return dependencies
    
    def connect(self, headless: bool = True, timeout: int = 60) -> Dict[str, Any]:
        """Connect to WhatsApp Web and get QR code for authentication.
        
        Args:
            headless: Whether to run the browser in headless mode
            timeout: Timeout in seconds for waiting for QR code
            
        Returns:
            Dictionary with connection status and QR code if available
        """
        # Check if Chrome is installed
        if not self._check_chrome_installed():
            return self._handle_chrome_not_installed()
            
        # Check dependencies
        dependencies = self._check_dependencies()
        logger.info(f"Dependency check results: {dependencies}")
        
        # Log warning if any dependencies are missing
        self._log_missing_dependencies(dependencies)
            
        # Create logs directory if it doesn't exist
        log_dir = os.path.join(os.getcwd(), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        try:
            # Add debug logs
            logger.info(f"Connecting to WhatsApp Web for session: {self.session_id}")
            logger.info(f"Headless mode: {headless}, Timeout: {timeout} seconds")
            
            # Update session status
            self._update_session_status("connecting")
            
            # Initialize Chrome driver
            self._initialize_chrome_driver(headless)
            
            # Navigate to WhatsApp Web
            return self._navigate_to_whatsapp_web(timeout)
            
        except Exception as e:
            return self._handle_connection_error(e)
    
    def _handle_chrome_not_installed(self) -> Dict[str, Any]:
        """Handle case when Chrome is not installed.
        
        Returns:
            Error response dictionary
        """
        error_msg = "Chrome is not installed. Please install Google Chrome to use WhatsApp Web integration."
        logger.error(error_msg)
        self.session.status = "error"
        db.session.commit()
        return {
            "status": "failed",
            "error": error_msg
        }
    
    def _log_missing_dependencies(self, dependencies: Dict[str, bool]) -> None:
        """Log warning if any dependencies are missing.
        
        Args:
            dependencies: Dictionary with dependency status
        """
        missing_deps = [dep for dep, installed in dependencies.items() if not installed]
        if missing_deps:
            logger.warning(f"Missing dependencies: {', '.join(missing_deps)}. Some features may not work properly.")
    
    def _update_session_status(self, status: str) -> None:
        """Update session status in database.
        
        Args:
            status: New status for the session
        """
        self.session.status = status
        db.session.commit()
        logger.info(f"Updated session status to '{status}'")
    
    def _initialize_chrome_driver(self, headless: bool) -> None:
        """Initialize Chrome driver with appropriate options.
        
        Args:
            headless: Whether to run the browser in headless mode
        """
        # Set up Chrome options
        chrome_options = self._setup_chrome_options(headless)
        
        # Initialize Chrome driver with cross-platform support
        service = self._setup_chrome_driver_service()
        
        # Create the Chrome driver
        try:
            logger.info("Initializing Chrome driver...")
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Chrome driver initialized successfully")
        except Exception as e:
            self._handle_chrome_driver_init_error(e)
    
    def _setup_chrome_options(self, headless: bool) -> Options:
        """Set up Chrome options for WebDriver.
        
        Args:
            headless: Whether to run the browser in headless mode
            
        Returns:
            Configured Chrome options
        """
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1280,800")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        return chrome_options
    
    def _setup_chrome_driver_service(self) -> Service:
        """Set up Chrome driver service with appropriate executable path.
        
        Returns:
            Configured Chrome driver service
        """
        # Check if we should use a specific ChromeDriver path
        chromedriver_dir = os.path.join(os.getcwd(), 'app_data', 'chromedriver')
        
        # Create the directory if it doesn't exist
        os.makedirs(chromedriver_dir, exist_ok=True)
        
        # Determine the correct chromedriver executable based on OS
        if os.name == 'nt':  # Windows
            chromedriver_name = 'chromedriver.exe'
            setup_script = os.path.join(chromedriver_dir, 'setup_chromedriver.bat')
        else:  # Linux/Mac
            chromedriver_name = 'chromedriver'
            setup_script = os.path.join(chromedriver_dir, 'setup_chromedriver.sh')
                
        chromedriver_path = os.path.join(chromedriver_dir, chromedriver_name)
        
        # Log the paths for debugging
        logger.info(f"ChromeDriver directory: {chromedriver_dir}")
        logger.info(f"ChromeDriver path: {chromedriver_path}")
        logger.info(f"Setup script path: {setup_script}")
        
        # Check if the specific chromedriver exists, use it if available
        if os.path.exists(chromedriver_path):
            return self._create_service_from_path(chromedriver_path)
        else:
            return self._download_and_create_service(chromedriver_path, setup_script)
    
    def _create_service_from_path(self, chromedriver_path: str) -> Service:
        """Create a Chrome driver service from a specific path.
        
        Args:
            chromedriver_path: Path to the ChromeDriver executable
            
        Returns:
            Configured Chrome driver service
        """
        try:
            service = Service(executable_path=chromedriver_path)
            logger.info(f"Using ChromeDriver from: {chromedriver_path}")
            return service
        except Exception as e:
            logger.error(f"Error creating ChromeDriver service: {str(e)}")
            # Log to selenium.log as well
            with open(os.path.join(os.getcwd(), 'logs', 'selenium.log'), 'a') as f:
                f.write(f"{datetime.now().isoformat()} - ERROR - Error creating ChromeDriver service: {str(e)}\n")
            raise
    
    def _download_and_create_service(self, chromedriver_path: str, setup_script: str) -> Service:
        """Download ChromeDriver and create a service.
        
        Args:
            chromedriver_path: Path where ChromeDriver should be installed
            setup_script: Path to the setup script
            
        Returns:
            Configured Chrome driver service
        """
        # Try to download ChromeDriver using the setup script
        logger.info("ChromeDriver not found. Attempting to download it automatically...")
        try:
            if os.path.exists(setup_script):
                self._run_setup_script(setup_script)
                    
                # Check if download was successful
                if os.path.exists(chromedriver_path):
                    service = Service(executable_path=chromedriver_path)
                    logger.info(f"Using newly downloaded ChromeDriver from: {chromedriver_path}")
                    return service
                else:
                    # Fall back to webdriver-manager if download failed
                    return self._use_webdriver_manager()
            else:
                logger.warning(f"Setup script not found: {setup_script}")
                with open(os.path.join(os.getcwd(), 'logs', 'selenium.log'), 'a') as f:
                    f.write(f"{datetime.now().isoformat()} - WARNING - Setup script not found: {setup_script}\n")
                return self._use_webdriver_manager()
        except Exception as e:
            logger.error(f"Error downloading ChromeDriver: {str(e)}")
            # Log to selenium.log as well
            with open(os.path.join(os.getcwd(), 'logs', 'selenium.log'), 'a') as f:
                f.write(f"{datetime.now().isoformat()} - ERROR - Error downloading ChromeDriver: {str(e)}\n")
            # Fall back to webdriver-manager
            return self._use_webdriver_manager()
    
    def _run_setup_script(self, setup_script: str) -> None:
        """Run the ChromeDriver setup script.
        
        Args:
            setup_script: Path to the setup script
        """
        if os.name == 'nt':  # Windows
            result = subprocess.run([setup_script], shell=True, capture_output=True, text=True)
        else:  # Linux/Mac
            result = subprocess.run(['bash', setup_script], capture_output=True, text=True)
            
        # Log the output of the setup script
        logger.info(f"Setup script stdout: {result.stdout}")
        if result.stderr:
            logger.warning(f"Setup script stderr: {result.stderr}")
            
        # Log to selenium.log as well
        with open(os.path.join(os.getcwd(), 'logs', 'selenium.log'), 'a') as f:
            f.write(f"{datetime.now().isoformat()} - INFO - Setup script stdout: {result.stdout}\n")
            if result.stderr:
                f.write(f"{datetime.now().isoformat()} - WARNING - Setup script stderr: {result.stderr}\n")
                
        if result.returncode == 0:
            logger.info("ChromeDriver downloaded successfully")
        else:
            logger.error(f"Setup script failed with return code: {result.returncode}")
            with open(os.path.join(os.getcwd(), 'logs', 'selenium.log'), 'a') as f:
                f.write(f"{datetime.now().isoformat()} - ERROR - Setup script failed with return code: {result.returncode}\n")
    
    def _use_webdriver_manager(self) -> Service:
        """Use webdriver-manager to download and create a service.
        
        Returns:
            Configured Chrome driver service
        """
        try:
            logger.info("Using webdriver-manager as fallback")
            driver_path = ChromeDriverManager().install()
            logger.info(f"WebDriver manager installed ChromeDriver at: {driver_path}")
            return Service(executable_path=driver_path)
        except Exception as e:
            logger.error(f"Error using webdriver-manager: {str(e)}")
            with open(os.path.join(os.getcwd(), 'logs', 'selenium.log'), 'a') as f:
                f.write(f"{datetime.now().isoformat()} - ERROR - Error using webdriver-manager: {str(e)}\n")
            raise
    
    def _handle_chrome_driver_init_error(self, error: Exception) -> None:
        """Handle error during Chrome driver initialization.
        
        Args:
            error: The exception that occurred
        """
        error_msg = f"Error initializing Chrome driver: {str(error)}"
        logger.error(error_msg)
        # Log to selenium.log as well
        with open(os.path.join(os.getcwd(), 'logs', 'selenium.log'), 'a') as f:
            f.write(f"{datetime.now().isoformat()} - ERROR - {error_msg}\n")
        logger.error(f"Error creating Chrome driver: {str(error)}")
        raise ValueError(f"Failed to initialize Chrome driver: {str(error)}. Please ensure Chrome is installed and up to date.")
    
    def _navigate_to_whatsapp_web(self, timeout: int) -> Dict[str, Any]:
        """Navigate to WhatsApp Web and handle login or QR code generation.
        
        Args:
            timeout: Timeout in seconds for waiting for QR code
            
        Returns:
            Dictionary with connection status and QR code if available
        """
        try:
            logger.info("Navigating to WhatsApp Web...")
            
            # Log Chrome and ChromeDriver versions
            self._log_browser_versions()
            
            self.driver.get("https://web.whatsapp.com/")
            logger.info("Navigation to WhatsApp Web completed")
            
            # Check if already logged in
            if self._check_if_already_logged_in():
                return {
                    "status": "success",
                    "message": "Already logged in to WhatsApp Web"
                }
                
            # Wait for QR code to appear
            return self._wait_for_qr_code(timeout)
            
        except Exception as nav_error:
            return self._handle_navigation_error(nav_error)
    
    def _log_browser_versions(self) -> None:
        """Log Chrome and ChromeDriver versions."""
        try:
            chrome_version = self.driver.capabilities['browserVersion']
            driver_version = self.driver.capabilities['chrome']['chromedriverVersion'].split(' ')[0]
            logger.info(f"Chrome version: {chrome_version}, ChromeDriver version: {driver_version}")
        except Exception as ver_error:
            logger.warning(f"Could not get Chrome/ChromeDriver versions: {str(ver_error)}")
    
    def _check_if_already_logged_in(self) -> bool:
        """Check if already logged in to WhatsApp Web.
        
        Returns:
            True if already logged in, False otherwise
        """
        try:
            # Wait a short time to see if we're already logged in
            logger.info("Checking if already logged in...")
            chat_list = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//div[@id='pane-side']"))
            )
            
            if chat_list:
                logger.info("Already logged in to WhatsApp Web")
                # Handle successful login
                self._handle_successful_login()
                
                # Take a screenshot for verification
                screenshot_path = os.path.join(os.getcwd(), 'logs', 'already_logged_in.png')
                self.driver.save_screenshot(screenshot_path)
                
                return True
        except TimeoutException:
            # Not logged in, continue with QR code generation
            logger.info("Not already logged in, continuing with QR code generation")
        
        return False
    
    def _handle_navigation_error(self, error: Exception) -> Dict[str, Any]:
        """Handle error during navigation to WhatsApp Web.
        
        Args:
            error: The exception that occurred
            
        Returns:
            Error response dictionary
        """
        logger.error(f"Error navigating to WhatsApp Web: {str(error)}")
        # Take a screenshot for debugging
        try:
            screenshot_path = os.path.join(os.getcwd(), 'logs', f'whatsapp_nav_error_{int(time.time())}.png')
            self.driver.save_screenshot(screenshot_path)
            logger.info(f"Saved navigation error screenshot to {screenshot_path}")
        except Exception as ss_error:
            logger.error(f"Failed to save navigation error screenshot: {str(ss_error)}")
        
        self._cleanup()
        return {
            "status": "failed",
            "error": f"Navigation error: {str(error)}"
        }
    
    def _wait_for_qr_code(self, timeout: int) -> Dict[str, Any]:
        """Wait for QR code to appear and extract it.
        
        Args:
            timeout: Timeout in seconds for waiting for QR code
            
        Returns:
            Dictionary with QR code data or error
        """
        try:
            logger.info(f"Waiting for QR code to appear (timeout: {timeout} seconds)...")
            
            # Save page source and screenshot for debugging
            self._save_debug_info()
            
            # Find QR code canvas
            qr_canvas = self._find_qr_code_canvas(timeout)
            
            if not qr_canvas:
                return self._handle_qr_code_not_found()
            
            # Extract QR code data
            qr_data = self._extract_qr_code_data(qr_canvas)
            
            if not qr_data or not qr_data.startswith('data:'):
                return self._handle_qr_code_extraction_failed()
            
            # Store QR code
            self._store_qr_code(qr_data)
            
            # Start monitoring for login
            threading.Thread(target=self._wait_for_login, daemon=True).start()
            
            return {
                "status": "success",
                "message": "QR code generated successfully",
                "qr_code": qr_data
            }
            
        except TimeoutException:
            return self._handle_qr_code_timeout()
    
    def _save_debug_info(self) -> None:
        """Save page source and screenshot for debugging."""
        # Save page source
        try:
            with open(os.path.join(os.getcwd(), 'logs', 'whatsapp_page_source.html'), 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            logger.info("Saved WhatsApp Web page source for debugging")
        except Exception as e:
            logger.warning(f"Could not save page source: {str(e)}")
        
        # Take screenshot
        try:
            screenshot_path = os.path.join(os.getcwd(), 'logs', 'whatsapp_before_qr.png')
            self.driver.save_screenshot(screenshot_path)
            logger.info(f"Saved screenshot to {screenshot_path}")
        except Exception as e:
            logger.warning(f"Could not save screenshot: {str(e)}")
    
    def _find_qr_code_canvas(self, timeout: int) -> Optional[WebElement]:
        """Find QR code canvas element on the page.
        
        Args:
            timeout: Timeout in seconds for waiting for QR code
            
        Returns:
            QR code canvas element or None if not found
        """
        # Try multiple XPath expressions to find the QR code canvas
        qr_canvas = None
        xpath_expressions = [
            "//canvas[contains(@aria-label, 'Scan me!')]",
            "//canvas[contains(@aria-label, 'QR code')]",
            "//canvas[contains(@data-testid, 'qrcode')]",
            "//div[contains(@data-ref, 'qrcode')]//canvas",
            "//div[contains(@class, 'qr')]//canvas",
            "//canvas[contains(@role, 'img')]",
            "//div[contains(@class, '_2UwZ_')]/canvas",
            "//div[contains(@class, '_1jJ70')]/canvas",
            "//div[contains(@class, '_2EZ_m')]/canvas"
        ]
        
        # Log all elements that might be QR code related
        self._log_canvas_elements()
        
        for xpath in xpath_expressions:
            logger.info(f"Trying to find QR canvas with XPath: {xpath}")
            try:
                qr_canvas = WebDriverWait(self.driver, timeout/len(xpath_expressions)).until(
                    EC.presence_of_element_located((By.XPATH, xpath)),
                )
                logger.info(f"QR code canvas found with XPath: {xpath}")
                break
            except TimeoutException:
                logger.warning(f"QR canvas not found with XPath: {xpath}, trying next expression")
                continue
        
        # If no QR canvas found, try to find any canvas element
        if not qr_canvas:
            qr_canvas = self._find_any_canvas_element()
        
        return qr_canvas
    
    def _log_canvas_elements(self) -> None:
        """Log all canvas elements on the page."""
        try:
            all_canvas = self.driver.find_elements(By.TAG_NAME, "canvas")
            logger.info(f"Found {len(all_canvas)} canvas elements on the page")
            
            for i, canvas in enumerate(all_canvas):
                try:
                    attrs = self.driver.execute_script(
                        """var items = {}; 
                        for (var i = 0; i < arguments[0].attributes.length; i++) { 
                            items[arguments[0].attributes[i].name] = arguments[0].attributes[i].value 
                        }; 
                        return items;""", canvas)
                    logger.info(f"Canvas {i} attributes: {attrs}")
                except Exception as e:
                    logger.warning(f"Could not get attributes for canvas {i}: {str(e)}")
        except Exception as e:
            logger.warning(f"Could not enumerate canvas elements: {str(e)}")
    
    def _find_any_canvas_element(self) -> Optional[WebElement]:
        """Find any canvas element on the page.
        
        Returns:
            Canvas element or None if not found
        """
        logger.warning("Could not find QR code canvas with specific XPath expressions, trying generic canvas search")
        try:
            # Try to find any canvas element
            canvas_elements = self.driver.find_elements(By.TAG_NAME, "canvas")
            if canvas_elements:
                logger.info(f"Found {len(canvas_elements)} canvas elements, using the first one")
                qr_canvas = canvas_elements[0]
                
                # Try to verify if it's a QR code by checking attributes
                try:
                    attrs = self.driver.execute_script(
                        """var items = {}; 
                        for (var i = 0; i < arguments[0].attributes.length; i++) { 
                            items[arguments[0].attributes[i].name] = arguments[0].attributes[i].value 
                        }; 
                        return items;""", qr_canvas)
                    logger.info(f"Selected canvas attributes: {attrs}")
                except Exception as e:
                    logger.warning(f"Could not get attributes for selected canvas: {str(e)}")
                
                return qr_canvas
        except Exception as e:
            logger.warning(f"Error finding any canvas elements: {str(e)}")
        
        return None
    
    def _handle_qr_code_not_found(self) -> Dict[str, Any]:
        """Handle case when QR code canvas is not found.
        
        Returns:
            Error response dictionary or success if QR code was detected directly from screenshot
        """
        logger.error("QR code canvas not found with any XPath expression")
        # Take a screenshot for debugging
        try:
            screenshot_path = os.path.join(os.getcwd(), 'logs', f'whatsapp_no_qr_{int(time.time())}.png')
            self.driver.save_screenshot(screenshot_path)
            logger.info(f"Saved no-QR screenshot to {screenshot_path}")
            
            # Log page source for debugging
            source_path = os.path.join(os.getcwd(), 'logs', f'whatsapp_page_source_{int(time.time())}.html')
            with open(source_path, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            logger.info(f"Saved page source to {source_path}")
            
            # Try to detect QR code directly from screenshot
            result = self._detect_qr_code_from_screenshot(screenshot_path)
            if result:
                return result
        except Exception as ss_error:
            logger.error(f"Failed to save debug info: {str(ss_error)}")
        
        self._cleanup()
        return {
            "status": "failed",
            "error": "QR code not found"
        }
    
    def _detect_qr_code_from_screenshot(self, screenshot_path: str) -> Optional[Dict[str, Any]]:
        """Detect QR code directly from screenshot.
        
        Args:
            screenshot_path: Path to the screenshot
            
        Returns:
            Dictionary with QR code data or None if detection failed
        """
        dependencies = self._check_dependencies()
        if dependencies["cv2"] and dependencies["zxingcpp"] and dependencies["numpy"]:
            try:
                logger.info("Attempting direct QR code detection from screenshot...")
                import cv2
                import numpy as np
                import zxingcpp
                
                # Read the screenshot
                img = cv2.imread(screenshot_path)
                
                # Check if image was loaded successfully
                if img is None:
                    logger.error(f"Failed to load image from {screenshot_path}")
                    return None
                    
                # Convert to grayscale
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                
                # Apply adaptive threshold
                thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                             cv2.THRESH_BINARY, 11, 2)
                
                # Save the processed image for debugging
                cv2.imwrite(os.path.join(os.getcwd(), 'logs', 'processed_screenshot.png'), thresh)
                
                # Try to detect QR codes using zxingcpp
                qr_codes = zxingcpp.read_barcodes(thresh)
                
                if qr_codes:
                    logger.info(f"Detected {len(qr_codes)} QR codes directly from screenshot")
                    
                    # Get the first QR code
                    qr_code = qr_codes[0]
                    
                    # Log the QR code text for debugging
                    logger.info(f"Detected QR code text: {qr_code.text[:30]}...")
                    
                    # Extract QR code data
                    qr_data = f"data:image/png;base64,{base64.b64encode(open(screenshot_path, 'rb').read()).decode('utf-8')}"
                    logger.info("Successfully extracted QR code data from direct detection")
                    
                    # Store QR code
                    self._store_qr_code(qr_data)
                    
                    # Start monitoring for login
                    threading.Thread(target=self._wait_for_login, daemon=True).start()
                    
                    return {
                        "status": "success",
                        "qr_code": qr_data
                    }
            except Exception as qr_detect_error:
                logger.error(f"Direct QR detection failed: {str(qr_detect_error)}")
        
        return None
    
    def _extract_qr_code_data(self, qr_canvas: WebElement) -> Optional[str]:
        """Extract QR code data from canvas element.
        
        Args:
            qr_canvas: QR code canvas element
            
        Returns:
            QR code data as base64 string or None if extraction failed
        """
        logger.info("Extracting QR code data from canvas...")
        try:
            # Try different JavaScript approaches to extract QR code
            js_approaches = [
                # First try with the provided canvas element
                "return arguments[0].toDataURL('image/png');",
                "return arguments[0].toDataURL();",
                "return arguments[0].toDataURL('image/jpeg', 1.0);",
                
                # Then try with more robust selectors
                """
                try {
                    // Try to find the QR code canvas with multiple selectors
                    const selectors = [
                        'canvas[aria-label="Scan me!"]',
                        'canvas[data-testid="qrcode"]',
                        'canvas[data-ref]',
                        'div[data-ref="qrcode"] canvas',
                        'div[data-testid="qrcode"] canvas',
                        'canvas[role="img"]',
                        'canvas'
                    ];
                    
                    let canvas = null;
                    for (const selector of selectors) {
                        const elements = document.querySelectorAll(selector);
                        if (elements.length > 0) {
                            canvas = elements[0];
                            console.log('Found canvas with selector:', selector);
                            break;
                        }
                    }
                    
                    if (canvas) {
                        // Check if canvas has dimensions
                        const width = canvas.width;
                        const height = canvas.height;
                        console.log('Canvas dimensions:', width, 'x', height);
                        
                        if (width > 0 && height > 0) {
                            return canvas.toDataURL('image/png');
                        } else {
                            console.error('Canvas has invalid dimensions:', width, 'x', height);
                            return null;
                        }
                    } else {
                        console.error('No canvas element found');
                        return null;
                    }
                } catch (error) {
                    console.error('Error extracting QR code:', error.message);
                    return null;
                }
                """,
                
                # Fallback to simpler selectors
                "return document.querySelector('canvas').toDataURL('image/png');",
                "return document.querySelector('[data-testid=\"qrcode\"] canvas').toDataURL();",
                "return document.querySelector('canvas[role=\"img\"]').toDataURL();",
                "return document.querySelector('div[data-ref=\"qrcode\"] canvas').toDataURL('image/png');"
            ]
            
            qr_data = None
            for js_code in js_approaches:
                try:
                    logger.info(f"Trying to extract QR data with JS: {js_code[:50]}...")
                    qr_data = self.driver.execute_script(js_code, qr_canvas)
                    if qr_data and qr_data.startswith('data:'):
                        logger.info("QR code data extracted successfully")
                        break
                except Exception as js_error:
                    logger.warning(f"Failed to extract QR with JS approach: {str(js_error)}")
            
            # Fallback: If canvas extraction fails, try to capture QR code using screenshot
            if not qr_data or not qr_data.startswith('data:'):
                qr_data = self._extract_qr_code_from_screenshot(qr_canvas)
            
            return qr_data
                
        except Exception as script_error:
            logger.error(f"Error executing script to get QR data: {str(script_error)}")
            # Take a screenshot for debugging
            try:
                screenshot_path = os.path.join(os.getcwd(), 'logs', f'whatsapp_qr_extract_error_{int(time.time())}.png')
                self.driver.save_screenshot(screenshot_path)
                logger.info(f"Saved QR extraction error screenshot to {screenshot_path}")
                
                # Try alternative QR code extraction using PIL if canvas was found
                if qr_canvas and isinstance(qr_canvas, WebElement):
                    return self._extract_qr_code_using_pil(qr_canvas, screenshot_path)
            except Exception as ss_error:
                logger.error(f"Failed to save QR extraction error screenshot: {str(ss_error)}")
            
            return None
    
    def _extract_qr_code_from_screenshot(self, qr_canvas: WebElement) -> Optional[str]:
        """Extract QR code from screenshot.
        
        Args:
            qr_canvas: QR code canvas element
            
        Returns:
            QR code data as base64 string or None if extraction failed
        """
        try:
            logger.info("Canvas extraction failed, trying screenshot method")
            
            # Take a screenshot of the QR code area
            if qr_canvas:
                # Get the location and size of the QR canvas
                location = qr_canvas.location
                size = qr_canvas.size
                
                # Take a screenshot of the entire page
                screenshot_path = os.path.join(os.getcwd(), 'logs', 'qr_full_screenshot.png')
                self.driver.save_screenshot(screenshot_path)
                logger.info(f"Saved full screenshot to {screenshot_path}")
                
                # Crop the screenshot to the QR code area
                try:
                    from PIL import Image
                    import base64
                    import io
                    
                    # Open the screenshot
                    img = Image.open(screenshot_path)
                    
                    # Crop the image to the QR code area
                    left = location['x']
                    top = location['y']
                    right = location['x'] + size['width']
                    bottom = location['y'] + size['height']
                    qr_img = img.crop((left, top, right, bottom))
                    
                    # Save the cropped image
                    qr_img_path = os.path.join(os.getcwd(), 'logs', 'qr_code.png')
                    qr_img.save(qr_img_path)
                    logger.info(f"Saved cropped QR code to {qr_img_path}")
                    
                    # Convert the image to base64
                    buffered = io.BytesIO()
                    qr_img.save(buffered, format="PNG")
                    qr_data = f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode('utf-8')}"
                    logger.info("Successfully extracted QR code using screenshot method")
                    return qr_data
                except ImportError:
                    logger.warning("PIL not installed, cannot process screenshot")
                except Exception as crop_error:
                    logger.error(f"Error cropping QR code: {str(crop_error)}")
        except Exception as screenshot_error:
            logger.error(f"Screenshot method failed: {str(screenshot_error)}")
        
        return None
    
    def _extract_qr_code_using_pil(self, qr_canvas: WebElement, screenshot_path: str) -> Optional[str]:
        """Extract QR code using PIL.
        
        Args:
            qr_canvas: QR code canvas element
            screenshot_path: Path to the screenshot
            
        Returns:
            QR code data as base64 string or None if extraction failed
        """
        try:
            logger.info("Attempting alternative QR code extraction using PIL...")
            from PIL import Image
            import io
            import base64
            
            # Get the location and size of the QR canvas
            location = qr_canvas.location
            size = qr_canvas.size
            
            # Open the screenshot
            img = Image.open(screenshot_path)
            
            # Crop the image to the QR code area
            left = location['x']
            top = location['y']
            right = location['x'] + size['width']
            bottom = location['y'] + size['height']
            qr_img = img.crop((left, top, right, bottom))
            
            # Save the cropped image
            qr_img_path = os.path.join(os.getcwd(), 'logs', 'qr_code_alt_method.png')
            qr_img.save(qr_img_path)
            logger.info(f"Saved cropped QR code to {qr_img_path}")
            
            # Convert the image to base64
            buffered = io.BytesIO()
            qr_img.save(buffered, format="PNG")
            qr_data = f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode('utf-8')}"
            logger.info("Successfully extracted QR code using alternative method")
            return qr_data
        except ImportError:
            logger.warning("PIL not installed, cannot use alternative method")
        except Exception as alt_error:
            logger.error(f"Alternative QR extraction failed: {str(alt_error)}")
        
        return None
    
    def _handle_qr_code_extraction_failed(self) -> Dict[str, Any]:
        """Handle case when QR code extraction failed.
        
        Returns:
            Error response dictionary
        """
        logger.error("Failed to extract valid QR code data")
        self._cleanup()
        return {
            "status": "failed",
            "error": "Failed to extract QR code"
        }
    
    def _store_qr_code(self, qr_data: str) -> None:
        """Store QR code in memory and database.
        
        Args:
            qr_data: QR code data as base64 string
        """
        try:
            logger.info("Storing QR code in session...")
            self.qr_code = qr_data
            self.session.qr_code = qr_data
            db.session.commit()
            logger.info("QR code stored successfully")
        except Exception as db_error:
            logger.error(f"Error storing QR code in database: {str(db_error)}")
            # Try to rollback the transaction
            try:
                db.session.rollback()
                logger.info("Database session rolled back after error")
            except Exception as rollback_error:
                logger.error(f"Error rolling back database session: {str(rollback_error)}")
            
            # Try again with a new session
            try:
                logger.info("Attempting to store QR code with a new database session...")
                from app import db
                self.session.qr_code = qr_data
                db.session.commit()
                logger.info("QR code stored successfully on second attempt")
            except Exception as retry_error:
                logger.error(f"Error storing QR code on second attempt: {str(retry_error)}")
                # Continue anyway with the QR code in memory
                logger.info("Continuing with QR code in memory only")
    
    def _handle_qr_code_timeout(self) -> Dict[str, Any]:
        """Handle timeout waiting for QR code.
        
        Returns:
            Error response dictionary or success if already logged in
        """
        logger.error("Timeout waiting for QR code to appear")
        # Check if we're already logged in
        logger.info("Checking if already logged in...")
        try:
            cookies = self.driver.get_cookies()
            logger.info(f"Found {len(cookies)} cookies")
            
            cookie_names = [cookie.get('name') for cookie in cookies]
            logger.info(f"Cookie names: {cookie_names}")
            
            if "_wa_wam_authenticated" in cookie_names:
                logger.info("Found authentication cookie, user is already logged in")
                self._handle_successful_login()
                return {
                    "status": "success",
                    "message": "Already authenticated"
                }
            else:
                logger.error("Authentication cookie not found")
                # Take a screenshot for debugging
                try:
                    screenshot_path = os.path.join(os.getcwd(), 'logs', f'whatsapp_timeout_{int(time.time())}.png')
                    self.driver.save_screenshot(screenshot_path)
                    logger.info(f"Saved debug screenshot to {screenshot_path}")
                except Exception as ss_error:
                    logger.error(f"Failed to save debug screenshot: {str(ss_error)}")
                    
                # Get page source for debugging
                try:
                    page_source = self.driver.page_source
                    logger.info(f"Page source length: {len(page_source)} characters")
                    # Log first 500 chars of page source
                    logger.info(f"Page source preview: {page_source[:500]}...")
                except Exception as ps_error:
                    logger.error(f"Failed to get page source: {str(ps_error)}")
                    
                self._cleanup()
                return {
                    "status": "failed",
                    "error": "Timeout waiting for QR code"
                }
        except Exception as cookie_error:
            logger.error(f"Error checking cookies: {str(cookie_error)}")
            self._cleanup()
            return {
                "status": "failed",
                "error": f"Error checking login status: {str(cookie_error)}"
            }
    
    def _handle_connection_error(self, error: Exception) -> Dict[str, Any]:
        """Handle error during connection to WhatsApp Web.
        
        Args:
            error: The exception that occurred
            
        Returns:
            Error response dictionary
        """
        logger.error(f"Error connecting to WhatsApp Web: {str(error)}")
        # Log the full stack trace
        import traceback
        logger.error(f"Stack trace: {traceback.format_exc()}")
        
        # Try to capture additional diagnostic information
        try:
            if self.driver:
                # Take a screenshot if possible
                try:
                    screenshot_path = os.path.join(os.getcwd(), 'logs', f'whatsapp_error_{int(time.time())}.png')
                    self.driver.save_screenshot(screenshot_path)
                    logger.info(f"Saved error screenshot to {screenshot_path}")
                except Exception as ss_error:
                    logger.error(f"Failed to save error screenshot: {str(ss_error)}")
        except Exception as diag_error:
            logger.error(f"Error capturing diagnostic info: {str(diag_error)}")
            
        self._cleanup()
        return {
            "status": "failed",
            "error": str(error)
        }
    
    def _wait_for_login(self, timeout: int = 300) -> None:
        """Wait for successful login after QR code scan.
        
        Args:
            timeout: Timeout in seconds for waiting for login
        """
        try:
            # Wait for chat list to appear (indicates successful login)
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, "//div[@id='pane-side']"))
            )
            
            # Handle successful login
            self._handle_successful_login()
            
        except TimeoutException:
            logger.error("Timeout waiting for login")
            self._cleanup()
        except Exception as e:
            logger.error(f"Error waiting for login: {str(e)}")
            self._cleanup()
    
    def _handle_successful_login(self) -> None:
        """Handle successful login to WhatsApp Web."""
        try:
            # Update session status
            self.session.status = "connected"
            self.session.last_connected = datetime.utcnow()
            self.session.qr_code = None  # Clear QR code after successful login
            db.session.commit()
            
            # Extract and store session data
            local_storage = self.driver.execute_script("return Object.entries(window.localStorage);")
            session_data = {key: value for key, value in local_storage}
            self.session_data = json.dumps(session_data)
            self.session.session_data = self.session_data
            db.session.commit()
            
            # Extract device information
            self._extract_device_info()
            
            # Connect to WebSocket for real-time updates
            self._connect_websocket()
            
            self.is_connected = True
            
        except Exception as e:
            logger.error(f"Error handling successful login: {str(e)}")
            self._cleanup()
    
    def _extract_device_info(self) -> None:
        """Extract device information from WhatsApp Web."""
        try:
            # Execute JavaScript to get device info
            device_info = self.driver.execute_script(
                """return {
                    'phone': window.Store && window.Store.Conn ? window.Store.Conn.wid.user : null,
                    'name': window.Store && window.Store.Contact ? window.Store.Contact.getContact(window.Store.Conn.wid).name : null,
                    'platform': 'WhatsApp Web'
                };"""
            )
            
            if device_info and device_info.get('phone'):
                # Check if device already exists
                device = WhatsAppDevice.query.filter_by(
                    session_id=self.session.id,
                    phone_number=device_info.get('phone')
                ).first()
                
                if not device:
                    # Create new device
                    device = WhatsAppDevice(
                        session_id=self.session.id,
                        device_id=f"device_{int(time.time())}",
                        phone_number=device_info.get('phone'),
                        device_name=device_info.get('name'),
                        platform=device_info.get('platform')
                    )
                    db.session.add(device)
                    db.session.commit()
                
        except Exception as e:
            logger.error(f"Error extracting device info: {str(e)}")
    
    def _connect_websocket(self) -> None:
        """Connect to WhatsApp Web WebSocket for real-time updates."""
        try:
            # Get WebSocket URL from the page
            ws_url = self.driver.execute_script(
                "return window.Store.Stream.stream.websocket._url;"
            )
            
            if not ws_url:
                logger.error("WebSocket URL not found")
                return
            
            # Initialize WebSocket connection
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_message=self._on_ws_message,
                on_error=self._on_ws_error,
                on_close=self._on_ws_close,
                on_open=self._on_ws_open
            )
            
            # Start WebSocket in a separate thread
            self.ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
            self.ws_thread.start()
            
        except Exception as e:
            logger.error(f"Error connecting to WebSocket: {str(e)}")
    
    def _on_ws_message(self, ws, message) -> None:
        """Handle WebSocket message."""
        try:
            # Parse message
            data = json.loads(message)
            
            # Process message based on type
            if 'messageType' in data:
                # Call registered callbacks
                for callback in self.message_callbacks:
                    callback(data)
                    
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {str(e)}")
    
    def _on_ws_error(self, ws, error) -> None:
        """Handle WebSocket error."""
        logger.error(f"WebSocket error: {str(error)}")
    
    def _on_ws_close(self, ws, close_status_code, close_msg) -> None:
        """Handle WebSocket close."""
        logger.info(f"WebSocket closed: {close_status_code} - {close_msg}")
        self.is_connected = False
    
    def _on_ws_open(self, ws) -> None:
        """Handle WebSocket open."""
        logger.info("WebSocket connected")
    
    def register_message_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback for incoming messages.
        
        Args:
            callback: Function to call when a message is received
        """
        self.message_callbacks.append(callback)
    
    def send_message(self, phone: str, message: str, media_url: str = None) -> Dict[str, Any]:
        """Send a message to a WhatsApp contact.
        
        Args:
            phone: The phone number to send the message to
            message: The message text to send
            media_url: Optional URL to media to send
            
        Returns:
            Dictionary with send status and message ID if successful
        """
        if not self.is_connected:
            return {
                "status": "failed",
                "error": "Not connected to WhatsApp"
            }
        
        try:
            # Format phone number (remove any non-digit characters except +)
            phone = ''.join(c for c in phone if c.isdigit() or c == '+')
            
            # Ensure phone has country code
            if not phone.startswith('+'):
                phone = '+' + phone
            
            # Send media if provided
            if media_url:
                result = self._send_media_message(phone, message, media_url)
            else:
                result = self._send_text_message(phone, message)
                
            return result
            
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _send_text_message(self, phone: str, message: str) -> Dict[str, Any]:
        """Send a text message to a WhatsApp contact.
        
        Args:
            phone: The phone number to send the message to
            message: The message text to send
            
        Returns:
            Dictionary with send status and message ID if successful
        """
        try:
            # Execute JavaScript to send message
            result = self.driver.execute_script(
                f"""
                return window.WWebJS.sendMessage("{phone}@c.us", "{message}");
                """
            )
            
            if result and 'id' in result:
                return {
                    "status": "success",
                    "message_id": result['id'],
                    "timestamp": result.get('timestamp', int(time.time()))
                }
            else:
                return {
                    "status": "failed",
                    "error": "Failed to send message"
                }
                
        except Exception as e:
            logger.error(f"Error sending text message: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _send_media_message(self, phone: str, caption: str, media_url: str) -> Dict[str, Any]:
        """Send a media message to a WhatsApp contact.
        
        Args:
            phone: The phone number to send the message to
            caption: The caption text for the media
            media_url: URL to the media to send
            
        Returns:
            Dictionary with send status and message ID if successful
        """
        try:
            # Download media from URL
            response = requests.get(media_url)
            if response.status_code != 200:
                return {
                    "status": "failed",
                    "error": f"Failed to download media: HTTP {response.status_code}"
                }
            
            # Convert to base64
            media_base64 = base64.b64encode(response.content).decode('utf-8')
            
            # Determine media type from URL or content
            content_type = response.headers.get('Content-Type', '')
            if not content_type:
                # Try to guess from URL
                if media_url.lower().endswith(('.jpg', '.jpeg')):
                    content_type = 'image/jpeg'
                elif media_url.lower().endswith('.png'):
                    content_type = 'image/png'
                elif media_url.lower().endswith('.gif'):
                    content_type = 'image/gif'
                elif media_url.lower().endswith(('.mp4', '.mpeg4')):
                    content_type = 'video/mp4'
                elif media_url.lower().endswith('.pdf'):
                    content_type = 'application/pdf'
                else:
                    content_type = 'application/octet-stream'
            
            # Execute JavaScript to send media message
            result = self.driver.execute_script(
                f"""
                return window.WWebJS.sendMedia(
                    "{phone}@c.us", 
                    "data:{content_type};base64,{media_base64}", 
                    "{caption}"
                );
                """
            )
            
            if result and 'id' in result:
                return {
                    "status": "success",
                    "message_id": result['id'],
                    "timestamp": result.get('timestamp', int(time.time()))
                }
            else:
                return {
                    "status": "failed",
                    "error": "Failed to send media message"
                }
                
        except Exception as e:
            logger.error(f"Error sending media message: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def get_qr_code(self) -> Optional[str]:
        """Get the current QR code.
        
        Returns:
            QR code data as base64 string or None if not available
        """
        return self.qr_code
    
    def refresh_qr_code(self, headless: bool = True, timeout: int = 60) -> Dict[str, Any]:
        """Refresh the QR code by reconnecting.
        
        Args:
            headless: Whether to run the browser in headless mode
            timeout: Timeout in seconds for waiting for QR code
            
        Returns:
            Dictionary with refresh status and QR code if available
        """
        # Clean up existing resources
        self._cleanup()
        
        # Connect again
        return self.connect(headless=headless, timeout=timeout)
    
    def disconnect(self) -> Dict[str, Any]:
        """Disconnect from WhatsApp Web.
        
        Returns:
            Dictionary with disconnect status
        """
        try:
            # Clean up resources
            self._cleanup()
            
            return {
                "status": "success",
                "message": "Disconnected from WhatsApp Web"
            }
            
        except Exception as e:
            logger.error(f"Error disconnecting: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _cleanup(self) -> None:
        """Clean up resources."""
        # Close WebSocket if open
        if self.ws:
            try:
                self.ws.close()
                logger.info("WebSocket closed")
            except Exception as ws_error:
                logger.error(f"Error closing WebSocket: {str(ws_error)}")
            self.ws = None
        
        # Close browser if open
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser closed")
            except Exception as browser_error:
                logger.error(f"Error closing browser: {str(browser_error)}")
            self.driver = None
        
        # Update session status
        try:
            self.session.status = "disconnected"
            db.session.commit()
            logger.info("Session status updated to disconnected")
        except Exception as db_error:
            logger.error(f"Error updating session status: {str(db_error)}")
        
        self.is_connected = False