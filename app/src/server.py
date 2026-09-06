"""Small dependency-free HTTP service used by the platform demonstration."""

from __future__ import annotations

import json
import logging
import os
import signal
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock, Thread

STARTED_AT = time.monotonic()
REQUESTS = 0
REQUESTS_LOCK = Lock()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='{"time":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}',
)
LOGGER = logging.getLogger("platform-api")


def service_info() -> dict[str, str]:
    return {
        "service": "secure-gitops-platform-portfolio",
        "version": os.getenv("APP_VERSION", "dev"),
        "environment": os.getenv("APP_ENV", "local"),
    }


def metrics() -> str:
    with REQUESTS_LOCK:
        request_count = REQUESTS
    uptime = time.monotonic() - STARTED_AT
    return (
        "# HELP platform_http_requests_total Total HTTP requests.\n"
        "# TYPE platform_http_requests_total counter\n"
        f"platform_http_requests_total {request_count}\n"
        "# HELP platform_uptime_seconds Service uptime in seconds.\n"
        "# TYPE platform_uptime_seconds gauge\n"
        f"platform_uptime_seconds {uptime:.3f}\n"
    )


class Handler(BaseHTTPRequestHandler):
    server_version = "PlatformAPI/1.0"

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        global REQUESTS
        with REQUESTS_LOCK:
            REQUESTS += 1

        routes = {
            "/": (HTTPStatus.OK, "application/json", json.dumps(service_info())),
            "/healthz": (HTTPStatus.OK, "application/json", '{"status":"healthy"}'),
            "/readyz": (HTTPStatus.OK, "application/json", '{"status":"ready"}'),
            "/metrics": (HTTPStatus.OK, "text/plain; version=0.0.4", metrics()),
        }
        status, content_type, body = routes.get(
            self.path,
            (HTTPStatus.NOT_FOUND, "application/json", '{"error":"not found"}'),
        )
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        LOGGER.info("client=%s request=%s", self.client_address[0], format % args)


def run() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    server = ThreadingHTTPServer((host, port), Handler)

    def shutdown(_signum: int, _frame: object) -> None:
        LOGGER.info("shutdown requested")
        # shutdown() must run outside the serve_forever() thread.
        Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, shutdown)
    LOGGER.info("service starting on %s:%s", host, port)
    server.serve_forever()


if __name__ == "__main__":
    run()
