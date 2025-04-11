import os
import io
import json
import queue
import struct
import logging
import asyncio
import tempfile
import threading
import subprocess
from pathlib import Path
from datetime import datetime
from collections import deque

from typing import Dict, List, Set

import scapy
from scapy.utils import rdpcap
from scapy.layers.l2 import Ether
from scapy.utils import PcapReader
from scapy.all import conf
from scapy.layers.l2 import Ether
from scapy.layers.inet import IP, TCP, UDP
from scapy.layers.inet6 import IPv6
from scapy.layers.dns import DNS
from scapy.layers.http import HTTP
from scapy.layers.dhcp import DHCP
from scapy.layers.snmp import SNMP
from scapy.layers.inet import IP, TCP, UDP
from scapy.layers.inet6 import IPv6
from scapy.layers.l2 import Ether
from scapy.contrib.pfcp import PFCP
from scapy.layers.radius import Radius


conf.load_layers.extend([
    'inet', 'inet6',
    'gtp', 'diameter',
    'sctp', 's1ap',
    'pfcp', 'radius',
    'http', 'tls'
])

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
captures: Dict[str, Dict[str, str]] = {}  # hostname -> {interface -> filepath}
packet_queue = asyncio.Queue()  
connected_clients: Set[WebSocket] = set()
storage_path = Path("/tmp/capture")
storage_path.mkdir(exist_ok=True)


async def process_new_capture(filepath: str):
    """Process new capture file with tshark and queue packets"""
    cmd = [
        'tshark',
        '-r', filepath,
        '-T', 'json',
        '-x'  # Include hex dump
    ]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    if process.returncode == 0:
        packets = json.loads(stdout)
        for packet in packets:
            await packet_queue.put(packet)
            # Broadcast to all connected websocket clients
            for client in connected_clients:
                try:
                    await client.send_json(packet)
                except:
                    connected_clients.remove(client)

def d2p(pkt_dict):
    assert pkt_dict['top'] == 'Ether'
    pkt = Ether(bytes.fromhex(pkt_dict["packet"]))
    # Restore metadata
    pkt.time = pkt_dict["time"]
    pkt.sniffed_on = pkt_dict["interface"]

    return pkt

def pkt2dict(pkt):
    """
    https://stackoverflow.com/a/72128891
    """
    packet_dict = {}
    for line in pkt.show2(dump=True).split('\n'):
        if '###' in line:
            if '|###' in line:
                sublayer = line.strip('|#[] ')
                packet_dict[layer][sublayer] = {}
            else:
                layer = line.strip('#[] ')
                packet_dict[layer] = {}
        elif '=' in line:
            if '|' in line and 'sublayer' in locals():
                key, val = line.strip('| ').split('=', 1)
                packet_dict[layer][sublayer][key.strip()] = val.strip('\' ')
            else:
                key, val = line.split('=', 1)
                val = val.strip('\' ')
                if(val):
                    try:
                        packet_dict[layer][key.strip()] = eval(val)
                    except:
                        packet_dict[layer][key.strip()] = val
        else:
            log.debug("pkt2dict packet not decoded: " + line)
    return packet_dict

@app.put("/api/capture/{hostname}/{interface}")
async def receive_capture(hostname: str, interface: str, request: Request):
    content_type = request.headers.get("content-type", "")

    # Initialize storage if needed
    if hostname not in captures:
        captures[hostname] = {}
    if interface not in captures[hostname]:
        captures[hostname][interface] = []

    if "application/json" in content_type:
        packets = await request.json()
        pkts = list(map(d2p, packets))
        for x in pkts:
            print(hostname, interface, x.summary())
            await packet_queue.put({
                "hostname":hostname,
                "interface":interface,
                "summary":x.summary(),
                "json":json.loads(x.json()),
                #"bytes":x.original.hex(),
                })
        captures[hostname][interface].append(pkts)

    elif "application/vnd.tcpdump.pcap" in content_type or "application/octet-stream" in content_type:
        os.makedirs(f"{storage_path}/{hostname}", exist_ok=True)

        try:
            os.remove(f"{storage_path}/{hostname}/{interface}.pcap")
        except:
            pass
        fn =  f"/tmp/capture/{hostname}/{interface}.pcap"
        with open(fn,'wb+') as fd:
            i = 0
            async for chunk in request.stream():
                fd.seek(0, io.SEEK_END) 
                fd.write(chunk) #append latest chunk to file

                fd.seek(0) 
                #yes, this will get slower and slower. 
                #I need this to work for limited-scope stuff for a demo for now
                packets = scapy.utils.PcapReader(fn).read_all() 
                for x in packets[i:]:
                    print(hostname, interface, x.summary())
                    await packet_queue.put({
                        "hostname":hostname,
                        "interface":interface,
                        "summary":x.summary(),
                        "json":json.loads(x.json()),
                        #"bytes":x.original.hex(),
                    })
                i = len(packets)
    
    else:
        return {"error": f"Unsupported content type: {content_type}"}

    return {"status": "ok"}
@app.get("/api/captures")
async def get_captures():
    """Get list of all captures"""
    return captures

@app.get("/api/packets/summary")
async def get_summary():
    """Get summary of all packets"""
    # This could be more sophisticated with actual packet analysis
    summary = {
        'captures': captures,
        'total_files': sum(len(interfaces) for interfaces in captures.values()),
        'hosts': list(captures.keys())
    }
    return summary

@app.get("/api/packets/{hostname}/{interface}")
async def get_packets(hostname: str, interface: str, limit: int = 1000):
    """Get packets from specific capture file"""
    if hostname not in captures or interface not in captures[hostname]:
        return {"error": "Capture not found"}
    
    filepath = captures[hostname][interface]
    cmd = [
        'tshark',
        '-r', filepath,
        '-T', 'json',
        '-c', str(limit)  # Limit number of packets
    ]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    if process.returncode == 0:
        return json.loads(stdout)
    else:
        return {"error": stderr.decode()}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        while True:
            # Keep connection alive and handle any client messages
            data = await websocket.receive_text()
    except:
        connected_clients.remove(websocket)

async def cleanup_old_captures():
    while True:
        # Delete captures older than 1 hour
        # This is just an example - adjust as needed
        threshold = datetime.now().timestamp() - 3600
        for file in storage_path.glob("*.pcap"):
            if file.stat().st_mtime < threshold:
                file.unlink()
        await asyncio.sleep(3600)


async def process_new_packets():
    while True:
        pkt = await packet_queue.get()
        for client in connected_clients:
            try:
                await client.send_json(pkt)
            except:
                connected_clients.remove(client)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(cleanup_old_captures())
    asyncio.create_task(process_new_packets())

app.mount("/", StaticFiles(directory=".",html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
