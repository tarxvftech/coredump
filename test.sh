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
