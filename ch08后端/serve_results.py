#!/usr/bin/env python3
"""Local-only static preview with HTTP byte ranges for seeking H.264 videos."""

import argparse
import functools
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def byte_range(header, size):
    if not header.startswith("bytes=") or "," in header or size <= 0:
        raise ValueError("Unsupported byte range")
    start, end = header[6:].split("-", 1)
    if not start:
        length = int(end)
        if length <= 0:
            raise ValueError("Invalid suffix length")
        return max(0, size - length), size - 1
    start = int(start)
    end = min(int(end), size - 1) if end else size - 1
    if start < 0 or start >= size or end < start:
        raise ValueError("Unsatisfiable range")
    return start, end


class Handler(SimpleHTTPRequestHandler):
    def send_head(self):
        self.range_end = None
        path = Path(self.translate_path(self.path))
        requested = self.headers.get("Range")
        if not requested or not path.is_file():
            return super().send_head()
        stream = path.open("rb")
        size = os.fstat(stream.fileno()).st_size
        try:
            start, end = byte_range(requested, size)
        except (ValueError, TypeError):
            stream.close()
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(str(path)))
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        stream.seek(start)
        self.range_end = end
        return stream

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def copyfile(self, source, outputfile):
        if self.range_end is None:
            return super().copyfile(source, outputfile)
        remaining = self.range_end - source.tell() + 1
        while remaining > 0:
            block = source.read(min(65536, remaining))
            if not block:
                break
            outputfile.write(block)
            remaining -= len(block)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path(__file__).resolve().parent / "results/driving_lk")
    parser.add_argument("--port", type=int, default=8769)
    args = parser.parse_args()
    handler = functools.partial(Handler, directory=str(args.directory.resolve()))
    with ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
        print(f"Preview: http://127.0.0.1:{args.port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
