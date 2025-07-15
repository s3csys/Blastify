import base64
import io
import cv2
import numpy as np
import zxingcpp
from PIL import Image

def decode_base64_qr(base64_data):
    """
    Decode a QR code directly from base64 encoded image data using zxing-cpp
    
    Args:
        base64_data (str): Base64 encoded image data, can include data URI prefix
                           (e.g., 'data:image/png;base64,...')
    
    Returns:
        str: Decoded QR code content
        None: If no QR code was found or could not be decoded
    """
    try:
        # Remove data URI prefix if present
        if ';base64,' in base64_data:
            base64_data = base64_data.split(';base64,')[1]
        
        # Decode base64 to binary
        image_data = base64.b64decode(base64_data)
        
        # Create an in-memory image file
        pil_image = Image.open(io.BytesIO(image_data))
        
        # Convert PIL image to OpenCV format (numpy array)
        cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        
        # Decode QR code using zxing-cpp
        qr_codes = zxingcpp.read_barcodes(cv_image)
        
        # Return the decoded data if found
        if qr_codes:
            return qr_codes[0].text
        else:
            return None
    except Exception as e:
        print(f"Error decoding QR code: {e}")
        return None

# Example usage
if __name__ == "__main__":
    # Example with data URI prefix
    qr_data = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAOQAAADkCAYAAACIV4iNAAAAAXNSR0IArs4c6QAAGyRJREFUeF7t3WuSG7mxBWB5C3P3MY65+1+DI7wQr0EOKhyaKjaFD4cJFNnt1N8E8nEeANjqxz/++POv798u+veff/9rWOn//vn/pU7u89/nU/374uonrad89/Wv7lf1V+Mp/CSG1ftT/tXfM/F/tCF/DZsMJEEoLsLakGOEduMr/sXfM/E25AA1ESJBKC7C2pC/uSFTAUhQeuLsjqdPEM2fGlT4qL9qP3qCqj/xo/6VX3EdaMJH/Wl/Or/mUT+3+OmGVIPVginAAkTxGQCOazRqj8jqORAkSFUL51X8ymf4sJX87Yhw6+yVgGXwF4tGNV/9/4/W3+Pbvy+IQ8qTAnViam4DLD7AEifgCk+V/f/2fprQ94ppGoY7Ve8DVn7gd/Phm/8ZE1PTAlqpgHlOMaVT/H7WlqvE1eCqOKp/oSd+tf+alz4VG/Qan9X4zujh6W/lzUVfAqoAFQ87U+CluBmCBhhkM6j+VK8q+uFTxvyI8JtyAMm7yagNuT4SVs9MK7Gd+aAbkO2Iau6/uX+dzvg9IKYMczoI5SAnMkf/da5tKBOID0J03pav7qfGYArT9IqPnoSCi8JeHd+GboaT+dfvZ5fZdWAakj7FVf+qgDakP4VEskBUuVDhpdeqvFUb6vXtyHv/v6kCBUBfUOeEboaD/GnuPjdHW9DtiFLGtMTug2ZwfvpDKkTTnE9qSQw7d/95Mjo/bhaBtETXvNV8Unnq/Kd1tP6FD/lu8Xf+os6IkBxCaYNmf63gvBKD4AZgR7XVPlO62l9G7L45EwJlaF1g6ie4hKE4qlB0vVVfNS/8lcPiLR+yvcz+fuGDFBLBSvDKR609nBptV8JUIZJ92veFC/Nr3qKf/kbUgAKgDQuQaUnsOqLYAlY+Ch/tT/hofrqX/2pfmrY1fxr/pn4W92QqwlLCVq9XvOIIAlU+1cbXIZQP8JD86p+yl8bEj8QvJqwlKDV6zWPBCyBan8b8vxFK+FV5V/5Z+J9Qx5QqhLybgZqQ34xQ844erRGAt39BEmfJKtvNOGnA2B1XP2kBk75S/NrveZZjZ/0rH5n9PXSn/ZICdX61QQpnwjQ/lcLRv1JgOJDAlT+z45vOt9t3jbk4MkqwX52wWg+CaoNOf5mfeH3CP82ZBvyl76UoNqQmw2pE7Ma1xNN+bVfTyTll8C0f3X96rzVeTSvPqPrBSG81L/wUf+qr/1pXAfchydrWiBdvxrAmQGTHiUA5aoSrHkUlwHUfzWu+Vf3v1pP1fm1f2b+t/69rDqBZwYUSMd4GzJB6+PaNuQYvxm9tiEPGLYh25A1BNqQJwR0QgvsNqQQGseF/8wNkbxYvuKT9b8cOoubpI34egAAAABJRU5ErkJggg=="
    
    result = decode_base64_qr(qr_data)
    print(f"Decoded QR code content: {result}")