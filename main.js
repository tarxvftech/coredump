
let ws;
let liveUpdate = true;
let captures = {};
let displayedPackets = [];
let vis;

async function init() {
    // Get initial captures
    const response = await fetch('/api/captures');
    captures = await response.json();
    updateSourceList();

    // Setup WebSocket
    connectWebSocket();
}

function connectWebSocket() {
    ws = new WebSocket(`ws://${window.location.host}/ws`);

    ws.onopen = () => {
        document.getElementById('connection-status').textContent = 'Connected';
        document.getElementById('connection-status').className = 'status connected';
    };

    ws.onclose = () => {
        document.getElementById('connection-status').textContent = 'Disconnected - Reconnecting...';
        document.getElementById('connection-status').className = 'status disconnected';
        setTimeout(connectWebSocket, 1000);
    };

    ws.onmessage = (event) => {
        if (!liveUpdate) return;
        const packet = JSON.parse(event.data);
        addPacket(packet);
    };
}

function updateSourceList() {
    const sourceList = document.getElementById('source-list');
    sourceList.innerHTML = '';

    for (const [hostname, interfaces] of Object.entries(captures)) {
        const hostDiv = document.createElement('div');
        hostDiv.innerHTML = `<strong>${hostname}</strong>`;

        for (const [iface, filepath] of Object.entries(interfaces)) {
            const ifaceDiv = document.createElement('div');
            ifaceDiv.className = 'source-item';
            ifaceDiv.textContent = iface;
            ifaceDiv.onclick = () => loadCapture(hostname, iface);
            hostDiv.appendChild(ifaceDiv);
        }

        sourceList.appendChild(hostDiv);
    }
}

async function loadCapture(hostname, interface) {
    const response = await fetch(`/api/packets/${hostname}/${interface}`);
    const packets = await response.json();
    clearPackets();
    packets.forEach(addPacket);
}

function addPacket(packet) {
    displayedPackets.push(packet);

    const packetDiv = document.createElement('div');
    packetDiv.className = 'packet';

    // Basic packet info - customize based on your needs
    packetDiv.innerHTML = `
                <div>
                ${packet.summary}
                </div>
            `;

    const detailsDiv = document.createElement('div');
    detailsDiv.className = 'packet-details';
    detailsDiv.innerHTML = `
                <pre></pre>
                <div id="hex-dump"></div>
            `;

    packetDiv.onclick = () => {
        const wasHidden = detailsDiv.style.display === 'none';
        document.querySelectorAll('.packet-details').forEach(d => d.style.display = 'none');
        document.querySelectorAll('.packet').forEach(p => p.classList.remove('selected'));
        if (wasHidden) {
            detailsDiv.style.display = 'block';
            packetDiv.classList.add('selected');
        }
    };

    packetDiv.appendChild(detailsDiv);
    document.getElementById('packets').appendChild(packetDiv);
    updatePacketCount();
    console.log(packet);

    if( packet.json.type == 2048 ){
        let source = "";
        let destination = "";
        let proto = "misc";
        let protos = {
            1: "ICMP",
            2: "IGMP",
            4: "IP-in-IP",
            6: "TCP",
            17: "UDP",
            50: "ESP",
            93: "AX.25",
            94: "IPIP",
            98: "ENCAP",
            132: "SCTP"
        };
        proto = protos [ packet.json.payload.proto ];
        if( proto == undefined ){
            proto = "misc";
        }
        if( proto == "UDP" && packet.json.payload.payload.dport == 53  || packet.json.payload.payload.sport == 53){
            proto = "DNS";
        }
        if( proto == "SCTP" && packet.json.payload.payload.dport == 36412  || packet.json.payload.payload.sport == 36412){
            proto = "S1AP";
        }
        if( proto == "UDP" && packet.json.payload.payload.dport == 2152  || packet.json.payload.payload.sport == 2152){
            proto = "GTP";
        }
        let names = {
            "192.168.170.218":"ue1",
            "192.168.170.1":"enb1",
        };
        source = names[packet.json.payload.src];
        destination = names[packet.json.payload.dst];
        let packetData = {
            size:packet.json.payload.len,
            protocol:proto,
            source: source,
            destination, destination
        };

        if( source != undefined && destination != undefined ){
            vis.visualizePacket( source, destination, packetData);
        }
    }

    // Keep only last 1000 packets in view
    if (displayedPackets.length > 1000) {
        displayedPackets.shift();
        document.getElementById('packets').removeChild(
            document.getElementById('packets').firstChild
        );
    }

    // Auto-scroll if at bottom
    const packetsDiv = document.getElementById('packets');
    if (packetsDiv.scrollTop + packetsDiv.clientHeight >= packetsDiv.scrollHeight - 50) {
        packetsDiv.scrollTop = packetsDiv.scrollHeight;
    }
}

function toggleLiveUpdate() {
    liveUpdate = !liveUpdate;
}

function clearPackets() {
    document.getElementById('packets').innerHTML = '';
    displayedPackets = [];
    updatePacketCount();
}

function updatePacketCount() {
    document.getElementById('packet-count').textContent = 
        `${displayedPackets.length} packets`;
}

function applyFilter(event) {
    if (event.key === 'Enter') {
        const filter = event.target.value.toLowerCase();
        document.querySelectorAll('.packet').forEach(packet => {
            packet.style.display = 
                packet.textContent.toLowerCase().includes(filter) ? 'block' : 'none';
        });
    }
}

init();
var cy = cytoscape({
    container: document.getElementById('cy'),
    elements: [
        { data: { id: 'ue1'}, position: {x:150,y:500}  },
        { data: { id: 'ue2'}, position: {x:200,y:500}  },
        { data: { id: 'ue3' }, position:{x:300,y:500} },
        { data: { id: 'enb1' }, position:{x:175,y:400} },
        { data: { id: 'enb2' }, position:{x:300,y:400} },

        { data: { id: 'dragon' }, classes: ['group']},
        { data: { id: 'open5gs',parent:"dragon" }, classes: ['group']},
        { data: { id: 'epc',parent:"open5gs" }, classes: ['group'] },
        { data: { id: 'ims',parent:"open5gs" }, classes: ['group'] },

        { data: { id: 'mme',parent:"epc" }, position:{x:175,y:300} },
        { data: { id: 'sgwu',parent:"epc" }, position:{x:300,y:300} },
        { data: { id: 'upf',parent:"epc" }, position:{x:300,y:200} },
        { data: { id: 'sgwc',parent:"epc" }, position:{x:250,y:250} },
        { data: { id: 'amf',parent:"epc" }, position:{x:175,y:150} },
        { data: { id: 'smf',parent:"epc" }, position:{x:250,y:100} },

        { data: { id: 'pyhss',parent:"epc" }, position:{x:150,y:0} },
        { data: { id: 'hss',parent:"epc" }, position:{x:250,y:0} },
        { data: { id: 'osmohlr',parent:"epc" }, position:{x:350,y:0} },
        { data: { id: 'pcrf',parent:"epc" }, position:{x:250,y:50} },

        { data: { id: 'vpn',parent:"open5gs" }, position:{x:100,y:-100} },

        { data: { id: 'dns',parent:"open5gs" }, position:{x:50,y:-100} },
        { data: { id: 'mysql',parent:"open5gs" }, position:{x:150,y:-100} },
        { data: { id: 'mongo',parent:"open5gs" }, position:{x:200,y:-100} },

        { data: { id: 'metrics',parent:"open5gs" }, position:{x:350,y:-100} },
        { data: { id: 'grafana',parent:"open5gs" }, position:{x:300,y:-100} },
        
        { data: { id: 'rtpengine',parent:"ims" }, position:{x:-50,y:50} },
        { data: { id: 'osmomsc',parent:"ims" }, position:{x:50,y:200} },
        { data: { id: 'pscscf',parent:"ims" }, position:{x:-50,y:100} },
        { data: { id: 'sscscf',parent:"ims" }, position:{x:-50,y:200} },
        { data: { id: 'iscscf',parent:"ims" }, position:{x:-50,y:300} },
        { data: { id: 'smsc',parent:"ims" }, position:{x:0,y:100} },

        { data: { id: 'x1', source: 'enb1', target: 'mme' }, classes: "rt" },
        { data: { id: 'x2', source: 'enb2', target: 'mme' }, classes: "rt" },
        { data: { id: 'x3', source: 'enb1', target: 'sgwu' }, classes: "rt" },
        { data: { id: 'x4', source: 'enb2', target: 'sgwu' }, classes: "rt" },
        { data: { id: 'x5', source: 'sgwu', target: 'upf' }, classes: "rt" },
        { data: { id: 'x7', source: 'ue1', target: 'enb1' }, classes: "rt" },
        { data: { id: 'x8', source: 'ue2', target: 'enb1' }, classes: "rt" },
        { data: { id: 'x9', source: 'ue3', target: 'enb2' }, classes: "rt" },
        { data: { id: 'xA', source: 'mme', target: 'sgwc' }, classes: "rt" },
        { data: { id: 'xB', source: 'sgwc', target: 'amf' }, classes: "rt" },
        { data: { id: 'xC', source: 'amf', target: 'sgwu' }, classes: "rt" },
        { data: { id: 'xD', source: 'amf', target: 'upf' }, classes: "rt" },
        { data: { id: 'xE', source: 'mme', target: 'osmomsc' }, classes: "rt" },
        { data: { id: 'xF', source: 'hss', target: 'mongo' }, classes: "rt" },
        { data: { id: 'x10', source: 'pyhss', target: 'mysql' }, classes: "rt" },
    ],

    style: [
        {
            selector: 'edge',
            style: {
                'curve-style': 'round-taxi',
                "taxi-direction": "auto",
                "taxi-turn": '100%',
                "taxi-turn-min-distance": 5,
                "taxi-radius": 15,
                'width': 3,
                'line-color': '#111',
                'target-arrow-color': '#111',
                //'target-arrow-shape': 'triangle',
                'line-style':'dashed',
                'line-dash-pattern': [1,3,1,4,1,5],
                'line-dash-offset': 0,
                "edge-text-rotation": "autorotate"
            }
        },
        {
            selector: 'node',
            style: {
                'background-color': '#eee',
                'label': 'data(id)',
                "text-outline-color": "#fff",
                "text-outline-width": 3,
                "text-valign":"center",
                "text-halign":"center",
            }
        }, 
        {
            selector: 'node.packet',
            style: {
                'label': '',
            }
        }, 
        {
            selector: 'node.group',
            style: {
                "text-valign":"top",
            }
        }, 
        {
            selector: 'node > node',
            style: {
                'background-color': '#ddd',
            }
        }, 
        {
            selector: 'node > node > node',
            style: {
                'background-color': '#ccc',
            }
        }, 
        {
            selector: 'node > node > node > node',
            style: {
                'background-color': '#bbb',
            }
        }, 
        {
            selector: 'node > node > node > node > node',
            style: {
                'background-color': '#aaa',
            }
        }, 
    ],

    layout: {
        //name: 'klay',
        //https://github.com/cytoscape/cytoscape.js-klay?tab=readme-ov-file
        name: 'preset',
    }
});
class PacketVisualizer {
    constructor(cy) {
        this.cy = cy;
        this.packetCount = 0;
    }
    visualizePacket(sourceId, targetId, packetData) {
        let edge = this.cy.$(`edge[source="${sourceId}"][target="${targetId}"]`);
        let swapdirection = false;
        if( ! edge.length ){
            edge = this.cy.$(`edge[source="${targetId}"][target="${sourceId}"]`);
            swapdirection = true;
        }
        if( ! edge.length ){
            //maybe add an edge or node as required, and recompute layout?
        }
        const color = this.getProtocolColor(packetData.protocol);
        const size = 2 + 2*Math.log10( packetData.size );
        let frompos, midpos, topos;
        if( swapdirection == true ){
            frompos = {x:edge.target().position().x, y:edge.target().position().y};
            midpos = {x:edge.midpoint().x, y:edge.midpoint().y};
            topos = {x:edge.source().position().x, y:edge.source().position().y};
        } else {
            frompos = {x:edge.source().position().x, y:edge.source().position().y};
            midpos = {x:edge.midpoint().x, y:edge.midpoint().y};
            topos = {x:edge.target().position().x, y:edge.target().position().y};
        }

        const particle = this.cy.add({
            group: 'nodes',
            data: { 
                id: `packet-${this.packetCount++}`,
                label: ''
            },
            classes: ["packet"],
            position: frompos,
        });

        particle.style({
            'width': size,
            'height': size,
            'background-color': color,
            'shape': 'ellipse',
            'opacity': 0.8,
        });


        // Animate particle
        particle.animate({
            position: midpos,
            duration: 50,
            easing: 'ease-in',
            complete: () => {
                particle.animate({
                    position: topos,
                    duration: 50,
                    easing: 'ease-out',
                    complete: () => {
                        particle.remove()
                    }
                });
            }
        });

        
    }

    getProtocolColor(protocol) {
        return {
            'ICMP': '#f0f',
            'DNS': '#a22',
            'TCP': '#00f',
            'UDP': '#0f0',
            'GTP': '#f0f',
            'SCTP': '#7f0',
            'ESP': 'yellow',
        }[protocol] || 'black';
    }
}

let packet = {
    source: "enb1",
    destination: "mme",
    protocol: "SCTP",
    size: "10"
};
function testPacket() {
    // Get a random edge from the graph
    const edges = cy.edges();
    const idx = Math.floor(Math.random() * edges.length);
    const edge = edges[idx];

    // Generate test packet data
    const packet = {
        source: edge.source().id(),
        destination: edge.target().id(),
        protocol: ['TCP', 'UDP', 'GTP', 'SCTP'][Math.floor(Math.random() * 4)],
        size: Math.floor(Math.random() * 1400) + 100  // 100-1500 bytes
    };
    if( Math.random() > .5){
        let t = packet.destination;
        packet.destination = packet.source;
        packet.source = t;
    }

    // Visualize it
    vis.visualizePacket(
        packet.source,
        packet.destination,
        packet
    );
}

vis = new PacketVisualizer(cy);
//setInterval(testPacket, 100);
