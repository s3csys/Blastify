import json
import sys
from qr_decoder import decode_base64_qr

def main():
    """
    Command-line tool to decode QR codes from base64 data
    
    Usage:
        python decode_qr_cli.py <json_file>
        python decode_qr_cli.py <base64_string>
    
    If a JSON file is provided, it should contain a 'qr_code' field with the base64 data.
    Otherwise, the script will treat the input as a direct base64 string.
    """
    if len(sys.argv) < 2:
        print("Error: Please provide either a JSON file path or a base64 string")
        print("Usage: python decode_qr_cli.py <json_file>")
        print("       python decode_qr_cli.py <base64_string>")
        return
    
    input_data = sys.argv[1]
    
    # Check if input is a JSON file
    if input_data.endswith('.json'):
        try:
            with open(input_data, 'r') as f:
                data = json.load(f)
                if 'qr_code' not in data:
                    print("Error: JSON file does not contain 'qr_code' field")
                    return
                base64_data = data['qr_code']
        except Exception as e:
            print(f"Error reading JSON file: {e}")
            return
    else:
        # Treat input as direct base64 string
        base64_data = input_data
    
    # Decode the QR code
    result = decode_base64_qr(base64_data)
    
    if result:
        print(f"Decoded QR code content: {result}")
    else:
        print("Failed to decode QR code or no QR code found")

if __name__ == "__main__":
    main()