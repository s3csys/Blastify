"""QR code generation utilities."""

import qrcode
import base64
import io
import os
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Create a file handler for this logger
def setup_logger():
    """Set up logger with file handler."""
    try:
        # Create logs directory if it doesn't exist
        log_dir = os.path.join(os.getcwd(), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # Create a file handler
        log_file = os.path.join(log_dir, 'qr_generator.log')
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
        
        logger.info(f"QR Generator logger initialized. Log file: {log_file}")
    except Exception as e:
        print(f"Error setting up QR generator logger: {str(e)}")

# Set up the logger
setup_logger()

def generate_qr_code(data, size=10):
    """Generate a QR code image from data.
    
    Args:
        data: The data to encode in the QR code
        size: The size of the QR code (box size in pixels)
        
    Returns:
        Dictionary with status and QR code data as base64 string
    """
    try:
        # Log the data being encoded (truncated for security)
        if isinstance(data, str) and len(data) > 20:
            logger.info(f"Generating QR code for data starting with: {data[:20]}...")
        
        # Create QR code instance with higher error correction
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,  # Higher error correction for better scanning
            box_size=size,
            border=4,
        )
        
        # Add data to the QR code
        qr.add_data(data)
        qr.make(fit=True)
        
        # Create an image from the QR code
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save the image to a bytes buffer
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        
        # Encode the image as base64
        img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return {
            'status': 'success',
            'qr_data': f"data:image/png;base64,{img_str}"
        }
        
    except Exception as e:
        logger.error(f"Error generating QR code: {str(e)}")
        return {'status': 'failed', 'error': str(e)}