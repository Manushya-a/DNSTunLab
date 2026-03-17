import os
import platform
import subprocess
import base64

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


# Example usage
if __name__ == "__main__":
    print(get_system_snapshot_string())
    print(get_fs_inventory_raw_string(os.path.expanduser("~"), target_depth=3))
    print(encode_to_base32(get_system_snapshot_string()))