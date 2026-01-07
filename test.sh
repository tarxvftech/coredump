
## -i interface (like eth0, or wlan0, or whatever you have)
sudo tcpdump -i wlp0s20f3 \
	-U \
	-w - \
	not tcp port 8000 \
	| \
	curl --no-buffer \
	-H "Content-Type: application/vnd.tcpdump.pcap" \
	-H "Transfer-Encoding: chunked" \
	-T - \
	http://localhost:8000/api/capture/tangen/wlp0s20f3
#		change hostname/port to your python server reference
#		change 'tangen' to the label for your listener - so maybe a docker container id. 
#		'tangen' is my laptop's hostname. wlp0s20f3 is of course my laptops wifi card
#		so the backend gets a 'node' name and then a 'interface' name or similar.
#
