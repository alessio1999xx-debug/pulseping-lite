# pulseping-lite: uptime monitor and TLS certificate expiry check in one Python file

pulseping-lite helps with quick uptime and TLS certificate expiry checks for one URL or `host:port`, from cron or CI, without running a monitoring server. Python stdlib only (3.9+), plain text or `--json` output, and exit codes 0/1/2 so cron or CI can act on the result.


**Free · MIT · one file · no pip install.** One target per run; no dashboard, history or built-in alerts.

Need multi-monitor workflows? **[PulsePing CLI](https://py-forge.com/products/pulseping-cli?utm_source=github&utm_medium=readme&utm_campaign=pulseping-lite)** · **[PyForge All-Access Pass](https://py-forge.com/pass?utm_source=github&utm_medium=readme&utm_campaign=pulseping-lite)**

## Demo

![Real terminal demo: one command checks uptime and TLS expiry; a larger warning window fails with exit 1; a refused TCP connection also fails.](docs/demo.gif)

Recorded on November 10, 2026 with asciinema + agg; real commands and output, no simulated results. The file is already downloaded when the demo starts. Public endpoint latency and certificate lifetime will change.

```console
$ python3 pulseping_lite.py https://example.com
UP   https://example.com  status=200  172.5 ms  cert expires in 45 days
$ python3 pulseping_lite.py https://example.com --warn-days 365
DOWN https://example.com  status=200  200.0 ms  cert expires in 45 days
  certificate expires in 45 days (warn at 365)
```

The first check exits `0`; the deliberately larger warning window exits `1` even though HTTP is up. [Recording source](docs/demo.cast) · [Capture script](docs/record-demo.py).

## One-command install (zero dependencies)

```bash
curl -fsSLO https://raw.githubusercontent.com/alessio1999xx-debug/pulseping-lite/main/pulseping_lite.py && python3 pulseping_lite.py https://example.com
```

Requires an existing Python 3.9+ installation and `curl` for the download command. Alternatively, download `pulseping_lite.py`, inspect it, and run it with Python. No `pip install`, no config file, no state. Flags: `--warn-days`, `--timeout`, `--tls`, `--insecure`, `--json`, `--version`.

## Usage

### HTTP(S) health check for a URL

```bash
python3 pulseping_lite.py https://example.com/health
python3 pulseping_lite.py http://127.0.0.1:8080/ready --timeout 3
```

An HTTP status below 400 counts as up. `--timeout` is in seconds (default 5).

### TCP check for host:port

```bash
python3 pulseping_lite.py db.local:5432 --timeout 2
```

Without `--tls`, a `host:port` target is only a TCP connect check (databases, SSH, …).

### TLS certificate expiry (days left)

```bash
python3 pulseping_lite.py https://example.com --warn-days 14
python3 pulseping_lite.py example.com:443 --tls --warn-days 14
```

For `https://` URLs the certificate is read from the same connection; for `host:port` add `--tls`. The check fails when the certificate expires in fewer than `--warn-days` days (default 14).

`--insecure` skips certificate verification. Use it only for self-signed or internal certs you already trust; certificate expiry can be unavailable in this mode (`null` in JSON).

### JSON output

Real output captured November 10, 2026 (network-dependent values vary):

```console
$ python3 pulseping_lite.py https://example.com --json
{
  "target": "https://example.com",
  "up": true,
  "status_code": 200,
  "tls_days_left": 45,
  "issuer": null,
  "latency_ms": 172.1,
  "error": null
}
```

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Target is up, and the TLS certificate (if read) is not within `--warn-days` of expiry |
| `1` | Target is down (HTTP ≥ 400, connect failure, timeout, TLS error) **or** the certificate is expired / fewer than `--warn-days` days left |
| `2` | Bad arguments (e.g. a target that is neither a URL nor `host:port`) |

There is no separate "warning" code: an expiring certificate is a failure (`1`).

## Cron example

```cron
# every 5 minutes: mail me if the site is down or the cert expires within 14 days
*/5 * * * * python3 /opt/pulseping_lite.py https://example.com/health --warn-days 14 || echo "example.com check failed" | mail -s "uptime" you@example.com
```

pulseping-lite does not send alerts and checks one target per run: it exits non-zero and you decide what happens next (mail, a script, a failed CI job).

## Measured footprint: lite CLI vs Blackbox Exporter

A one-shot check and a persistent monitoring exporter solve different jobs. This is a small, reproducible footprint check, **not a full monitoring-stack shootout**.

| Metric | pulseping-lite 0.1.0 | [Prometheus Blackbox Exporter 0.29.1](https://github.com/prometheus/blackbox_exporter/releases/tag/v0.29.1) |
| --- | ---: | ---: |
| Installed payload, excluding shared runtime | 6,511 bytes (one Python file) | 35,573,925 bytes (binary + minimal YAML) |
| Fresh-process start → first successful local HTTP result, median of 5 | 64.2 ms | 12.7 ms |
| Third-party code dependencies shipped/required | 0 Python modules | 40 Go modules embedded in binary |

**Method and machine.** Measured November 10, 2026, Europe/Rome, on this shared Linux box: kernel 6.12.113+, x86_64 KVM, 8 vCPUs (Intel Xeon), 16,002 MiB RAM, Python 3.13.5; exporter official linux-amd64 release built with Go 1.27.3. Five alternating fresh-process runs per tool, no warm-up, no filesystem-cache flush, no CPU/memory isolation. Both check the same local HTTP server returning 200 and `OK`; no DNS, public network or TLS in this benchmark.

Timing starts before process launch. For lite it ends after successful CLI exit. For the exporter it includes readiness polling (1 ms retry interval), one `/probe` request, and validation of `probe_success 1`, but excludes shutdown. It is **fresh-process**, not cold-disk timing or steady-state probe latency. Blackbox Exporter was faster in this test; lite's advantage here is its smaller payload and lack of third-party Python packages, not a blanket performance claim.

Payload uses exact file byte counts, not compressed downloads or filesystem blocks. Python, its stdlib, CA certificates and OS libraries are excluded; Go dependencies are compiled into the exporter, not packages the user installs. The dependency counts have different packaging meanings and do not estimate security or maintenance burden. No Prometheus server, dashboard, history or alerting stack was installed for either side.

**Not measured:** reliable peak RSS, TLS performance, Uptime Kuma, or the size/memory of a complete monitoring stack. No memory or Uptime Kuma numbers are claimed.

[Raw runs + release build metadata](docs/benchmark-results.json) · [Reproduction script](docs/benchmark.py) · [Setup and exact scope](docs/BENCHMARK.md).

## What it does not do

- One target per invocation; no scheduler, persistent service, history or dashboard.
- No built-in alert delivery. Cron, CI or your wrapper decides what to do with exit codes.
- HTTP status / TCP connectivity and TLS expiry only; it is not a full replacement for Blackbox Exporter or Uptime Kuma.
- `--timeout` bounds individual network operations, not the entire process wall time; redirects are not followed.

## Need more?

The full **[PulsePing CLI](https://py-forge.com/products/pulseping-cli?utm_source=github&utm_medium=readme&utm_campaign=pulseping-lite)** helps with:

- many monitors in one config file (HTTP with expected status and keyword, TCP, DNS, certificate expiry, gRPC health)
- consecutive-failure thresholds, so a single blip does not become an alert
- alerts to Telegram, Discord, Slack, PagerDuty or a webhook, with recovery notices
- a static, zero-JavaScript status page

One-time payment, no subscription. Every PyForge tool is also in the [All-Access Pass](https://py-forge.com/pass?utm_source=github&utm_medium=readme&utm_campaign=pulseping-lite).

## Tests

```bash
python3 test_pulseping_lite.py
```

The tests use only a local server.

## License

MIT (this lite version). The full PulsePing CLI is sold separately under its own license.
