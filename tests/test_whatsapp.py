"""Test script for WhatsApp integration."""

import os
import sys
import time
import logging
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.services.whatsapp.auth import WhatsAppAuth
from app.services.whatsapp.message import WhatsAppMessageService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app context
app = create_app()
app_context = app.app_context()
app_context.push()

def test_create_session():
    """Test creating a WhatsApp session."""
    logger.info("Testing session creation...")
    
    # Create session
    result = WhatsAppAuth.create_session("Test Session")
    
    logger.info(f"Session creation result: {result}")
    
    if result.get("status") == "success":
        session_id = result.get("session_id")
        logger.info(f"Created session with ID: {session_id}")
        
        # Get QR code
        qr_result = WhatsAppAuth.get_session_qr(session_id)
        logger.info(f"QR code available: {qr_result.get('qr_code') is not None}")
        
        # Wait for user to scan QR code
        logger.info("Please scan the QR code to authenticate WhatsApp Web")
        logger.info("QR code data: " + qr_result.get("qr_code", "")[:50] + "...")
        
        # Wait for connection
        max_attempts = 30
        for i in range(max_attempts):
            status_result = WhatsAppAuth.get_session_status(session_id)
            status = status_result.get("status")
            
            logger.info(f"Session status: {status}")
            
            if status == "connected":
                logger.info("Successfully connected to WhatsApp!")
                return session_id
            
            # Refresh QR code if needed
            if i > 0 and i % 5 == 0:
                logger.info("Refreshing QR code...")
                WhatsAppAuth.refresh_session(session_id)
            
            time.sleep(5)
        
        logger.error("Failed to connect to WhatsApp after multiple attempts")
        return None
    else:
        logger.error(f"Failed to create session: {result.get('error')}")
        return None

def test_send_message(session_id, recipient, message):
    """Test sending a WhatsApp message."""
    if not session_id:
        logger.error("No session ID provided")
        return
    
    logger.info(f"Testing message sending to {recipient}...")
    
    # Create message service
    message_service = WhatsAppMessageService(session_id=session_id)
    
    # Send message
    result = message_service.send_message(
        recipient=recipient,
        message=message
    )
    
    logger.info(f"Message sending result: {result}")
    
    if result.get("status") == "success":
        logger.info(f"Successfully sent message with ID: {result.get('message_id')}")
    else:
        logger.error(f"Failed to send message: {result.get('error')}")

def test_queue_message(session_id, recipient, message):
    """Test queuing a WhatsApp message."""
    if not session_id:
        logger.error("No session ID provided")
        return
    
    logger.info(f"Testing message queuing to {recipient}...")
    
    # Create message service
    message_service = WhatsAppMessageService(session_id=session_id)
    
    # Queue message
    result = message_service.queue_message(
        recipient=recipient,
        message=message,
        scheduled_at=datetime.now()
    )
    
    logger.info(f"Message queuing result: {result}")
    
    if result.get("status") == "success":
        logger.info(f"Successfully queued message with ID: {result.get('queue_id')}")
        
        # Process queue
        process_result = message_service.process_queue()
        logger.info(f"Queue processing result: {process_result}")
    else:
        logger.error(f"Failed to queue message: {result.get('error')}")

def main():
    """Main test function."""
    try:
        # Test creating a session
        session_id = test_create_session()
        
        if session_id:
            # Get recipient from command line or use default
            recipient = sys.argv[1] if len(sys.argv) > 1 else input("Enter recipient phone number: ")
            
            # Test sending a message
            test_send_message(session_id, recipient, "Hello from Blastify WhatsApp integration test!")
            
            # Test queuing a message
            test_queue_message(session_id, recipient, "This is a queued message from Blastify!")
            
            # Disconnect session
            logger.info("Disconnecting session...")
            result = WhatsAppAuth.disconnect_session(session_id)
            logger.info(f"Disconnect result: {result}")
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
    finally:
        # Clean up
        app_context.pop()

if __name__ == "__main__":
    main()