"""WhatsApp Web client implementation."""

import json
import time
import logging
import base64
import threading
import os
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any, Union

import websocket
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from app import db
from app.models.whatsapp_session import WhatsAppSession, WhatsAppDevice
from app.utils.qr_generator import generate_qr_code

logger = logging.getLogger(__name__)

class WhatsAppClient:
    """Client for interacting with WhatsApp Web."""
    
    def __init__(self, session_id: str = None, session_name: str = None):
        """Initialize the WhatsApp client.
        
        Args:
            session_id: The session ID to use (if None, a new session will be created)
            session_name: The name for the session (required if session_id is None)
        """
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
        if session_id:
            self.session = WhatsAppSession.get_session_by_id(session_id)
            if not self.session:
                raise ValueError(f"Session with ID {session_id} not found")
            self.session_name = self.session.name
        elif session_name:
            # Create a new session
            self.session = WhatsAppSession(
                name=session_name,
                session_id=f"session_{int(time.time())}",
                status="disconnected"
            )
            db.session.add(self.session)
            db.session.commit()
            self.session_id = self.session.session_id
        else:
            raise ValueError("Either session_id or session_name must be provided")
    
    def connect(self, headless: bool = True, timeout: int = 60) -> Dict[str, Any]:
        """Connect to WhatsApp Web and get QR code for authentication.
        
        Args:
            headless: Whether to run the browser in headless mode
            timeout: Timeout in seconds for waiting for QR code
            
        Returns:
            Dictionary with connection status and QR code if available
        """
        try:
            # Update session status
            self.session.status = "connecting"
            db.session.commit()
            
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
                
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Navigate to WhatsApp Web
            self.driver.get("https://web.whatsapp.com/")
            
            # Wait for QR code to appear
            try:
                qr_canvas = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.XPATH, "//canvas[contains(@aria-label, 'Scan me!')]")),
                )
                
                # Get QR code data
                qr_data = self.driver.execute_script(
                    "return arguments[0].toDataURL('image/png');", qr_canvas
                )
                
                # Store QR code
                self.qr_code = qr_data
                self.session.qr_code = qr_data
                db.session.commit()
                
                # Start a thread to check for successful login
                threading.Thread(target=self._wait_for_login, daemon=True).start()
                
                return {
                    "status": "success",
                    "message": "QR code generated successfully",
                    "qr_code": qr_data
                }
                
            except TimeoutException:
                # Check if we're already logged in
                if "_wa_wam_authenticated" in self.driver.get_cookies():
                    self._handle_successful_login()
                    return {
                        "status": "success",
                        "message": "Already authenticated"
                    }
                else:
                    self._cleanup()
                    return {
                        "status": "failed",
                        "error": "Timeout waiting for QR code"
                    }
                    
        except Exception as e:
            logger.error(f"Error connecting to WhatsApp Web: {str(e)}")
            self._cleanup()
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _wait_for_login(self, timeout: int = 300) -> None:
        """Wait for successful login after QR code scan.
        
        Args:
            timeout: Timeout in seconds for waiting for login
        """
        try:
            # Wait for chat list to appear (indicates successful login)
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, "//div[@id='pane-side']")),
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
            caption: The caption for the media
            media_url: URL to the media to send
            
        Returns:
            Dictionary with send status and message ID if successful
        """
        try:
            # Download media
            response = requests.get(media_url, stream=True)
            if response.status_code != 200:
                return {
                    "status": "failed",
                    "error": f"Failed to download media: {response.status_code}"
                }
            
            # Get media content and type
            media_data = response.content
            media_type = response.headers.get('Content-Type', '').split('/')[0]
            
            # Convert to base64
            media_b64 = base64.b64encode(media_data).decode('utf-8')
            
            # Execute JavaScript to send media message
            result = self.driver.execute_script(
                f"""
                return window.WWebJS.sendMessage(
                    "{phone}@c.us",
                    "{caption}",
                    {{linkPreview: null, media: {{data: "{media_b64}", mimetype: "{response.headers.get('Content-Type')}", type: "{media_type}"}} }}
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
    
    def get_qr_code(self) -> Dict[str, Any]:
        """Get the current QR code for authentication.
        
        Returns:
            Dictionary with QR code data or error
        """
        if self.is_connected:
            return {
                "status": "failed",
                "error": "Already connected"
            }
        
        if self.qr_code:
            return {
                "status": "success",
                "qr_code": self.qr_code
            }
        else:
            return {
                "status": "failed",
                "error": "QR code not available"
            }
    
    def refresh_qr_code(self) -> Dict[str, Any]:
        """Refresh the QR code for authentication.
        
        Returns:
            Dictionary with new QR code data or error
        """
        if self.is_connected:
            return {
                "status": "failed",
                "error": "Already connected"
            }
        
        # Clean up existing session
        self._cleanup()
        
        # Connect again to get new QR code
        return self.connect()
    
    def disconnect(self) -> Dict[str, Any]:
        """Disconnect from WhatsApp Web.
        
        Returns:
            Dictionary with disconnect status
        """
        try:
            self._cleanup()
            
            return {
                "status": "success",
                "message": "Disconnected successfully"
            }
            
        except Exception as e:
            logger.error(f"Error disconnecting: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _cleanup(self) -> None:
        """Clean up resources."""
        # Close WebSocket
        if self.ws:
            self.ws.close()
            self.ws = None
        
        # Stop WebSocket thread
        self.ws_thread = None
        
        # Close browser
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.error(f"Error closing browser: {str(e)}")
            finally:
                self.driver = None
        
        # Update session status
        if self.session:
            self.session.status = "disconnected"
            db.session.commit()
        
        self.is_connected = False
        self.qr_code = None