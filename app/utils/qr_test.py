"""Test script for QR code generation and scanning."""

import os
import sys
import logging
import base64
import argparse
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path to import app modules
parent_dir = str(Path(__file__).parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import QR generator
from app.utils.qr_generator import generate_qr_code

def test_qr_generation(data="https://web.whatsapp.com", size=10, output_path=None):
    """Test QR code generation.
    
    Args:
        data: The data to encode in the QR code
        size: The size of the QR code (box size in pixels)
        output_path: Path to save the QR code image (optional)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Testing QR code generation with data: {data[:30]}...")
        
        # Generate QR code
        result = generate_qr_code(data, size)
        
        if result.get("status") != "success":
            logger.error(f"Failed to generate QR code: {result.get('error')}")
            return False
        
        # Get QR code data
        qr_data = result.get("qr_data")
        
        if not qr_data or not qr_data.startswith("data:image/png;base64,"):
            logger.error("Invalid QR code data format")
            return False
        
        logger.info("Successfully generated QR code")
        
        # Save QR code to file if output path is provided
        if output_path:
            try:
                # Extract base64 data
                base64_data = qr_data.replace("data:image/png;base64,", "")
                
                # Decode base64 data
                image_data = base64.b64decode(base64_data)
                
                # Save to file
                with open(output_path, "wb") as f:
                    f.write(image_data)
                
                logger.info(f"Saved QR code to {output_path}")
            except Exception as e:
                logger.error(f"Error saving QR code to file: {str(e)}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error testing QR code generation: {str(e)}")
        return False

def test_qr_scanning(image_path):
    """Test QR code scanning.
    
    Args:
        image_path: Path to the QR code image
        
    Returns:
        Decoded data if successful, None otherwise
    """
    try:
        logger.info(f"Testing QR code scanning with image: {image_path}")
        
        # Check if zxingcpp is installed
        try:
            import zxingcpp
        except ImportError:
            logger.error("zxingcpp is not installed. Please install it with: pip install zxingcpp")
            return None
        
        # Check if OpenCV is installed
        try:
            import cv2
        except ImportError:
            logger.error("OpenCV is not installed. Please install it with: pip install opencv-python")
            return None
        
        # Read the image
        img = cv2.imread(image_path)
        
        if img is None:
            logger.error(f"Failed to load image from {image_path}")
            return None
        
        # Scan for QR codes
        qr_codes = zxingcpp.read_barcodes(img)
        
        if not qr_codes:
            logger.error("No QR codes found in the image")
            return None
        
        # Get the first QR code
        qr_code = qr_codes[0]
        
        # Get the QR code data
        qr_text = qr_code.text
        
        logger.info(f"Successfully scanned QR code: {qr_text[:30]}...")
        
        return qr_text
    
    except Exception as e:
        logger.error(f"Error scanning QR code: {str(e)}")
        return None

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test QR code generation and scanning")
    parser.add_argument("--data", default="https://web.whatsapp.com", help="Data to encode in the QR code")
    parser.add_argument("--size", type=int, default=10, help="Size of the QR code (box size in pixels)")
    parser.add_argument("--output", default="qr_test.png", help="Path to save the QR code image")
    parser.add_argument("--scan", action="store_true", help="Scan the generated QR code")
    
    args = parser.parse_args()
    
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Set output path
    output_path = os.path.join(logs_dir, args.output)
    
    # Test QR code generation
    success = test_qr_generation(args.data, args.size, output_path)
    
    if not success:
        logger.error("QR code generation test failed")
        return
    
    # Test QR code scanning if requested
    if args.scan:
        qr_text = test_qr_scanning(output_path)
        
        if qr_text:
            logger.info(f"QR code scanning test passed. Decoded data: {qr_text}")
        else:
            logger.error("QR code scanning test failed")

if __name__ == "__main__":
    main()