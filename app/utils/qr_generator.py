"""QR code generation utilities."""

import qrcode
import io
import base64
import logging

logger = logging.getLogger(__name__)

def generate_qr_code(data, size=10):
    """Generate a QR code image from data.
    
    Args:
        data: The data to encode in the QR code
        size: The size of the QR code (box size in pixels)
        
    Returns:
        Dictionary with status and QR code data as base64 string
    """
    try:
        # Create QR code instance
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
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