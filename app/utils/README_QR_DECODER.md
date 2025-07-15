# QR Code Decoder for Base64 Data

This utility allows you to decode QR codes directly from base64 encoded image data without needing to save the image to disk first. This is particularly useful for processing QR codes received from APIs or web services.

## Files

- `qr_decoder.py` - The main utility for decoding base64 QR codes
- `decode_qr_cli.py` - A command-line interface for the decoder
- `example_qr.json` - An example JSON file containing a base64 encoded QR code

## Requirements

To use this utility, you need to install the following Python packages:

```bash
pip install pillow opencv-python zxing-cpp
```

Note: `zxing-cpp` is a modern barcode scanning library that doesn't require additional system dependencies, making it easier to install than alternatives like pyzbar.

## Usage

### As a Python Module

```python
from qr_decoder import decode_base64_qr

# With data URI prefix
base64_data = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...."
result = decode_base64_qr(base64_data)
print(f"Decoded QR code content: {result}")

# Or with just the base64 data
base64_only = "iVBORw0KGgoAAAANSUhEUgAA...."
result = decode_base64_qr(base64_only)
print(f"Decoded QR code content: {result}")
```

### From Command Line

1. Decode from a JSON file containing a 'qr_code' field:

```bash
python decode_qr_cli.py example_qr.json
```

2. Decode directly from a base64 string:

```bash
python decode_qr_cli.py "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...."
```

## Integration with WhatsApp QR Code

This utility can be used to decode WhatsApp QR codes received from the WhatsApp Web API. The QR code data is typically returned as a base64 encoded string in a JSON response.

Example of processing a WhatsApp QR code response:

```python
import json
from qr_decoder import decode_base64_qr

# Parse the JSON response from WhatsApp API
response_data = json.loads(whatsapp_response)

# Extract the QR code data
qr_code_data = response_data.get('qr_code')

# Decode the QR code
if qr_code_data:
    decoded_content = decode_base64_qr(qr_code_data)
    print(f"Scan this link with WhatsApp: {decoded_content}")
else:
    print("No QR code found in the response")
```

## How It Works

The decoder works by:

1. Extracting the base64 data from the input (removing any data URI prefix)
2. Decoding the base64 string to binary image data
3. Creating an in-memory image using PIL (Pillow)
4. Converting the PIL image to OpenCV format (numpy array)
5. Using zxing-cpp to detect and decode any QR codes in the image
6. Returning the decoded text content

This approach avoids the need to save temporary files to disk, making it efficient for processing QR codes in memory.