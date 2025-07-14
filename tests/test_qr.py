"""Test script for WhatsApp QR code generation."""

import sys
import os
import time
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the current directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the WhatsAppClient directly
from app.services.whatsapp.client import WhatsAppClient

def test_qr_generation():
    """Test QR code generation for WhatsApp."""
    logger.info("Testing WhatsApp QR code generation...")
    
    # Create a new session with a unique name
    session_name = f"Test Session {int(time.time())}"
    logger.info(f"Creating session with name: {session_name}")
    
    try:
        # Create a new WhatsApp client
        client = WhatsAppClient(session_name=session_name)
        logger.info(f"Created client with session ID: {client.session_id}")
        
        # Connect to WhatsApp Web to get QR code
        result = client.connect(headless=True)
        logger.info(f"Connection result: {json.dumps(result, indent=2)}")
        
        if result.get("status") == "success":
            logger.info("Successfully generated QR code")
            logger.info(f"QR code available: {result.get('qr_code') is not None}")
            return True
        else:
            logger.error(f"Failed to connect: {result.get('error')}")
            return False
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        return False

if __name__ == "__main__":
    test_qr_generation()