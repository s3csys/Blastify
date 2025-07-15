# zxing-cpp Installation Guide

## Overview
This document provides instructions for installing the `zxing-cpp` library, which has replaced `pyzbar` for QR code scanning in our application. The `zxing-cpp` library is a C++ port of the ZXing barcode scanning library with Python bindings, and it does not require Visual Studio build tools to install.

## Installation

### Using pip
The simplest way to install `zxing-cpp` is using pip:

```bash
pip install zxing-cpp==1.4.0
```

Or you can install all project dependencies including `zxing-cpp` by running:

```bash
pip install -r requirements.txt
```

### Benefits of zxing-cpp over pyzbar

1. **No Visual Studio build tools required**: Unlike `pyzbar`, `zxing-cpp` provides pre-built wheels for Windows that don't require Visual C++ build tools.

2. **Better maintained**: The `zxing-cpp` library is actively maintained and has better support for modern Python versions.

3. **More barcode formats**: `zxing-cpp` supports more barcode formats than `pyzbar`.

4. **Better performance**: `zxing-cpp` often has better detection performance for QR codes.

## Usage

The application has been updated to use `zxing-cpp` instead of `pyzbar`. The main difference in usage is:

```python
# Old code with pyzbar
from pyzbar.pyzbar import decode
qr_codes = decode(gray_image)

# New code with zxing-cpp
import zxingcpp
qr_codes = zxingcpp.read_barcodes(image)
```

## Troubleshooting

If you encounter any issues with `zxing-cpp`, please check the following:

1. Make sure you have the latest version of pip: `pip install --upgrade pip`
2. If you're using a virtual environment, make sure it's activated before installing.
3. If installation fails, try installing from source: `pip install zxing-cpp --no-binary zxing-cpp`

For more information, visit the [zxing-cpp GitHub repository](https://github.com/zxing-cpp/zxing-cpp).