#!/bin/bash

# Script to install Chrome on Linux systems
# This script detects the Linux distribution and installs the appropriate Chrome package

echo "Chrome Installation Helper for Blastify"
echo "======================================"

# Check if script is run with sudo/root
if [ "$(id -u)" -ne 0 ]; then
    echo "Error: This script must be run as root or with sudo privileges."
    echo "Please run: sudo $0"
    exit 1
fi

# Detect Linux distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$ID
else
    echo "Error: Could not detect Linux distribution."
    exit 1
fi

echo "Detected Linux distribution: $DISTRO"

# Install Chrome based on distribution
case $DISTRO in
    ubuntu|debian|linuxmint|pop)
        echo "Installing Chrome for Debian/Ubuntu-based distribution..."
        apt update
        
        # Try to install Google Chrome first
        if ! apt-get install -y google-chrome-stable; then
            echo "Google Chrome package not found. Adding Google Chrome repository..."
            
            # Add Google Chrome repository
            wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add -
            echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list
            apt update
            
            # Try installing Google Chrome again
            if ! apt-get install -y google-chrome-stable; then
                echo "Failed to install Google Chrome. Trying Chromium instead..."
                apt-get install -y chromium-browser || apt-get install -y chromium
            fi
        fi
        ;;
    fedora|rhel|centos)
        echo "Installing Chrome for Fedora/RHEL-based distribution..."
        
        # Try installing Google Chrome
        if ! dnf install -y google-chrome-stable; then
            echo "Google Chrome package not found. Adding Google Chrome repository..."
            
            # Add Google Chrome repository
            dnf install -y dnf-plugins-core
            dnf config-manager --set-enabled google-chrome
            dnf install -y google-chrome-stable
            
            # If that fails, try Chromium
            if [ $? -ne 0 ]; then
                echo "Failed to install Google Chrome. Trying Chromium instead..."
                dnf install -y chromium
            fi
        fi
        ;;
    arch|manjaro)
        echo "Installing Chrome for Arch-based distribution..."
        pacman -Sy
        
        # Try installing Chromium (more common in Arch)
        if ! pacman -S --noconfirm chromium; then
            echo "Failed to install Chromium. Trying Google Chrome from AUR..."
            
            # Check if yay is installed for AUR access
            if ! command -v yay &> /dev/null; then
                echo "Installing yay AUR helper..."
                pacman -S --noconfirm git base-devel
                git clone https://aur.archlinux.org/yay.git
                cd yay
                makepkg -si --noconfirm
                cd ..
                rm -rf yay
            fi
            
            # Install Google Chrome from AUR
            yay -S --noconfirm google-chrome
        fi
        ;;
    *)
        echo "Unsupported Linux distribution: $DISTRO"
        echo "Please install Google Chrome or Chromium manually."
        exit 1
        ;;
esac

# Check if installation was successful
if command -v google-chrome &> /dev/null || command -v google-chrome-stable &> /dev/null || command -v chromium &> /dev/null || command -v chromium-browser &> /dev/null; then
    echo "\nChrome/Chromium installation successful!"
    echo "You can now run the check_chromedriver.py script again."
    exit 0
else
    echo "\nFailed to install Chrome/Chromium."
    echo "Please install it manually according to your distribution's instructions."
    exit 1
fi