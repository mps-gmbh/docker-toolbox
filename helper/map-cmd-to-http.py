#!/usr/bin/python3
"""
Very simple HTTP server which asznyncron executes a given command on get request
Usage:
    ./map-cmd-to-http.py <cmd> ... <args>
"""

import sys
import subprocess 

from http.server import HTTPServer, BaseHTTPRequestHandler


class S(BaseHTTPRequestHandler):
    cmd = None
    def do_GET(self):
        subprocess.Popen(self.cmd)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        content = "Executed cmd: {}".format(" ".join(self.cmd)) + "\n"
        self.wfile.write(content.encode("utf-8"))


def run(args):
    S.cmd = args 
    httpd = HTTPServer(('', 8000), S )
    httpd.serve_forever()

if __name__ == "__main__":
    run(sys.argv[1:])
