# Reproduce the local footprint check

From the repository root on Linux, with Python 3.9+, Go (`go version -m` metadata inspection only), curl and tar:

```sh
mkdir -p /tmp/pulseping-benchmark
cd /tmp/pulseping-benchmark
curl -fLO https://github.com/prometheus/blackbox_exporter/releases/download/v0.29.1/blackbox_exporter-0.29.1.linux-amd64.tar.gz
curl -fLO https://github.com/prometheus/blackbox_exporter/releases/download/v0.29.1/sha256sums.txt
# Official archive SHA256 verified for the measurements in this repository:
echo 'b82b81839e6317e84fdd367f46d7ddd3b773fa09cbe2e3d5633a59171d741e76  blackbox_exporter-0.29.1.linux-amd64.tar.gz' | sha256sum -c -
tar -xzf blackbox_exporter-0.29.1.linux-amd64.tar.gz
# Return to your pulseping-lite checkout, then:
python3 docs/benchmark.py /tmp/pulseping-benchmark/blackbox_exporter-0.29.1.linux-amd64/blackbox_exporter > /tmp/pulseping-results.json
```

The harness starts a loopback-only HTTP server and a fresh exporter bound to loopback for each run. It makes five alternating checks per tool and terminates each exporter. Its temporary minimal configuration is included in the result JSON. No persistent services, database, Prometheus server or external API calls are involved.

Size: `pulseping_lite.py` byte count versus exporter binary plus minimal YAML byte count. Neither includes license/readme files, shared runtime, the demo GIF, benchmark tooling or the surrounding monitoring ecosystem. Module count: lite's imports are standard-library only; exporter count is the number of `dep` records in the downloaded binary's `go version -m` build metadata, not OS package count.

RSS was intentionally omitted: the first Python-parent `wait4` approach carried inherited high-water marks and was discarded. GNU time was unavailable; apt installation failed because repository metadata could not be fetched/verified. No unreliable RSS figures are published. Uptime Kuma was not installed or measured (Docker unavailable). OS caches were not flushed; host load was not controlled. Timing is illustrative, not a performance promise.

## Re-record the demo

Install asciinema and [agg](https://docs.asciinema.org/manual/agg/installation/) separately; these are documentation tools, not runtime dependencies. From the repository root:

```sh
asciinema rec --cols 98 --rows 18 -q -c 'python3 docs/record-demo.py' docs/demo.cast
agg --theme dracula --font-family 'JetBrains Mono' --font-size 17 --line-height 1.3 --fps-cap 15 --last-frame-duration 3 docs/demo.cast docs/demo.gif
```

The capture script types three real commands and streams their actual output; only typing and pause timing are staged. It does not upload the recording. The first command starts the already-downloaded tool; the second intentionally sets a 365-day warning window to demonstrate exit 1. The TCP example assumes nothing is listening on local port 9; choose another unused port if necessary.
