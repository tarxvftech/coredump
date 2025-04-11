```
I want to see:
(traffic here means packets and logs)

eNB-related traffic and issues
    eNB connection to MME and that sort of thing
UE-related traffic
    attach process
    bearer negotiation
    GTP tunnels
IMS-related traffic


I have to somehow tie the logical with the actual together.


dashed edges can show overall traffic balance through animation line-dash-offset + is one way, - is the other, and the value can be proportional to the speed.
color the edges based on primary traffic type
flash edges based on errors, resets, retransmissions, etc
colored dots flying aroudn for packets, color for type, size for length
    they can go flying off if we get ICMP redirects or something
    big animated X pops up and shakes and makes funny noises
extra edges parallel to original edge to show tcp, sctp connections?
    then we can make the width the traffic rate, with a decay
    retransmissions get a ? aniamted with funny noises


instead of having packets going out, and replies coming back
    so that packets appear to pass each other when visualized
    show the *source* sending a packet, and getting a reply back
    TCP should get a dashed pipe and show average data flow direction
    showing rejections and drops should be interesting and intuitive

maybe I can measure delay from backend to frontend and schedule visualizations to be accurate relative to each other?


```
