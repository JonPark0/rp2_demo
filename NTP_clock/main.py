import network
import socket
import time
import json
import ntptime
import random
import machine
from machine import Pin
import uasyncio as asyncio
import gc
from captive_portal import CaptivePortal

# Load HTML and JS files
def read_file(filename):
    with open(filename, 'r') as file:
        return file.read()

# AP credentials
AP_SSID = "PiPicoW"
AP_PASSWORD = "picopico"

# Setup LED
led = Pin("LED", Pin.OUT)

# Global variables
connected_ssid = None
connected_password = None
sta_if = network.WLAN(network.STA_IF)
ap_if = network.WLAN(network.AP_IF)
current_ip = None
scanning_networks = False

# Function to scan and return available networks
def scan_networks():
    global scanning_networks
    scanning_networks = True
    try:
        sta_if.active(True)
        networks = sta_if.scan()
        result = []
        # Sort networks by signal strength
        for net in sorted(networks, key=lambda x: x[3], reverse=True):
            ssid = net[0].decode('utf-8')
            # Skip empty SSIDs
            if ssid:
                security = "Open" if net[4] == 0 else "Secured"
                signal = net[3]
                result.append({"ssid": ssid, "security": security, "signal": signal})
        return result
    except Exception as e:
        print("Scan error:", e)
        return []
    finally:
        scanning_networks = False

# Connect to a specific WiFi network
def connect_to_wifi(ssid, password=None):
    global connected_ssid, connected_password, current_ip
    
    try:
        # Stop AP mode
        ap_if.active(False)
        
        # Activate station interface
        sta_if.active(True)
        
        # Store credentials
        connected_ssid = ssid
        connected_password = password
        
        # Connect to WiFi
        print(f"Connecting to {ssid}...")
        if password:
            sta_if.connect(ssid, password)
        else:
            sta_if.connect(ssid)
        
        # Wait for connection
        max_wait = 20
        while max_wait > 0:
            if sta_if.isconnected():
                current_ip = sta_if.ifconfig()[0]
                print(f"Connected! IP: {current_ip}")
                return {"status": "connected", "ip": current_ip}
            max_wait -= 1
            led.toggle()
            time.sleep(1)
            
        # If we got here, connection failed
        sta_if.active(False)
        connected_ssid = None
        connected_password = None
        return {"status": "failed", "message": "Connection timeout"}
        
    except Exception as e:
        print("Connection error:", e)
        sta_if.active(False)
        connected_ssid = None
        connected_password = None
        return {"status": "failed", "message": str(e)}

# Start in AP mode
def start_ap_mode():
    global ap_if, current_ip
    
    # Disable station mode if active
    if sta_if.active():
        sta_if.active(False)
    
    # Configure AP mode
    ap_if.active(True)
    ap_if.config(essid=AP_SSID, password=AP_PASSWORD, security=network.AUTH_WPA_WPA2_PSK)
    
    current_ip = ap_if.ifconfig()[0]
    print(f"AP mode started. SSID: {AP_SSID}, IP: {current_ip}")
    return current_ip

# Get current time from NTP server
def get_ntp_time():
    try:
        ntptime.settime()
        t = time.localtime()
        return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
            t[0], t[1], t[2], t[3], t[4], t[5]
        )
    except Exception as e:
        print("NTP error:", e)
        return "NTP time unavailable"

# Web server handler
async def handle_client(reader, writer):
    global connected_ssid, current_ip
    
    # Read request
    request_line = await reader.readline()
    request = request_line.decode().strip()
    print("Request:", request)
    
    # Read all headers
    while True:
        line = await reader.readline()
        if line == b'\r\n' or not line:
            break
    
    # Parse request
    try:
        method, path, _ = request.split()
    except Exception:
        method, path = "GET", "/"
    
    # Handle API requests
    if path == "/api/scan" and method == "GET":
        networks = scan_networks()
        response = json.dumps({"networks": networks})
        writer.write('HTTP/1.1 200 OK\r\n')
        writer.write('Content-Type: application/json\r\n')
        writer.write('Connection: close\r\n')
        writer.write(f'Content-Length: {len(response)}\r\n\r\n')
        writer.write(response)
    
    elif path == "/api/connect" and method == "POST":
        # Read the body of the POST request
        content_length = 0
        while True:
            line = await reader.readline()
            if line == b'\r\n':
                break
            parts = line.decode().strip().split(':')
            if parts[0].lower() == 'content-length':
                content_length = int(parts[1].strip())
        
        body = await reader.read(content_length)
        data = json.loads(body.decode())
        
        ssid = data.get("ssid", "")
        password = data.get("password", None)
        
        result = connect_to_wifi(ssid, password)
        response = json.dumps(result)
        
        writer.write('HTTP/1.1 200 OK\r\n')
        writer.write('Content-Type: application/json\r\n')
        writer.write('Connection: close\r\n')
        writer.write(f'Content-Length: {len(response)}\r\n\r\n')
        writer.write(response)
    
    elif path == "/api/status" and method == "GET":
        is_ap_mode = ap_if.active()
        is_sta_mode = sta_if.isconnected()
        
        status = {
            "mode": "AP" if is_ap_mode else "STA",
            "connected": is_sta_mode,
            "ssid": connected_ssid if is_sta_mode else None,
            "ip": current_ip,
            "time": get_ntp_time() if is_sta_mode else None
        }
        
        response = json.dumps(status)
        writer.write('HTTP/1.1 200 OK\r\n')
        writer.write('Content-Type: application/json\r\n')
        writer.write('Connection: close\r\n')
        writer.write(f'Content-Length: {len(response)}\r\n\r\n')
        writer.write(response)
    
    elif path == "/api/disconnect" and method == "POST":
        # Disconnect from WiFi and start AP mode
        if sta_if.active():
            sta_if.active(False)
        
        connected_ssid = None
        connected_password = None
        
        ip = start_ap_mode()
        response = json.dumps({"status": "disconnected", "ap_ip": ip})
        
        writer.write('HTTP/1.1 200 OK\r\n')
        writer.write('Content-Type: application/json\r\n')
        writer.write('Connection: close\r\n')
        writer.write(f'Content-Length: {len(response)}\r\n\r\n')
        writer.write(response)
    
    # Serve static files
    else:
        if path == "/" or path == "/index.html":
            content = read_file("index.html")
            content_type = "text/html"
        elif path == "/style.css":
            content = read_file("style.css")
            content_type = "text/css"
        elif path == "/script.js":
            content = read_file("script.js")
            content_type = "text/javascript"
        else:
            # 404 page
            content = "<html><body><h1>404 Not Found</h1></body></html>"
            writer.write('HTTP/1.1 404 Not Found\r\n')
            writer.write('Content-Type: text/html\r\n')
            writer.write('Connection: close\r\n')
            writer.write(f'Content-Length: {len(content)}\r\n\r\n')
            writer.write(content)
            await writer.drain()
            writer.close()
            return
        
        writer.write('HTTP/1.1 200 OK\r\n')
        writer.write(f'Content-Type: {content_type}\r\n')
        writer.write('Connection: close\r\n')
        writer.write(f'Content-Length: {len(content)}\r\n\r\n')
        writer.write(content)
    
    await writer.drain()
    writer.close()

# Main web server function
async def start_server():
    global current_ip
    
    print("Starting web server...")
    server = await asyncio.start_server(handle_client, current_ip, 80)
    print(f"Web server started on {current_ip}:80")
    
    while True:
        await asyncio.sleep(1)
        # Blink LED while in AP mode
        if ap_if.active():
            led.toggle()

# Main function
async def main():
    global current_ip, ap_if
    
    # Start in AP mode initially
    start_ap_mode()
    
    # Initialize captive portal to redirect all DNS requests
    portal = CaptivePortal(ap_if)
    asyncio.create_task(portal.start_dns_server())
    
    # Start the web server
    await start_server()

# Start the main application
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Program stopped by user")
except Exception as e:
    print("Unexpected error:", e)
    # Reset the device on critical error
    machine.reset()
