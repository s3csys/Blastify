# Blastify

A messaging platform with WhatsApp integration capabilities.

## Installation

1. Clone the repository

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables by copying `.env.example` to `.env` and updating the values.

4. Initialize the database:
   ```bash
   flask db upgrade
   ```

5. Run the application:
   ```bash
   python run.py
   ```

## ChromeDriver Setup (Cross-Platform Support)

This application uses Selenium with ChromeDriver to interact with WhatsApp Web. To ensure cross-platform compatibility, follow these steps:

### Automatic Setup

#### Windows
Run the setup script from the project root directory:
```batch
app_data\chromedriver\setup_chromedriver.bat
```

#### Linux/macOS
Run the setup script from the project root directory:
```bash
chmod +x app_data/chromedriver/setup_chromedriver.sh
./app_data/chromedriver/setup_chromedriver.sh
```

### Manual Setup

1. Download the appropriate ChromeDriver for your Chrome version and operating system from:
   - Chrome for Testing: https://googlechromelabs.github.io/chrome-for-testing/

2. Extract the ZIP file and place the ChromeDriver executable in the `app_data/chromedriver` directory:
   - For Windows: `chromedriver.exe`
   - For Linux/macOS: `chromedriver` (make it executable with `chmod +x chromedriver`)

For more detailed instructions, see the README in the `app_data/chromedriver` directory.

## Features

- WhatsApp Web integration
- QR code generation for WhatsApp Web authentication
- Session management
- User authentication

## Development

### Running Tests

```bash
python -m pytest tests/
```

### Building Frontend Assets

```bash
npm install
npm run build
```