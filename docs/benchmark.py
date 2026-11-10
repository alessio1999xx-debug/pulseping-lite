#!/usr/bin/env python3
"""Linux-only, 5 fresh-process HTTP checks; no external network traffic.
Usage: python3 docs/benchmark.py /path/to/blackbox_exporter
Requires Go only for inspecting embedded module metadata. Emits JSON to stdout.
"""
import http.server
import json
from pathlib import Path
import platform
import socket
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(sys.argv[1]).resolve()

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Length', '3')
        self.end_headers()
        self.wfile.write(b'OK\n')
    def log_message(self, *args):
        pass

server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
target = 'http://127.0.0.1:%s/health' % server.server_port
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


results = {'pulseping_lite': [], 'blackbox_exporter': []}
config = 'modules:\n  http_2xx:\n    prober: http\n    timeout: 2s\n    http:\n      preferred_ip_protocol: ip4\n'
with tempfile.TemporaryDirectory() as directory:
    config_path = Path(directory) / 'blackbox.yml'
    config_path.write_text(config)
    for _ in range(5):
        # Both timings start before Popen. Five measured runs, no warm-up.
        started = time.perf_counter()
        with tempfile.TemporaryFile() as output:
            p = subprocess.Popen([sys.executable, str(ROOT/'pulseping_lite.py'), target], stdout=output)
            p.wait(timeout=5)
            elapsed = (time.perf_counter()-started)*1000
            output.seek(0)
            text = output.read().decode()
        assert p.returncode == 0 and 'status=200' in text, text
        results['pulseping_lite'].append({'fresh_process_to_result_ms': elapsed})
        port = free_port()
        started = time.perf_counter()
        p = subprocess.Popen([str(BINARY), '--config.file='+str(config_path), '--web.listen-address=127.0.0.1:'+str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            while True:
                if time.perf_counter()-started > 5:
                    raise TimeoutError('exporter readiness exceeded 5 seconds')
                try:
                    with opener.open('http://127.0.0.1:%s/-/healthy' % port, timeout=.1) as response:
                        response.read()
                    break
                except (OSError, urllib.error.URLError):
                    time.sleep(.001)
            readiness = (time.perf_counter()-started)*1000
            query = urllib.parse.urlencode({'module': 'http_2xx', 'target': target})
            with opener.open('http://127.0.0.1:%s/probe?' % port+query, timeout=3) as response:
                text = response.read().decode()
            elapsed = (time.perf_counter()-started)*1000
            assert '\nprobe_success 1\n' in text, text
        finally:
            p.terminate()
            p.wait(timeout=5)
        results['blackbox_exporter'].append({'fresh_process_to_result_ms': elapsed, 'ready_ms': readiness})
server.shutdown()
metadata = subprocess.check_output(['go', 'version', '-m', str(BINARY)], text=True)
summary = {}
for tool, runs in results.items():
    summary[tool] = {metric: statistics.median(run[metric] for run in runs) for metric in runs[0]}
summary['pulseping_lite']['installed_payload_bytes'] = (ROOT/'pulseping_lite.py').stat().st_size
summary['pulseping_lite']['third_party_modules'] = 0
summary['blackbox_exporter']['installed_payload_bytes'] = BINARY.stat().st_size + len(config.encode())
summary['blackbox_exporter']['embedded_go_dependency_modules'] = sum(line.lstrip().startswith('dep\t') for line in metadata.splitlines())
print(json.dumps({'measured_at_rome': time.strftime('%Y-%m-%d %H:%M:%S %Z'), 'machine': platform.platform(), 'python': platform.python_version(), 'runs': results, 'summary_medians': summary, 'blackbox_config': config, 'blackbox_build_metadata': metadata}, indent=2))
