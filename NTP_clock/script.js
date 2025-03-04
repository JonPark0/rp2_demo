document.addEventListener('DOMContentLoaded', function() {
    // Constants
    const RECONNECT_INFO = "You've been disconnected from the Pi Pico W access point. To access the device on your network, please visit: http://{IP_ADDRESS}";
    
    // DOM Elements
    const apModeEl = document.getElementById('ap-mode');
    const staModeEl = document.getElementById('sta-mode');
    const networkListEl = document.getElementById('network-list');
    const scanBtnEl = document.getElementById('scan-btn');
    const connectBtnEl = document.getElementById('connect-btn');
    const disconnectBtnEl = document.getElementById('disconnect-btn');
    const statusMessageEl = document.getElementById('status-message');
    const passwordModalEl = document.getElementById('password-modal');
    const selectedSsidEl = document.getElementById('selected-ssid');
    const passwordInputEl = document.getElementById('wifi-password');
    const showPasswordBtnEl = document.getElementById('show-password');
    const submitBtnEl = document.getElementById('submit-btn');
    const cancelBtnEl = document.getElementById('cancel-btn');
    const closeBtnEl = document.querySelector('.close-btn');
    const scannerEl = document.getElementById('scan-spinner');
    const connectedSsidEl = document.getElementById('connected-ssid');
    const deviceIpEl = document.getElementById('device-ip');
    const currentTimeEl = document.getElementById('current-time');
    
    // State variables
    let selectedNetwork = null;
    let isSecuredNetwork = false;
    let networks = [];
    
    // Initialize
    init();
    
    function init() {
        // Set up event listeners
        setupEventListeners();
        
        // Check current status
        checkStatus();
        
        // Initial network scan if in AP mode
        setTimeout(() => {
            if (apModeEl.style.display !== 'none') {
                scanNetworks();
            }
        }, 500);
    }
    
    function setupEventListeners() {
        // Scan button
        scanBtnEl.addEventListener('click', scanNetworks);
        
        // Network selection change
        networkListEl.addEventListener('change', function() {
            const selectedValue = this.value;
            selectedNetwork = networks.find(net => net.ssid === selectedValue);
            
            if (selectedNetwork) {
                connectBtnEl.disabled = false;
                isSecuredNetwork = selectedNetwork.security === 'Secured';
            } else {
                connectBtnEl.disabled = true;
            }
        });
        
        // Connect button
        connectBtnEl.addEventListener('click', function() {
            if (!selectedNetwork) return;
            
            if (isSecuredNetwork) {
                // Show password modal for secured networks
                selectedSsidEl.textContent = selectedNetwork.ssid;
                passwordInputEl.value = '';
                passwordModalEl.style.display = 'block';
            } else {
                // Connect directly to open networks
                connectToNetwork(selectedNetwork.ssid);
            }
        });
        
        // Password modal events
        submitBtnEl.addEventListener('click', function() {
            const password = passwordInputEl.value.trim();
            if (password === '') {
                alert('Please enter a password');
                return;
            }
            
            passwordModalEl.style.display = 'none';
            connectToNetwork(selectedNetwork.ssid, password);
        });
        
        cancelBtnEl.addEventListener('click', function() {
            passwordModalEl.style.display = 'none';
        });
        
        closeBtnEl.addEventListener('click', function() {
            passwordModalEl.style.display = 'none';
        });
        
        // Close modal if clicking outside
        window.addEventListener('click', function(event) {
            if (event.target === passwordModalEl) {
                passwordModalEl.style.display = 'none';
            }
        });
        
        // Show/hide password toggle
        showPasswordBtnEl.addEventListener('click', function() {
            if (passwordInputEl.type === 'password') {
                passwordInputEl.type = 'text';
                this.textContent = 'Hide';
            } else {
                passwordInputEl.type = 'password';
                this.textContent = 'Show';
            }
        });
        
        // Disconnect button
        disconnectBtnEl.addEventListener('click', disconnectAndRestart);
        
        // Enter key in password field
        passwordInputEl.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                submitBtnEl.click();
            }
        });
    }
    
    // Check current connection status
    function checkStatus() {
        showStatusMessage('Checking connection status...', 'info');
        
        fetch('/api/status')
            .then(response => response.json())
            .then(data => {
                if (data.mode === 'STA' && data.connected) {
                    // We're in station mode and connected
                    showStaMode(data);
                } else {
                    // We're in AP mode or not connected
                    showApMode();
                }
                clearStatusMessage();
            })
            .catch(error => {
                console.error('Status check failed:', error);
                showApMode();
                clearStatusMessage();
            });
    }
    
    // Poll status when in STA mode
    function startStatusPolling() {
        // Update status every 10 seconds
        const statusInterval = setInterval(() => {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    if (data.mode === 'STA' && data.connected) {
                        // Update the time
                        if (data.time) {
                            currentTimeEl.textContent = data.time;
                        }
                    } else {
                        // We've disconnected, stop polling
                        clearInterval(statusInterval);
                        showApMode();
                    }
                })
                .catch(error => {
                    console.error('Status polling error:', error);
                    // If we can't reach the device, assume disconnected
                    clearInterval(statusInterval);
                    showApMode();
                });
        }, 10000);
    }
    
    // Scan for available networks
    function scanNetworks() {
        // Clear the dropdown
        while (networkListEl.options.length > 1) {
            networkListEl.remove(1);
        }
        
        // Disable connect button until a network is selected
        connectBtnEl.disabled = true;
        
        // Show spinner and disable scan button
        scannerEl.style.display = 'block';
        scanBtnEl.disabled = true;
        
        // Show status message
        showStatusMessage('Scanning for networks...', 'info');
        
        // Fetch available networks
        fetch('/api/scan')
            .then(response => response.json())
            .then(data => {
                networks = data.networks || [];
                
                // Sort networks by signal strength
                networks.sort((a, b) => b.signal - a.signal);
                
                // Add networks to dropdown
                networks.forEach(network => {
                    const option = document.createElement('option');
                    option.value = network.ssid;
                    option.textContent = `${network.ssid} (${network.security}, ${network.signal}%)`;
                    networkListEl.appendChild(option);
                });
                
                // Hide spinner and enable scan button
                scannerEl.style.display = 'none';
                scanBtnEl.disabled = false;
                
                if (networks.length === 0) {
                    showStatusMessage('No networks found. Try scanning again.', 'error');
                } else {
                    clearStatusMessage();
                }
            })
            .catch(error => {
                console.error('Network scan failed:', error);
                showStatusMessage('Network scan failed. Please try again.', 'error');
                scannerEl.style.display = 'none';
                scanBtnEl.disabled = false;
            });
    }
    
    // Connect to selected network
    function connectToNetwork(ssid, password = null) {
        showStatusMessage('Connecting to network...', 'info');
        
        // Disable buttons while connecting
        connectBtnEl.disabled = true;
        scanBtnEl.disabled = true;
        
        const data = {
            ssid: ssid,
            password: password
        };
        
        fetch('/api/connect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(result => {
            if (result.status === 'connected') {
                // Connection successful
                const ipAddress = result.ip;
                const reconnectMessage = RECONNECT_INFO.replace('{IP_ADDRESS}', ipAddress);
                showStatusMessage(reconnectMessage, 'success');
                
                // Inform the user about the successful connection
                alert("Connected to " + ssid + "!\n\n" + reconnectMessage);
                
                // We might lose connection to the AP at this point
                // The user should now reconnect to their normal WiFi and access
                // the device at the new IP address
            } else {
                // Connection failed
                showStatusMessage('Connection failed: ' + (result.message || 'Unknown error'), 'error');
                connectBtnEl.disabled = false;
                scanBtnEl.disabled = false;
            }
        })
        .catch(error => {
            console.error('Connection error:', error);
            
            // This error is expected when the device switches to station mode
            // and the AP is no longer available
            const reconnectMessage = "If connection was successful, you've been disconnected from the Pi Pico W access point. Please connect to your normal WiFi and access the device using its IP address.";
            showStatusMessage(reconnectMessage, 'info');
        });
    }
    
    // Disconnect from WiFi and restart AP
    function disconnectAndRestart() {
        showStatusMessage('Disconnecting and restarting AP mode...', 'info');
        
        fetch('/api/disconnect', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'disconnected') {
                alert("Disconnected! Pi Pico W is restarting in Access Point mode. Please connect to the \"PiPicoW\" WiFi network to configure.");
            }
        })
        .catch(error => {
            console.error('Disconnect error:', error);
            // This error is expected as the device restarts and the connection is lost
        });
    }
    
    // Display functions
    function showApMode() {
        apModeEl.style.display = 'block';
        staModeEl.style.display = 'none';
    }
    
    function showStaMode(data) {
        apModeEl.style.display = 'none';
        staModeEl.style.display = 'block';
        
        // Update the connected info
        connectedSsidEl.textContent = data.ssid || '-';
        deviceIpEl.textContent = data.ip || '-';
        currentTimeEl.textContent = data.time || '-';
        
        // Start polling for updates (time, etc.)
        startStatusPolling();
    }
    
    // Status message helpers
    function showStatusMessage(message, type) {
        statusMessageEl.textContent = message;
        statusMessageEl.className = 'status-message ' + type;
        statusMessageEl.style.display = 'block';
    }
    
    function clearStatusMessage() {
        statusMessageEl.style.display = 'none';
    }
});