/**
 * WhatsApp UI JavaScript
 * Handles all WhatsApp UI interactions and SweetAlert2 integrations
 */

// Initialize WhatsApp UI when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initWhatsAppUI();
});

/**
 * Initialize WhatsApp UI components
 */
function initWhatsAppUI() {
    // Initialize SweetAlert2 theme to match the current site theme
    const currentTheme = localStorage.getItem('theme') || 'default';
    const isDarkTheme = document.body.classList.contains('dark-mode');
    
    // Set SweetAlert2 theme based on current site theme
    Swal.fire({
        title: 'Loading...',
        text: 'Please wait while we initialize the WhatsApp interface',
        timer: 500,
        timerProgressBar: true,
        didOpen: () => {
            Swal.showLoading();
        },
        willClose: () => {
            console.log('WhatsApp UI initialized');
        },
        showConfirmButton: false,
        theme: isDarkTheme ? 'dark' : 'light'
    });
    
    // Initialize event listeners
    initEventListeners();
}

/**
 * Initialize event listeners for WhatsApp UI
 */
function initEventListeners() {
    // Generate QR Code button
    // Note: This event listener is now handled in the index.html file
    // to use Flask's url_for function for more reliable routing
    const generateQrBtn = document.getElementById('generate-qr-btn');
    if (generateQrBtn && !generateQrBtn.hasAttribute('data-event-attached')) {
        console.log('WhatsApp JS: Attaching event to generate-qr-btn');
    }
    
    // Connect Device button
    const connectDeviceBtn = document.getElementById('connect-device-btn');
    if (connectDeviceBtn) {
        connectDeviceBtn.addEventListener('click', showConnectDeviceModal);
    }
    
    // Refresh Session buttons
    document.querySelectorAll('.refresh-session-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const sessionId = this.getAttribute('data-session-id');
            refreshSession(sessionId);
        });
    });
    
    // Disconnect Session buttons
    document.querySelectorAll('.disconnect-session-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const sessionId = this.getAttribute('data-session-id');
            const deviceName = this.getAttribute('data-device-name');
            disconnectSession(sessionId, deviceName);
        });
    });
    
    // Download QR Code buttons
    document.querySelectorAll('.download-qr-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const sessionId = this.getAttribute('data-session-id');
            downloadQrCode(sessionId);
        });
    });
}

/**
 * Show Generate QR Code modal using SweetAlert2
 */
function showGenerateQrModal() {
    Swal.fire({
        title: 'Generate QR Code',
        html: `
            <form id="generate-qr-form" class="mt-3">
                <div class="mb-3">
                    <label for="device-name" class="form-label">Device Name</label>
                    <input type="text" class="form-control" id="device-name" name="device_name" required 
                           placeholder="e.g. My Phone, Office WhatsApp">
                    <div class="form-text">Enter a name to identify this WhatsApp session.</div>
                </div>
            </form>
        `,
        showCancelButton: true,
        confirmButtonText: 'Generate',
        cancelButtonText: 'Cancel',
        focusConfirm: false,
        preConfirm: () => {
            const deviceName = document.getElementById('device-name').value;
            if (!deviceName) {
                Swal.showValidationMessage('Device name is required');
                return false;
            }
            return { deviceName };
        }
    }).then((result) => {
        if (result.isConfirmed) {
            generateQrCode(result.value.deviceName);
        }
    });
}

/**
 * Generate QR Code with the given device name
 * @param {string} deviceName - Name of the device
 */
function generateQrCode(deviceName) {
    // Show loading state
    Swal.fire({
        title: 'Generating QR Code',
        text: 'Please wait while we generate your QR code...',
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });
    
    // Send request to generate QR code
    fetch('/whatsapp/generate-qr-code', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({ device_name: deviceName })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Close loading dialog
            Swal.close();
            
            // Display QR code
            displayQrCode(data.qr_code, data.session_id);
        } else {
            // Show error
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: data.error || 'Failed to generate QR code. Please try again.'
            });
        }
    })
    .catch(error => {
        console.error('Error generating QR code:', error);
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'An unexpected error occurred. Please try again.'
        });
    });
}

/**
 * Display QR Code in a modal
 * @param {string} qrCode - QR code data URL or text
 * @param {string} sessionId - Session ID
 */
function displayQrCode(qrCode, sessionId) {
    // Create QR code container
    const qrContainer = document.createElement('div');
    qrContainer.className = 'qr-code-container mt-3';
    
    // Create QR code image if it's a data URL
    if (qrCode.startsWith('data:image')) {
        const qrImage = document.createElement('img');
        qrImage.src = qrCode;
        qrImage.className = 'qr-code-image';
        qrImage.alt = 'WhatsApp QR Code';
        qrContainer.appendChild(qrImage);
    } else {
        // If it's text, create a div with the text
        const qrText = document.createElement('div');
        qrText.textContent = qrCode;
        qrText.className = 'qr-code-text p-3 bg-light';
        qrContainer.appendChild(qrText);
    }
    
    // Add timer overlay
    const timerOverlay = document.createElement('div');
    timerOverlay.className = 'qr-code-timer';
    timerOverlay.textContent = '120';
    qrContainer.appendChild(timerOverlay);
    
    // Add action buttons
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'qr-code-actions';
    
    // Download button
    const downloadBtn = document.createElement('button');
    downloadBtn.innerHTML = '<i class="align-middle" data-feather="download"></i> Download';
    downloadBtn.onclick = function() { downloadQrCode(sessionId); };
    actionsDiv.appendChild(downloadBtn);
    
    // Open in new tab button
    const openBtn = document.createElement('button');
    openBtn.innerHTML = '<i class="align-middle" data-feather="external-link"></i> Open';
    openBtn.onclick = function() { window.open(`/whatsapp/display-qr-code/${sessionId}`, '_blank'); };
    actionsDiv.appendChild(openBtn);
    
    // Refresh button
    const refreshBtn = document.createElement('button');
    refreshBtn.innerHTML = '<i class="align-middle" data-feather="refresh-cw"></i> Refresh';
    refreshBtn.id = 'refresh-qr-btn';
    refreshBtn.onclick = function() { refreshQrCode(sessionId); };
    actionsDiv.appendChild(refreshBtn);
    
    qrContainer.appendChild(actionsDiv);
    
    // Show QR code in SweetAlert2
    Swal.fire({
        title: 'Scan this QR Code',
        html: `
            <div class="text-center mb-3">
                <p>Open WhatsApp on your phone, tap <strong>Menu</strong> or <strong>Settings</strong> and select <strong>Linked Devices</strong>.</p>
                <p>Point your phone to this screen to capture the QR code.</p>
            </div>
            ${qrContainer.outerHTML}
            <div class="mt-3" id="connection-status">Waiting for connection...</div>
        `,
        showConfirmButton: false,
        showCancelButton: true,
        cancelButtonText: 'Close',
        allowOutsideClick: false,
        didOpen: () => {
            // Initialize feather icons
            if (typeof feather !== 'undefined') {
                feather.replace();
            }
            
            // Start timer
            startQrCodeTimer();
            
            // Start checking connection status
            checkConnectionStatus(sessionId);
        },
        willClose: () => {
            // Clear intervals when modal is closed
            clearInterval(window.qrCodeTimerInterval);
            clearInterval(window.connectionCheckInterval);
        }
    });
}

/**
 * Start QR code timer countdown
 */
function startQrCodeTimer() {
    const timerElement = document.querySelector('.qr-code-timer');
    if (!timerElement) return;
    
    let timeLeft = 120; // 2 minutes
    
    // Clear any existing interval
    if (window.qrCodeTimerInterval) {
        clearInterval(window.qrCodeTimerInterval);
    }
    
    // Update timer every second
    window.qrCodeTimerInterval = setInterval(() => {
        timeLeft--;
        timerElement.textContent = timeLeft;
        
        // Change color when time is running out
        if (timeLeft <= 30) {
            timerElement.classList.add('expiring');
        }
        
        // When timer reaches zero
        if (timeLeft <= 0) {
            clearInterval(window.qrCodeTimerInterval);
            
            // Add expired overlay
            const qrContainer = document.querySelector('.qr-code-container');
            if (qrContainer) {
                const expiredOverlay = document.createElement('div');
                expiredOverlay.className = 'qr-code-overlay';
                expiredOverlay.innerHTML = `
                    <div class="mb-2"><i data-feather="clock" style="width: 48px; height: 48px;"></i></div>
                    <div class="mb-3">QR Code Expired</div>
                    <button class="btn btn-light btn-sm" id="refresh-expired-qr">Refresh QR Code</button>
                `;
                qrContainer.appendChild(expiredOverlay);
                
                // Initialize feather icons
                if (typeof feather !== 'undefined') {
                    feather.replace();
                }
                
                // Add event listener to refresh button
                document.getElementById('refresh-expired-qr').addEventListener('click', function() {
                    const sessionId = new URLSearchParams(window.location.search).get('session_id');
                    refreshQrCode(sessionId);
                });
            }
        }
    }, 1000);
}

/**
 * Check connection status for a session
 * @param {string} sessionId - Session ID
 */
function checkConnectionStatus(sessionId) {
    // Clear any existing interval
    if (window.connectionCheckInterval) {
        clearInterval(window.connectionCheckInterval);
    }
    
    const statusElement = document.getElementById('connection-status');
    
    // Check status every 3 seconds
    window.connectionCheckInterval = setInterval(() => {
        fetch(`/whatsapp/check-connection-status/${sessionId}`, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (statusElement) {
                statusElement.textContent = `Status: ${data.status}`;
            }
            
            // If connected, show success message
            if (data.status === 'connected') {
                clearInterval(window.connectionCheckInterval);
                clearInterval(window.qrCodeTimerInterval);
                
                // Add success overlay
                const qrContainer = document.querySelector('.qr-code-container');
                if (qrContainer) {
                    const successOverlay = document.createElement('div');
                    successOverlay.className = 'qr-code-overlay';
                    successOverlay.style.backgroundColor = 'rgba(40, 167, 69, 0.8)';
                    successOverlay.innerHTML = `
                        <div class="mb-2"><i data-feather="check-circle" style="width: 48px; height: 48px;"></i></div>
                        <div class="mb-3">Successfully Connected!</div>
                    `;
                    qrContainer.appendChild(successOverlay);
                    
                    // Initialize feather icons
                    if (typeof feather !== 'undefined') {
                        feather.replace();
                    }
                }
                
                if (statusElement) {
                    statusElement.innerHTML = `
                        <div class="alert alert-success mt-3">
                            <i class="align-middle" data-feather="check-circle"></i>
                            <strong>Connected!</strong> WhatsApp is now connected.
                            <div class="mt-2">
                                <a href="/whatsapp" class="btn btn-sm btn-success">Go to WhatsApp Dashboard</a>
                            </div>
                        </div>
                    `;
                    
                    // Initialize feather icons
                    if (typeof feather !== 'undefined') {
                        feather.replace();
                    }
                }
            }
            
            // If there's an error, show error message
            if (data.error) {
                clearInterval(window.connectionCheckInterval);
                clearInterval(window.qrCodeTimerInterval);
                
                if (statusElement) {
                    statusElement.innerHTML = `
                        <div class="alert alert-danger mt-3">
                            <i class="align-middle" data-feather="alert-circle"></i>
                            <strong>Error:</strong> ${data.error}
                            <div class="mt-2">
                                <button class="btn btn-sm btn-danger" id="try-again-btn">Try Again</button>
                            </div>
                        </div>
                    `;
                    
                    // Initialize feather icons
                    if (typeof feather !== 'undefined') {
                        feather.replace();
                    }
                    
                    // Add event listener to try again button
                    document.getElementById('try-again-btn').addEventListener('click', function() {
                        refreshQrCode(sessionId);
                    });
                }
            }
        })
        .catch(error => {
            console.error('Error checking connection status:', error);
        });
    }, 3000);
}

/**
 * Refresh QR code for a session
 * @param {string} sessionId - Session ID
 */
function refreshQrCode(sessionId) {
    // Disable refresh button
    const refreshBtn = document.getElementById('refresh-qr-btn');
    if (refreshBtn) {
        refreshBtn.disabled = true;
        refreshBtn.innerHTML = '<span class="loading-spinner"></span> Refreshing...';
    }
    
    // Show loading overlay on QR code
    const qrContainer = document.querySelector('.qr-code-container');
    if (qrContainer) {
        const loadingOverlay = document.createElement('div');
        loadingOverlay.className = 'qr-code-overlay';
        loadingOverlay.innerHTML = `
            <div class="mb-2"><span class="loading-spinner"></span></div>
            <div>Refreshing QR Code...</div>
        `;
        qrContainer.appendChild(loadingOverlay);
    }
    
    // Send request to refresh QR code
    fetch(`/whatsapp/refresh-qr-code/${sessionId}`, {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        // Remove loading overlay
        const overlay = document.querySelector('.qr-code-overlay');
        if (overlay) {
            overlay.remove();
        }
        
        // Enable refresh button
        if (refreshBtn) {
            refreshBtn.disabled = false;
            refreshBtn.innerHTML = '<i class="align-middle" data-feather="refresh-cw"></i> Refresh';
            // Initialize feather icons
            if (typeof feather !== 'undefined') {
                feather.replace();
            }
        }
        
        if (data.success) {
            // Update QR code image
            const qrImage = document.querySelector('.qr-code-image');
            if (qrImage && data.qr_code) {
                qrImage.src = data.qr_code;
            }
            
            // Reset timer
            const timerElement = document.querySelector('.qr-code-timer');
            if (timerElement) {
                timerElement.textContent = '120';
                timerElement.classList.remove('expiring');
            }
            
            // Restart timer
            startQrCodeTimer();
            
            // Restart connection status check
            checkConnectionStatus(sessionId);
        } else {
            // Show error
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: data.error || 'Failed to refresh QR code. Please try again.'
            });
        }
    })
    .catch(error => {
        console.error('Error refreshing QR code:', error);
        
        // Enable refresh button
        if (refreshBtn) {
            refreshBtn.disabled = false;
            refreshBtn.innerHTML = '<i class="align-middle" data-feather="refresh-cw"></i> Refresh';
            // Initialize feather icons
            if (typeof feather !== 'undefined') {
                feather.replace();
            }
        }
        
        // Show error
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'An unexpected error occurred. Please try again.'
        });
    });
}

/**
 * Download QR code for a session
 * @param {string} sessionId - Session ID
 */
function downloadQrCode(sessionId) {
    window.location.href = `/whatsapp/download-qr-code/${sessionId}`;
}

/**
 * Show Connect Device modal using SweetAlert2
 */
function showConnectDeviceModal() {
    // Fetch available sessions
    fetch('/api/sessions/whatsapp', {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.sessions && data.sessions.length > 0) {
            // Create session options
            const sessionOptions = data.sessions.map(session => {
                return `<option value="${session.id}">${session.name} (${session.phone || 'No phone'})</option>`;
            }).join('');
            
            // Show connect device modal
            Swal.fire({
                title: 'Connect Device',
                html: `
                    <form id="connect-device-form" class="mt-3">
                        <div class="mb-3">
                            <label for="device-name" class="form-label">Device Name</label>
                            <input type="text" class="form-control" id="device-name" name="device_name" required 
                                   placeholder="e.g. My Phone, Office WhatsApp">
                            <div class="form-text">Enter a name to identify this WhatsApp session.</div>
                        </div>
                        <div class="mb-3">
                            <label for="session" class="form-label">Session</label>
                            <select class="form-select" id="session" name="session_id" required>
                                <option value="" selected disabled>Select a session</option>
                                ${sessionOptions}
                            </select>
                            <div class="form-text">Select an existing WhatsApp session to connect to.</div>
                        </div>
                    </form>
                `,
                showCancelButton: true,
                confirmButtonText: 'Connect',
                cancelButtonText: 'Cancel',
                focusConfirm: false,
                preConfirm: () => {
                    const deviceName = document.getElementById('device-name').value;
                    const sessionId = document.getElementById('session').value;
                    
                    if (!deviceName) {
                        Swal.showValidationMessage('Device name is required');
                        return false;
                    }
                    
                    if (!sessionId) {
                        Swal.showValidationMessage('Session is required');
                        return false;
                    }
                    
                    return { deviceName, sessionId };
                }
            }).then((result) => {
                if (result.isConfirmed) {
                    connectDevice(result.value.deviceName, result.value.sessionId);
                }
            });
        } else {
            // No sessions available
            Swal.fire({
                icon: 'info',
                title: 'No Sessions Available',
                html: `
                    <p>No WhatsApp sessions are available for connection.</p>
                    <p>Please generate a QR code first to create a new session.</p>
                `,
                confirmButtonText: 'Generate QR Code',
                showCancelButton: true,
                cancelButtonText: 'Cancel'
            }).then((result) => {
                if (result.isConfirmed) {
                    showGenerateQrModal();
                }
            });
        }
    })
    .catch(error => {
        console.error('Error fetching sessions:', error);
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Failed to fetch available sessions. Please try again.'
        });
    });
}

/**
 * Connect a device to a session
 * @param {string} deviceName - Name of the device
 * @param {string} sessionId - Session ID
 */
function connectDevice(deviceName, sessionId) {
    // Show loading state
    Swal.fire({
        title: 'Connecting Device',
        text: 'Please wait while we connect your device...',
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });
    
    // Send request to connect device
    fetch('/whatsapp/connect-device', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({
            device_name: deviceName,
            session_id: sessionId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show success message
            Swal.fire({
                icon: 'success',
                title: 'Device Connected',
                text: 'Your device has been successfully connected to WhatsApp.',
                confirmButtonText: 'Go to WhatsApp Dashboard'
            }).then(() => {
                window.location.href = '/whatsapp';
            });
        } else {
            // Show error
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: data.error || 'Failed to connect device. Please try again.'
            });
        }
    })
    .catch(error => {
        console.error('Error connecting device:', error);
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'An unexpected error occurred. Please try again.'
        });
    });
}

/**
 * Refresh a WhatsApp session
 * @param {string} sessionId - Session ID
 */
function refreshSession(sessionId) {
    Swal.fire({
        title: 'Refresh Session',
        text: 'Are you sure you want to refresh this WhatsApp session?',
        icon: 'question',
        showCancelButton: true,
        confirmButtonText: 'Yes, refresh it',
        cancelButtonText: 'Cancel'
    }).then((result) => {
        if (result.isConfirmed) {
            // Show loading state
            Swal.fire({
                title: 'Refreshing Session',
                text: 'Please wait while we refresh your WhatsApp session...',
                allowOutsideClick: false,
                didOpen: () => {
                    Swal.showLoading();
                }
            });
            
            // Send request to refresh session
            fetch(`/whatsapp/refresh_session/${sessionId}`, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Show success message
                    Swal.fire({
                        icon: 'success',
                        title: 'Session Refreshed',
                        text: 'Your WhatsApp session has been successfully refreshed.',
                        confirmButtonText: 'OK'
                    }).then(() => {
                        window.location.reload();
                    });
                } else {
                    // Show error
                    Swal.fire({
                        icon: 'error',
                        title: 'Error',
                        text: data.error || 'Failed to refresh session. Please try again.'
                    });
                }
            })
            .catch(error => {
                console.error('Error refreshing session:', error);
                Swal.fire({
                    icon: 'error',
                    title: 'Error',
                    text: 'An unexpected error occurred. Please try again.'
                });
            });
        }
    });
}

/**
 * Disconnect a WhatsApp session
 * @param {string} sessionId - Session ID
 * @param {string} deviceName - Name of the device
 */
function disconnectSession(sessionId, deviceName) {
    Swal.fire({
        title: 'Disconnect Session',
        text: `Are you sure you want to disconnect the WhatsApp session "${deviceName}"?`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: 'Yes, disconnect it',
        cancelButtonText: 'Cancel',
        confirmButtonColor: '#dc3545'
    }).then((result) => {
        if (result.isConfirmed) {
            // Show loading state
            Swal.fire({
                title: 'Disconnecting Session',
                text: 'Please wait while we disconnect your WhatsApp session...',
                allowOutsideClick: false,
                didOpen: () => {
                    Swal.showLoading();
                }
            });
            
            // Send request to disconnect session
            fetch(`/whatsapp/disconnect-session/${sessionId}`, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Show success message
                    Swal.fire({
                        icon: 'success',
                        title: 'Session Disconnected',
                        text: 'Your WhatsApp session has been successfully disconnected.',
                        confirmButtonText: 'OK'
                    }).then(() => {
                        window.location.reload();
                    });
                } else {
                    // Show error
                    Swal.fire({
                        icon: 'error',
                        title: 'Error',
                        text: data.error || 'Failed to disconnect session. Please try again.'
                    });
                }
            })
            .catch(error => {
                console.error('Error disconnecting session:', error);
                Swal.fire({
                    icon: 'error',
                    title: 'Error',
                    text: 'An unexpected error occurred. Please try again.'
                });
            });
        }
    });
}

/**
 * Toggle auto-reply status
 * @param {string} replyId - Auto-reply ID
 * @param {number} currentStatus - Current status (0 or 1)
 */
function toggleAutoReplyStatus(replyId, currentStatus) {
    const newStatus = currentStatus === 1 ? 0 : 1;
    const statusText = newStatus === 1 ? 'activate' : 'deactivate';
    
    Swal.fire({
        title: `${newStatus === 1 ? 'Activate' : 'Deactivate'} Auto-Reply`,
        text: `Are you sure you want to ${statusText} this auto-reply?`,
        icon: 'question',
        showCancelButton: true,
        confirmButtonText: `Yes, ${statusText} it`,
        cancelButtonText: 'Cancel'
    }).then((result) => {
        if (result.isConfirmed) {
            // Send request to toggle status
            fetch(`/whatsapp/toggle-auto-reply-status/${replyId}/${newStatus}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Show success message
                    Swal.fire({
                        icon: 'success',
                        title: 'Status Updated',
                        text: `Auto-reply has been ${newStatus === 1 ? 'activated' : 'deactivated'}.`,
                        confirmButtonText: 'OK'
                    }).then(() => {
                        window.location.reload();
                    });
                } else {
                    // Show error
                    Swal.fire({
                        icon: 'error',
                        title: 'Error',
                        text: data.error || 'Failed to update status. Please try again.'
                    });
                }
            })
            .catch(error => {
                console.error('Error toggling status:', error);
                Swal.fire({
                    icon: 'error',
                    title: 'Error',
                    text: 'An unexpected error occurred. Please try again.'
                });
            });
        }
    });
}