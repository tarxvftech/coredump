# CoreDump

Network visualization tool originally focused on LTE network troubleshooting.

Captures and visualizes packet flows across complex service meshes, helping you
understand what's actually happening versus what should be happening.

Originally made (with a fair bit of AI at the time) to troubleshoot a specific Baicells eNB bug with GTP.

Later was just kinda neat. Lots of room to improve.

License: AGPLv3 (at least as far as my actual contributions).

## Features
- Packet capture from multiple hosts, including all interfaces and all interfaces in all containers.

## FutureFeatures
- Protocol-aware packet analysis (GTP, S1AP, Diameter)
- Interactive graph visualization of service relationships
- Compare actual vs expected packet flows
- Stream captures in real-time or analyze stored captures

## Use Cases
- Debug LTE core network services
- Visualize GTP tunnel flows
- Track session establishment
- Identify protocol mismatches
- Analyze handover issues
- Map service dependencies
- Why the fuck is my Baicells eNB doing X


<!--I am done with tabbing through five workspaces and a billion
terminals (or worse one or more screen sessions), only to have to
tcpdump -w, scp it back home, open that in wireshark, and repeat over and
over. So. OpenObserve and packet captures in one place will be good.I
am done with tabbing through five workspaces and a billion terminals
(or worse one or more screen sessions), only to have to tcpdump
-w, scp it back home, open that in wireshark, and repeat over and
over. So. OpenObserve and packet captures in one place will be good.-->
