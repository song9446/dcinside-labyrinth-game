import logging
import socket
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

from scapy.all import *

payload='GET / HTTP/1.0\n\n'

spoof_ip = "10.20.21.249"
spoof_ip = socket.gethostbyname("unist.cc")
print(spoof_ip)
target_ip = IP(src=spoof_ip, dst=socket.gethostbyname("google.com"))
target_port = 80

port = RandNum(1024, 65535)
SYN=target_ip/TCP(sport=port, dport=target_port, flags="S", seq=0)
print("sending SYN packet")
SYNACK=sr1(SYN)

exit(1)
ACK=target_ip/TCP(sport=SYNACK.dport, dport=target_port, flags="A", seq=SYNACK.ack, ack=SYNACK.seq + 1)/payload

print("sending ACK-GET packet")
reply,error=sr(ACK)

print(reply.show())

def parse(pkt):
    if pkt.haslayer(TCP) and pkt.haslayer(Raw):
        print(pkt.getlayer(Raw).load)

parse(reply[0][0])
parse(reply[0][1])

