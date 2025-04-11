import io
import json
import time
import socket
from pathlib import Path
import argparse

import requests
import paho.mqtt.client as mqtt
from scapy.all import sniff, PcapWriter

# buf = io.BytesIO()
# PcapWriter(buf).write(packets)
#headers={'Content-Type': 'application/vnd.tcpdump.pcap'}
class PacketSubmitter:
    def __init__(self, hostname):
        self.hostname = hostname
        self.buffer = {}  # interface -> packet list
        self.buffer_size = 10  # packets per interface before submit
        self.ttb = .5 #time to buffer
        
    def add_packet(self, interface, packet):
        if interface not in self.buffer:
            self.buffer[interface] = []
        self.buffer[interface].append(packet)
        
        if len(self.buffer[interface]) >= self.buffer_size:
            self.flush(interface)
        elif len(self.buffer[interface]) and time.time() > self.buffer[interface][0]["time"] + self.ttb:
            self.flush(interface)
    
    def flush(self, interface):
        if interface not in self.buffer or not self.buffer[interface]:
            return
        self.submit(interface, self.buffer[interface])
        self.buffer[interface] = []

    def submit(self, interface, packets):
        # Override in subclasses
        raise(NotImplementedError)

class MQTTSubmitter(PacketSubmitter):
    def __init__(self, hostname, mqtt_host, mqtt_port=1883):
        super().__init__(hostname)
        self.client = mqtt.Client()
        self.client.connect(mqtt_host, mqtt_port)
        
    def submit(self, interface, packets):
        topic = f"pcap/{self.hostname}/{interface}"
        self.client.publish(topic, json.dumps(packets))

class HTTPSubmitter(PacketSubmitter):
    def __init__(self, hostname, url):
        super().__init__(hostname)
        self.url = url
        
    def submit(self, interface, packets):
        print(len(packets))
        requests.put(
            f"{self.url}/{self.hostname}/{interface}",
            data=json.dumps(packets),
            headers={'Content-Type': 'application/json'}
        )

def packet_callback(submitter):
    def callback(packet):
        # Get interface from packet
        interface = packet.sniffed_on
        capture_time = packet.time
        packet.summary()
        top = packet.layers()[0].__name__
        pkt = {"interface":interface,"time":capture_time, "packet":packet.original.hex(), "top":top}
        submitter.add_packet(interface, pkt)
    return callback

def main():
    parser = argparse.ArgumentParser(description='Capture and submit packets')
    parser.add_argument('-i', '--interface', action='append', help='Interface to capture on')
    parser.add_argument('--me', help='myhostname')
    
    # Submitter options (mutually exclusive)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--mqtt', help='MQTT broker hostname')
    group.add_argument('--http', help='HTTP submission URL')
    
    # Optional ports
    parser.add_argument('--mqtt-port', type=int, default=1883)
    
    args = parser.parse_args()
    
    # Get hostname
    if args.me:
        hostname = args.me
    else:
        hostname = socket.gethostname()
    
    # Create appropriate submitter
    if args.mqtt:
        submitter = MQTTSubmitter(hostname, args.mqtt, args.mqtt_port)
    elif args.http:
        submitter = HTTPSubmitter(hostname, args.http)
    
    # Handle interface selection
    interfaces = args.interface
    if 'any' in interfaces:
        interfaces = None  # Scapy will capture on all interfaces
    
    from scapy.layers.inet import TCP, UDP, IP
    try:
        sniff(
            iface=interfaces,
            prn=packet_callback(submitter),
            #filter="port not 8000 and port not 1883"
            lfilter=lambda p: not (
                p.haslayer(TCP) and 
                (p[TCP].dport == 8000 or p[TCP].sport == 8000)
                )
            #store=0  # Don't store packets in memory
        )
    except KeyboardInterrupt:
        # Flush any remaining packets
        for interface in submitter.buffer:
            submitter.flush(interface)
        print("\nCapture stopped")

if __name__ == "__main__":
    main()
