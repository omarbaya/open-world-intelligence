#!/usr/bin/env python3
from pathlib import Path
import http.server
import os
import socketserver
from functools import partial
ROOT=Path(__file__).resolve().parents[1]/'site'
class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control','no-store')
        super().end_headers()

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument('--port',type=int,default=8787)
    args=ap.parse_args()
    with socketserver.TCPServer(('127.0.0.1',args.port),partial(Handler,directory=str(ROOT))) as s:
        print(f'Apri http://127.0.0.1:{args.port}')
        s.serve_forever()
