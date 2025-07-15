# WhatsApp QR Code Troubleshooting Guide

This guide provides steps to troubleshoot issues with WhatsApp Web QR code generation and scanning.

## Common Issues and Solutions

### QR Code Not Generating

1. **Check Dependencies**
   - Ensure all required dependencies are installed:
     ```
     pip install -r requirements.txt
     ```
   - Specifically, make sure these packages are installed:
     - selenium
     - webdriver-manager
     - zxingcpp (version 2.3.0 or higher)
     - Pillow (PIL)
     - opencv-python
     - numpy

2. **Check Chrome Installation**
   - Make sure Google Chrome is installed on your system
   - The application checks common installation paths for Chrome

3. **Check ChromeDriver**
   - The application will attempt to download the appropriate ChromeDriver automatically
   - If this fails, you can manually download the ChromeDriver that matches your Chrome version from: https://chromedriver.chromium.org/downloads
   - Place it in the `app_data/chromedriver` directory

4. **Check Logs**
   - Look for log files in the `logs` directory
   - Key log files to check:
     - `selenium.log`
     - Screenshots of QR code attempts (e.g., `whatsapp_before_qr.png`, `detected_qr.png`)
     - Processed images for QR detection (e.g., `processed_original.png`, `processed_grayscale.png`)

### QR Code Not Scanning

1. **Check QR Code Image Quality**
   - The QR code should be clear and not distorted
   - Try running the QR test utility:
     ```
     python -m app.utils.qr_test --scan
     ```

2. **Try Different Browsers**
   - If Chrome is having issues, you might need to update Chrome to the latest version

3. **Check WhatsApp Web Status**
   - Verify that WhatsApp Web is accessible from your network
   - Try accessing https://web.whatsapp.com/ directly in your browser

4. **Check for WhatsApp Web Updates**
   - WhatsApp Web occasionally changes its UI elements, which might affect QR code detection
   - Check if there are any recent updates to the WhatsApp Web interface

## Debugging Steps

1. **Enable Verbose Logging**
   - Set the logging level to DEBUG in your application configuration

2. **Run the QR Test Utility**
   - Use the included QR test utility to verify QR code generation and scanning:
     ```
     python -m app.utils.qr_test --data="https://web.whatsapp.com" --output="test_qr.png" --scan
     ```

3. **Check Generated Images**
   - Examine the images in the `logs` directory to see what's being captured
   - Look for files like:
     - `qr_full_screenshot.png` - Full page screenshot
     - `qr_code.png` - Cropped QR code
     - `detected_qr_*.png` - QR code with detection boundary
     - `processed_*.png` - Processed images for QR detection

4. **Verify zxingcpp Installation**
   - Run the following Python code to verify zxingcpp is working correctly:
     ```python
     import zxingcpp
     print(zxingcpp.__version__)
     ```

## Advanced Troubleshooting

1. **Try Non-Headless Mode**
   - Set `headless=False` when calling the `connect()` method to see the browser in action

2. **Increase Timeout**
   - Increase the timeout value when calling the `connect()` method to give more time for the QR code to appear

3. **Check Network Connectivity**
   - Ensure your system can access WhatsApp Web servers
   - Check for any proxy or firewall settings that might be blocking access

4. **Check for Element Changes**
   - WhatsApp Web might change their element IDs or classes
   - Check the page source to see if the selectors used in the code still match

## Getting Help

If you continue to experience issues after trying these troubleshooting steps, please:

1. Collect all log files from the `logs` directory
2. Note your Chrome and ChromeDriver versions
3. Provide details about your operating system and environment
4. Contact support with this information for further assistance