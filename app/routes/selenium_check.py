import os
import logging
import subprocess
from datetime import datetime
from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_login import login_required
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ensure logs directory exists
log_dir = os.path.join(os.getcwd(), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Set up file handler for selenium.log
selenium_log_file = os.path.join(log_dir, 'selenium.log')

# Initialize the log file with a header if it doesn't exist or is empty
if not os.path.exists(selenium_log_file) or os.path.getsize(selenium_log_file) == 0:
    with open(selenium_log_file, 'w') as f:
        f.write(f"{datetime.now().isoformat()} - INFO - Selenium log file initialized\n")
        f.write(f"{datetime.now().isoformat()} - INFO - This file logs Selenium integration status and errors\n")
        f.write(f"{datetime.now().isoformat()} - INFO - Note: AMD VideoProcessor errors are known non-critical issues\n")

file_handler = logging.FileHandler(selenium_log_file)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Create blueprint
bp = Blueprint('selenium_check', __name__, url_prefix='/selenium')

@bp.route('/', methods=['GET'])
@login_required
def index():
    """Display Selenium integration check page.
    
    Returns:
        Rendered template with Selenium integration status
    """
    # Check if ChromeDriver exists
    chromedriver_dir = os.path.join(os.getcwd(), 'app_data', 'chromedriver')
    
    # Determine the correct chromedriver executable based on OS
    if os.name == 'nt':  # Windows
        chromedriver_name = 'chromedriver.exe'
        setup_script = os.path.join(chromedriver_dir, 'setup_chromedriver.bat')
    else:  # Linux/Mac
        chromedriver_name = 'chromedriver'
        setup_script = os.path.join(chromedriver_dir, 'setup_chromedriver.sh')
    
    chromedriver_path = os.path.join(chromedriver_dir, chromedriver_name)
    chromedriver_exists = os.path.exists(chromedriver_path)
    setup_script_exists = os.path.exists(setup_script)
    
    # Get Chrome version if possible
    chrome_version = get_chrome_version()
    
    # Check if Selenium can start Chrome
    selenium_working = check_selenium_integration(chromedriver_path) if chromedriver_exists else False
    
    return render_template(
        'selenium/index.html',
        chromedriver_exists=chromedriver_exists,
        chromedriver_path=chromedriver_path,
        setup_script_exists=setup_script_exists,
        setup_script=setup_script,
        chrome_version=chrome_version,
        selenium_working=selenium_working,
        os_type=os.name
    )

@bp.route('/install', methods=['POST'])
@login_required
def install_chromedriver():
    """Install ChromeDriver using the appropriate setup script.
    
    Returns:
        Redirect to Selenium check page with status message
    """
    try:
        chromedriver_dir = os.path.join(os.getcwd(), 'app_data', 'chromedriver')
        
        # Determine the correct setup script based on OS
        if os.name == 'nt':  # Windows
            setup_script = os.path.join(chromedriver_dir, 'setup_chromedriver.bat')
            if os.path.exists(setup_script):
                result = subprocess.run([setup_script], shell=True, capture_output=True, text=True)
            else:
                flash('Setup script not found', 'danger')
                return redirect(url_for('selenium_check.index'))
        else:  # Linux/Mac
            setup_script = os.path.join(chromedriver_dir, 'setup_chromedriver.sh')
            if os.path.exists(setup_script):
                result = subprocess.run(['bash', setup_script], capture_output=True, text=True)
            else:
                flash('Setup script not found', 'danger')
                return redirect(url_for('selenium_check.index'))
        
        if result.returncode == 0:
            flash('ChromeDriver installed successfully', 'success')
        else:
            flash(f'Error installing ChromeDriver: {result.stderr}', 'danger')
            logger.error(f"Error installing ChromeDriver: {result.stderr}")
    except Exception as e:
        flash(f'Error installing ChromeDriver: {str(e)}', 'danger')
        logger.error(f"Error installing ChromeDriver: {str(e)}")
    
    return redirect(url_for('selenium_check.index'))

@bp.route('/check', methods=['POST'])
@login_required
def check_selenium():
    """Check if Selenium integration is working.
    
    Returns:
        JSON response with Selenium integration status
    """
    try:
        # Log the start of the check
        logger.info("Starting Selenium integration check")
        
        chromedriver_dir = os.path.join(os.getcwd(), 'app_data', 'chromedriver')
        
        # Determine the correct chromedriver executable based on OS
        if os.name == 'nt':  # Windows
            chromedriver_name = 'chromedriver.exe'
        else:  # Linux/Mac
            chromedriver_name = 'chromedriver'
        
        chromedriver_path = os.path.join(chromedriver_dir, chromedriver_name)
        logger.info(f"ChromeDriver path: {chromedriver_path}")
        
        if not os.path.exists(chromedriver_path):
            error_msg = 'ChromeDriver not found. Please install it first.'
            logger.error(error_msg)
            # Write to selenium.log
            log_file = os.path.join(os.getcwd(), 'logs', 'selenium.log')
            with open(log_file, 'a') as f:
                f.write(f"{datetime.now().isoformat()} - ERROR - {error_msg}\n")
            return jsonify({
                'status': 'error',
                'message': error_msg
            })
        
        # Check for AMD VideoProcessor errors in recent logs
        amd_error_detected = False
        if os.name == 'nt':  # Windows only
            try:
                # Use PowerShell to check for recent AMD errors
                cmd = 'powershell -Command "Get-EventLog -LogName Application -After (Get-Date).AddMinutes(-5) | Where-Object {$_.Message -like \'*AMD VideoProcessor*\'} | Select-Object -First 1 | Format-List"'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.stdout.strip():
                    amd_error_detected = True
                    logger.warning(f"AMD VideoProcessor error detected: {result.stdout.strip()}")
                    logger.info("This is a known issue with AMD graphics cards and doesn't affect WhatsApp functionality")
                    # Write to selenium.log
                    log_file = os.path.join(os.getcwd(), 'logs', 'selenium.log')
                    with open(log_file, 'a') as f:
                        f.write(f"{datetime.now().isoformat()} - WARNING - AMD VideoProcessor error detected. This is a known issue with AMD graphics cards and doesn't affect WhatsApp functionality.\n")
            except Exception as amd_error:
                logger.warning(f"Could not check for AMD errors: {str(amd_error)}")
        
        # Check if Selenium can start Chrome
        selenium_working = check_selenium_integration(chromedriver_path)
        
        if selenium_working:
            success_msg = 'Selenium integration is working correctly.'
            if amd_error_detected:
                success_msg += ' (Note: AMD VideoProcessor errors were detected but these are known issues that don\'t affect functionality)'
            logger.info(success_msg)
            return jsonify({
                'status': 'success',
                'message': success_msg
            })
        else:
            error_msg = 'Selenium integration is not working. Please check the logs for more information.'
            logger.error(error_msg)
            return jsonify({
                'status': 'error',
                'message': error_msg
            })
    except Exception as e:
        error_msg = f"Error checking Selenium integration: {str(e)}"
        logger.error(error_msg)
        # Write to selenium.log
        log_file = os.path.join(os.getcwd(), 'logs', 'selenium.log')
        with open(log_file, 'a') as f:
            f.write(f"{datetime.now().isoformat()} - ERROR - {error_msg}\n")
        return jsonify({
            'status': 'error',
            'message': error_msg
        })

@bp.route('/logs', methods=['GET'])
@login_required
def get_logs():
    """Get Selenium integration logs.
    
    Returns:
        JSON response with Selenium integration logs
    """
    try:
        # Get the last 100 lines of the log file
        log_file = os.path.join(os.getcwd(), 'logs', 'selenium.log')
        selenium_logs = []
        
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                selenium_logs = f.readlines()
                selenium_logs = selenium_logs[-100:] if len(selenium_logs) > 100 else selenium_logs
        else:
            selenium_logs = ['No selenium.log file found']
        
        # Try to capture DevTools errors from system logs
        devtools_errors = []
        amd_errors = []
        try:
            # On Windows, we can use PowerShell to get recent Application logs
            if os.name == 'nt':
                # Get Chrome and DevTools related errors from the last hour
                cmd = 'powershell -Command "Get-EventLog -LogName Application -After (Get-Date).AddHours(-1) | Where-Object {$_.Source -like \'*Chrome*\' -or $_.Message -like \'*DevTools*\' -or $_.Message -like \'*Selenium*\'} | Select-Object TimeGenerated, Message | Format-List"'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.stdout.strip():
                    devtools_errors = [f"System Log: {line}" for line in result.stdout.splitlines() if line.strip()]
                
                # Specifically look for AMD VideoProcessor errors
                amd_cmd = 'powershell -Command "Get-EventLog -LogName Application -After (Get-Date).AddHours(-1) | Where-Object {$_.Message -like \'*AMD VideoProcessor*\'} | Select-Object TimeGenerated, Message | Format-List"'
                amd_result = subprocess.run(amd_cmd, shell=True, capture_output=True, text=True)
                if amd_result.stdout.strip():
                    amd_errors = [f"AMD Error: {line}" for line in amd_result.stdout.splitlines() if line.strip()]
                    # Log these as warnings since they're non-critical
                    for error in amd_errors:
                        logger.warning(f"AMD VideoProcessor error detected: {error}")
                        logger.info("This is a known issue with AMD graphics cards and doesn't affect WhatsApp functionality")
                        # Write to selenium.log
                        with open(log_file, 'a') as f:
                            f.write(f"{datetime.now().isoformat()} - WARNING - {error} (This is a known non-critical issue)\n")
            
            # For Linux, we could check syslog or journalctl
            elif os.path.exists('/var/log/syslog'):
                cmd = 'grep -i "chrome\|devtools\|selenium" /var/log/syslog | tail -n 50'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.stdout.strip():
                    devtools_errors = [f"System Log: {line}" for line in result.stdout.splitlines() if line.strip()]
            
            # Log any DevTools errors we found
            if devtools_errors:
                for error in devtools_errors:
                    logger.warning(f"Found DevTools error: {error}")
                    # Also write to selenium.log
                    with open(log_file, 'a') as f:
                        f.write(f"{datetime.now().isoformat()} - WARNING - {error}\n")
        except Exception as e:
            logger.error(f"Error getting system logs: {str(e)}")
            # Also write to selenium.log
            with open(log_file, 'a') as f:
                f.write(f"{datetime.now().isoformat()} - ERROR - Error getting system logs: {str(e)}\n")
        
        # Combine logs with clear sections
        all_logs = selenium_logs
        
        # Add AMD errors with a special header if they exist
        if amd_errors:
            all_logs.append('\n--- AMD VideoProcessor Errors (Known Non-Critical Issues) ---\n')
            all_logs.extend(amd_errors)
        
        # Add other system logs if they exist
        if devtools_errors:
            all_logs.append('\n--- Other System Logs ---\n')
            all_logs.extend(devtools_errors)
        
        return jsonify({
            'status': 'success',
            'logs': all_logs
        })
    except Exception as e:
        error_msg = f"Error getting Selenium logs: {str(e)}"
        logger.error(error_msg)
        # Also write to selenium.log
        log_file = os.path.join(os.getcwd(), 'logs', 'selenium.log')
        with open(log_file, 'a') as f:
            f.write(f"{datetime.now().isoformat()} - ERROR - {error_msg}\n")
        return jsonify({
            'status': 'error',
            'message': error_msg
        })

def get_chrome_version():
    """Get the installed Chrome version.
    
    Returns:
        str: Chrome version or 'Unknown' if not found
    """
    try:
        if os.name == 'nt':  # Windows
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Google\Chrome\BLBeacon')
            version, _ = winreg.QueryValueEx(key, 'version')
            return version
        else:  # Linux/Mac
            result = subprocess.run(['google-chrome', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip().split()[-1]
            else:
                return 'Unknown'
    except Exception as e:
        logger.error(f"Error getting Chrome version: {str(e)}")
        return 'Unknown'

def check_selenium_integration(chromedriver_path):
    """Check if Selenium integration is working.
    
    Args:
        chromedriver_path: Path to ChromeDriver executable
    
    Returns:
        bool: True if Selenium integration is working, False otherwise
    """
    try:
        # Set up Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # Add logging preferences to capture browser console logs
        chrome_options.add_argument('--enable-logging')
        chrome_options.add_argument('--v=1')
        
        # Log the ChromeDriver path being used
        logger.info(f"Using ChromeDriver at: {chromedriver_path}")
        
        # Initialize Chrome driver
        service = Service(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Try to navigate to a simple page
        logger.info("Navigating to about:blank")
        driver.get('about:blank')
        
        # Check for any browser logs/errors
        try:
            logs = driver.get_log('browser')
            if logs:
                logger.warning(f"Browser logs found: {logs}")
                # Write to selenium.log file
                log_file = os.path.join(os.getcwd(), 'logs', 'selenium.log')
                with open(log_file, 'a') as f:
                    f.write(f"{datetime.now().isoformat()} - WARNING - Browser logs: {logs}\n")
        except Exception as log_error:
            logger.warning(f"Could not retrieve browser logs: {str(log_error)}")
        
        # Check for AMD VideoProcessor errors specifically
        # These errors often appear in the console but don't affect functionality
        if os.name == 'nt':  # Windows only
            try:
                # Use PowerShell to check for recent AMD errors in the Application log
                cmd = 'powershell -Command "Get-EventLog -LogName Application -After (Get-Date).AddMinutes(-5) | Where-Object {$_.Message -like \'*AMD VideoProcessor*\'} | Select-Object -First 3 | Format-List"'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.stdout.strip():
                    # Format the error message nicely
                    error_lines = result.stdout.strip().splitlines()
                    formatted_error = '\n'.join(error_lines)
                    
                    logger.warning(f"AMD VideoProcessor error detected:\n{formatted_error}")
                    logger.info("This is a known issue with AMD graphics cards and doesn't affect WhatsApp functionality")
                    
                    # Write to selenium.log file with clear formatting
                    log_file = os.path.join(os.getcwd(), 'logs', 'selenium.log')
                    with open(log_file, 'a') as f:
                        f.write(f"{datetime.now().isoformat()} - WARNING - AMD VideoProcessor error detected:\n{formatted_error}\n")
                        f.write(f"{datetime.now().isoformat()} - INFO - This is a known non-critical issue with AMD graphics cards and doesn't affect WhatsApp functionality.\n")
            except Exception as amd_error:
                logger.warning(f"Could not check for AMD errors: {str(amd_error)}")
        
        # Close the driver
        logger.info("Closing Chrome driver")
        driver.quit()
        
        logger.info("Selenium integration check completed successfully")
        return True
    except Exception as e:
        error_msg = f"Error checking Selenium integration: {str(e)}"
        logger.error(error_msg)
        # Write to selenium.log file
        log_file = os.path.join(os.getcwd(), 'logs', 'selenium.log')
        with open(log_file, 'a') as f:
            f.write(f"{datetime.now().isoformat()} - ERROR - {error_msg}\n")
        return False