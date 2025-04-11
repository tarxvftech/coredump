#!/usr/bin/env python3
# collect.py

import yaml
import subprocess
import sys
import signal
import time
from pathlib import Path
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description='Start packet capture across all containers')
    parser.add_argument('--collector', default='http://localhost:8000',
                       help='Collector URL (default: http://localhost:8000)')
    parser.add_argument('--compose-file', default='docker-compose.yml',
                       help='Docker compose file (default: docker-compose.yml)')
    parser.add_argument('--filter', default='',
                       help='Additional tcpdump filter')
    parser.add_argument('--exclude', nargs='*', default=[],
                       help='Container names to exclude')
    return parser.parse_args()

class CaptureManager:
    def __init__(self, collector_url, compose_file, filter_str, exclude):
        self.collector_url = collector_url
        self.compose_file = compose_file
        self.filter_str = filter_str
        self.exclude = exclude
        self.processes = {}
        self.running = True
        
        # Handle graceful shutdown
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

    def get_containers(self):
        with open(self.compose_file) as f:
            compose = yaml.safe_load(f)
        return [svc for svc in compose.get('services', {}).keys()
                if svc not in self.exclude]

    def start_capture(self, container):
        cmd = [
            'docker-compose',
            'exec',
            '-T',  # disable pseudo-tty
            container,
            'python3',
            '-m',
            'coredump.capture',
            '-i', 'any',
            '--http', self.collector_url
        ]
        
        if self.filter_str:
            cmd.extend(['--filter', self.filter_str])

        print(f"Starting capture on {container}")
        return subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    def start_all(self):
        containers = self.get_containers()
        print(f"Found containers: {', '.join(containers)}")
        
        for container in containers:
            try:
                self.processes[container] = self.start_capture(container)
            except Exception as e:
                print(f"Failed to start capture on {container}: {e}")

    def monitor(self):
        while self.running:
            for container, proc in list(self.processes.items()):
                if proc.poll() is not None:
                    print(f"Capture stopped on {container}, restarting...")
                    try:
                        self.processes[container] = self.start_capture(container)
                    except Exception as e:
                        print(f"Failed to restart capture on {container}: {e}")
            time.sleep(5)

    def shutdown(self, signum, frame):
        print("\nShutting down captures...")
        self.running = False
        for container, proc in self.processes.items():
            print(f"Stopping capture on {container}")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        sys.exit(0)

def main():
    args = parse_args()
    
    if not Path(args.compose_file).exists():
        print(f"Error: {args.compose_file} not found")
        sys.exit(1)

    manager = CaptureManager(
        args.collector,
        args.compose_file,
        args.filter,
        args.exclude
    )
    
    manager.start_all()
    manager.monitor()

if __name__ == '__main__':
    main()
