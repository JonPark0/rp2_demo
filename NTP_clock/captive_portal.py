import socket
import uasyncio as asyncio

# Class to implement a captive portal for automatic redirection
class CaptivePortal:
    def __init__(self, ap_if):
        self.ap_if = ap_if
        self.ip = ap_if.ifconfig()[0]
    
    async def process_dns_request(self, data, addr, sock):
        # Extract domain from DNS query (simplified)
        try:
            # DNS query format: [header (12 bytes)][question][...]
            domain = ""
            # Start after header (12 bytes)
            i = 12
            while data[i] != 0:
                length = data[i]
                i += 1
                domain += data[i:i+length].decode('utf-8') + "."
                i += length
            
            # Craft a DNS response that points to our IP
            # This is a simplified DNS response that will redirect all domains to our IP
            
            # Copy transaction ID from request
            transaction_id = data[0:2]
            
            # Create DNS response header
            flags = b'\x81\x80'  # Standard response, no error
            q_count = b'\x00\x01'  # One question
            ans_count = b'\x00\x01'  # One answer
            auth_count = b'\x00\x00'  # No authority records
            add_count = b'\x00\x00'  # No additional records
            
            header = transaction_id + flags + q_count + ans_count + auth_count + add_count
            
            # Include the original question in the response
            question = data[12:]
            # Find the end of the question section
            end_of_question = 12
            while data[end_of_question] != 0:
                end_of_question += data[end_of_question] + 1
            end_of_question += 5  # Skip the null byte and QTYPE/QCLASS
            
            # Create the answer section
            answer = (
                b'\xc0\x0c'  # Pointer to the domain name in the question
                b'\x00\x01'  # TYPE: A (Host address)
                b'\x00\x01'  # CLASS: IN (Internet)
                b'\x00\x00\x00\x3c'  # TTL: 60 seconds
                b'\x00\x04'  # RDLENGTH: 4 bytes (for IPv4)
            )
            
            # Add the IP address (convert string IP to bytes)
            ip_parts = [int(part) for part in self.ip.split('.')]
            ip_bytes = bytes(ip_parts)
            
            # Assemble the complete response
            response = header + data[12:end_of_question] + answer + ip_bytes
            
            # Send the response
            sock.sendto(response, addr)
            
        except Exception as e:
            print("DNS processing error:", e)
    
    async def start_dns_server(self):
        # Create UDP socket for DNS server (port 53)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(('0.0.0.0', 53))
        except OSError as e:
            print("DNS binding error:", e)
            return
        
        sock.setblocking(False)
        print("DNS server started on port 53")
        
        while True:
            try:
                # Wait for DNS requests
                yield asyncio.core._io_queue.queue_read(sock)
                
                data, addr = sock.recvfrom(512)  # Standard DNS message size
                
                # Process DNS request in the background
                asyncio.create_task(self.process_dns_request(data, addr, sock))
                
            except Exception as e:
                print("DNS server error:", e)
            
            # Small delay to prevent tight loops
            await asyncio.sleep(0.01)
