import contextlib
import datetime as dt
import http.server
import io
import json
import socket
import threading
import unittest

import pulseping_lite as pl


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        code = 500 if self.path == "/fail" else 200
        self.send_response(code)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *a):
        pass


def run(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = pl.main(argv)
    return code, out.getvalue()


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.HTTPServer(("127.0.0.1", 0), H)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_parse_target(self):
        self.assertEqual(pl.parse_target("https://a.com/x?y=1"), ("https", "a.com", 443, "/x?y=1"))
        self.assertEqual(pl.parse_target("http://a.com:8080"), ("http", "a.com", 8080, "/"))
        self.assertEqual(pl.parse_target("db.local:5432"), ("tcp", "db.local", 5432, "/"))
        self.assertEqual(pl.parse_target("[::1]:22"), ("tcp", "::1", 22, "/"))
        with self.assertRaises(ValueError):
            pl.parse_target("ftp://a.com")
        with self.assertRaises(ValueError):
            pl.parse_target("justahost")

    def test_http_up(self):
        code, out = run([f"http://127.0.0.1:{self.port}/"])
        self.assertEqual(code, 0)
        self.assertIn("UP", out)
        self.assertIn("status=200", out)

    def test_http_500_is_down(self):
        code, out = run([f"http://127.0.0.1:{self.port}/fail"])
        self.assertEqual(code, 1)
        self.assertIn("DOWN", out)

    def test_tcp_up_and_down(self):
        self.assertEqual(run([f"127.0.0.1:{self.port}"])[0], 0)
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        free = s.getsockname()[1]
        s.close()
        self.assertEqual(run([f"127.0.0.1:{free}", "--timeout", "1"])[0], 1)

    def test_json_output(self):
        code, out = run([f"http://127.0.0.1:{self.port}/", "--json"])
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertTrue(data["up"])
        self.assertEqual(data["status_code"], 200)

    def test_bad_target_exit_2(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(pl.main(["nonsense"]), 2)

    def test_days_left(self):
        future = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=30, hours=1)).strftime("%b %d %H:%M:%S %Y GMT")
        self.assertIn(pl.days_left({"notAfter": future}), (30,))
        past = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=3)).strftime("%b %d %H:%M:%S %Y GMT")
        self.assertLess(pl.days_left({"notAfter": past}), 0)
        self.assertIsNone(pl.days_left({}))


if __name__ == "__main__":
    unittest.main()
