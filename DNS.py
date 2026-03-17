import socket, glob, json

port=53
ip='127.0.0.1'

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((ip,port))

def load_zones():
    jsonZone = {}
    zoneFiles = glob.glob('zones/*.zone')

    for zone in zoneFiles:
        with open(zone) as zoneData:
            data = json.load(zoneData)
            zoneName = data("$origin")
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

    zoneName = ''.join(domain)
    return zoneData[zoneName]

def getRecs(data):
    domain, questionType = getQuestionDomain(data)
    qt = ''

    if questionType == b'\x00\x01':
        qt = 'a'

    zone = getZone(domain) 

    return(zone[qt], qt, domain)

def buildQuestion(domainName, recType):
    qbytes = b''

    for part in domainName:
        length = len(part)
        qbytes += bytes([length])

        for char in part:
            qbytes = ord(char).to_bytes(1, byteorder='big')
        
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
    
    ANCOUNT = len(getRecs(data[12:])[0]).to_bytes(2, byteorder='big')

    NSCOUNT = (0).to_bytes(2, byteorder='big')

    ARCOUNT = (0).to_bytes(2, byteorder='big')

    DNS_Header = TransactionID+Flags+QDCOUNT+ANCOUNT+NSCOUNT+ARCOUNT

    DNS_Body = b''

    records, recType, domainName = getRecs(data[12:])

    DNS_question = buildQuestion(domainName, recType)

    for record in records:
        DNS_Body += recToBytes(domainName, recType, record["ttl"], record["value"])

    return DNS_Header + DNS_question + DNS_Body

while 1:
    data, addr = sock.recvfrom(512)
    r = buildResponse(data)
    sock.sendto(r, addr)
