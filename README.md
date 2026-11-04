# pulseping-lite: uptime monitor and TLS certificate expiry check in one Python file

pulseping-lite is a zero-dependency health check for one URL or `host:port`: it tells you if the target is up (HTTP status or TCP connect) and how many days are left on its TLS certificate. Python stdlib only (3.9+), plain text or `--json` output, and exit codes 0/1/2 so cron or CI can act on the result.

## Demo

![pulseping-lite demo](docs/demo.gif)

Real output (captured Nov 4, 2026):

```console
$ python3 pulseping_lite.py https://example.com
UP   https://example.com  status=200  101.2 ms  cert expires in 51 days
$ echo $?
0

$ python3 pulseping_lite.py https://example.com --warn-days 60
DOWN https://example.com  status=200  50.8 ms  cert expires in 51 days
  certificate expires in 51 days (warn at 60)
$ echo $?
1

$ python3 pulseping_lite.py 127.0.0.1:9 --timeout 2
DOWN 127.0.0.1:9  0.9 ms
  ConnectionRefusedError: [Errno 111] Connection refused
```

## One-command install (zero dependencies)

```bash
curl -fsSLO https://raw.githubusercontent.com/alessio1999xx-debug/pulseping-lite/main/pulseping_lite.py && python3 pulseping_lite.py https://example.com
```

No `pip install`, no config file, no state. Flags: `--warn-days`, `--timeout`, `--tls`, `--insecure`, `--json`, `--version`.

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
# UP   example.com:443  37.3 ms  cert expires in 51 days
```

For `https://` URLs the certificate is read from the same connection; for `host:port` add `--tls`. The check fails when the certificate expires in fewer than `--warn-days` days (default 14).

`--insecure` skips certificate verification. Use it only for self-signed or internal certs you already trust.

### JSON output

```console
$ python3 pulseping_lite.py example.com:443 --tls --json
{
  "target": "example.com:443",
  "up": true,
  "status_code": null,
  "tls_days_left": 51,
  "issuer": "SSL Corporation, Cloudflare TLS Issuing ECC CA 3",
  "latency_ms": 38.2,
  "error": null
}
```

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Target is up, and the TLS certificate (if read) is not within `--warn-days` of expiry |
| `1` | Target is down (HTTP ≥ 400, connect failure, timeout, TLS error) **or** the certificate is expired / expiring within `--warn-days` |
| `2` | Bad arguments (e.g. a target that is neither a URL nor `host:port`) |

There is no separate "warning" code: an expiring certificate is a failure (`1`).

## Cron example

```cron
# every 5 minutes: mail me if the site is down or the cert expires within 14 days
*/5 * * * * python3 /opt/pulseping_lite.py https://example.com/health --warn-days 14 || echo "example.com check failed" | mail -s "uptime" you@example.com
```

pulseping-lite does not send alerts and checks one target per run: it exits non-zero and you decide what happens next (mail, a script, a failed CI job).

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
