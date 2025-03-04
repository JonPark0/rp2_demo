# Pi Pico W WiFi Manager

This project turns your Raspberry Pi Pico W into a WiFi access point with a captive portal that allows you to:

1. Host a WiFi access point that automatically opens a web page when someone connects
2. Scan for available WiFi networks in the area
3. Connect to a selected WiFi network (with password handling for secured networks)
4. Provide reconnection information when the Pico W connects to a network
5. Display connection status, current time (from NTP), and allow disconnection

## Files in the Project

- `boot.py` - Runs on boot-up, performs initial setup
- `main.py` - Main program with WiFi and web server functionality
- `captive_portal.py` - Implements the DNS redirect functionality for the captive portal
- `index.html` - The web interface
- `style.css` - Styling for the web interface
- `script.js` - JavaScript for the web interface functionality

## Setup Instructions

1. Install MicroPython on your Raspberry Pi Pico W if you haven't already
   - Download the latest MicroPython .uf2 file for the Pico W from [micropython.org](https://micropython.org/download/rp2-pico-w/)
   - Connect your Pico W while holding the BOOTSEL button
   - Drag and drop the .uf2 file to the RPI-RP2 drive that appears

2. Copy all project files to your Pico W:
   - You can use Thonny IDE, rshell, ampy, or another tool to transfer files
   - Transfer all the files in this project to the root directory of your Pico W

3. Reset your Pico W to run the program

## Usage

1. **Initial Connection**
   - Your Pico W will create a WiFi access point named `PiPicoW` with password `picopico`
   - Connect to this network from your device
   - A captive portal should automatically open (or navigate to http://192.168.4.1)

2. **Scanning Networks**
   - The web interface will automatically scan for available WiFi networks
   - You can click "Refresh Networks" to scan again

3. **Connecting to a WiFi Network**
   - Select a network from the dropdown list
   - Click "Connect"
   - If the network is secured, enter the password in the popup

4. **After Connection**
   - Once connected, you'll be disconnected from the Pico W's access point
   - Connect back to your normal WiFi network
   - Access the Pico W at the IP address shown in the connection message

5. **Connected Mode**
   - In connected mode, you'll see:
     - Connection status
     - Connected network name
     - Device IP address
     - Current NTP time
   - You can click "Disconnect & Restart AP" to return to access point mode

## Customization

You can customize several aspects of this project:

- Change the access point name and password in `main.py` (AP_SSID and AP_PASSWORD variables)
- Modify the web interface design in `index.html` and `style.css`
- Add additional features by extending the API endpoints in `main.py`

## Troubleshooting

- If the web page doesn't automatically open, try navigating to http://192.168.4.1
- If connecting to a WiFi network fails, verify the password and try again
- If the Pico W becomes inaccessible after connecting to a network, reset it by unplugging and plugging it back in

## Technical Details

- The captive portal uses a simple DNS server that redirects all domain requests to the Pico W's IP
- The web interface communicates with the Pico W through a simple JSON API
- In station mode, the device uses NTP to get the current time
