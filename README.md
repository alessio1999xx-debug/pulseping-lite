# pulseping-lite: check SSL certificate expiry and uptime from cron

pulseping-lite helps you check that one URL or host:port is up (HTTP status or TCP connect) and how many days are left on its TLS certificate, with a single command. It is stdlib-only (Python 3.9+), prints plain text or `--json`, and returns exit code 0/1/2, so cron or CI can tell OK, failure and bad arguments apart.

- One file, Python 3.9+. Nothing to `pip install`.
- One target per run. No config file, no state, **no alerts**, **no multi-URL monitoring**.
- Flags: `--warn-days`, `--timeout`, `--tls`, `--insecure`, `--json`, `--version`.

## Install

```bash
curl -fsSLO https://raw.githubusercontent.com/alessio1999xx-debug/pulseping-lite/main/pulseping_lite.py
python3 pulseping_lite.py --help
```

## Check SSL certificate expiry (days left)

```bash
python3 pulseping_lite.py https://example.com/health --warn-days 14
# UP   https://example.com/health  status=200  63 ms  cert expires in 52 days

python3 pulseping_lite.py example.com:443 --tls --warn-days 14
python3 pulseping_lite.py example.com:443 --tls --json
```

For `https://` targets the certificate expiry is read from the same connection. For a `host:port` target, add `--tls` (for example `host:443`) to also read the certificate. The check fails when the certificate expires in fewer than `--warn-days` days (default 14).

`--insecure` skips certificate verification (hostname check and chain). Use it only for self-signed or internal certs you already trust; do not use it on public endpoints.

## Uptime check for a URL or host:port

```bash
# HTTP: status below 400 counts as up
python3 pulseping_lite.py https://example.com/health
python3 pulseping_lite.py http://127.0.0.1:8080/ready --timeout 3

# TCP connect only (database, SSH, …)
python3 pulseping_lite.py db.local:5432 --timeout 2
```

Without `--tls`, a `host:port` target is only a TCP connect check. Use `--timeout` (seconds, default 5) to bound how long the check waits.

## Run it from cron with exit codes 0/1/2

| Exit code | Meaning |
| --- | --- |
| `0` | Target is up, and the TLS certificate (if read) is not within `--warn-days` of expiry |
| `1` | Target is down (HTTP ≥ 400, connect failure, timeout, TLS error) **or** the certificate is expired / expiring within `--warn-days` |
| `2` | Bad arguments (for example a target that is neither a URL nor `host:port`) |

There is no separate "warning" exit code: a certificate that is about to expire is treated as failure (`1`), so cron can mail or fail the job the same way as a down target.

```cron
*/5 * * * * python3 /opt/pulseping_lite.py https://example.com/health || echo "example.com check failed" | mail -s "uptime" you@example.com
```

Use `--json` when a script needs structured output. pulseping-lite does **not** send alerts itself and does **not** watch many URLs: it exits non-zero and you decide what to do with that (mail, a script, a CI failure).

## pulseping-lite vs PulsePing CLI

pulseping-lite checks **one target at a time**. It has no history, no alerts and no multi-URL monitoring.

The full **[PulsePing CLI](https://py-forge.com/products/pulseping-cli?utm_source=github&utm_medium=readme&utm_campaign=pulseping-lite)** helps with:

- many monitors in one config file: HTTP with expected status and keyword, TCP, DNS, certificate expiry and gRPC health
- a monitor goes down only after several consecutive failures, so one blip is not an alert
- alerts to Telegram, Discord, Slack, PagerDuty or a webhook, with recovery notices
- a static, zero-JavaScript status page you can host on GitHub Pages, Cloudflare Pages or S3

One-time payment, yours to keep. No subscription.

Or get every PyForge tool, current and future, with the [All-Access Pass](https://py-forge.com/pass?utm_source=github&utm_medium=readme&utm_campaign=pulseping-lite).

## Tests

```bash
python3 test_pulseping_lite.py
```

The tests use only a local server.

## License

MIT (this lite version). The full PulsePing CLI is sold separately under its own license.
