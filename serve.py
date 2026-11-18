#!/usr/bin/env python3
"""Build the site and serve dist/ for local preview."""

from __future__ import annotations

import argparse
import os
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import build

DIST = Path(__file__).resolve().parent / "dist"
DEFAULT_PORT = 8000


class QuietHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, format: str, *args: object) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and preview the directory site")
    parser.add_argument("--drafts", action="store_true", help="include draft pages")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", DEFAULT_PORT)))
    parser.add_argument("--no-build", action="store_true", help="serve existing dist/ without rebuilding")
    args = parser.parse_args()

    if not args.no_build:
        build.build(include_drafts=args.drafts)
    elif not DIST.exists():
        sys.stderr.write("dist/ is missing; run without --no-build first\n")
        sys.exit(1)

    handler = partial(QuietHandler, directory=str(DIST))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    server.allow_reuse_address = True
    print(f"Serving {DIST} at http://127.0.0.1:{args.port}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped")
        server.server_close()


if __name__ == "__main__":
    main()
