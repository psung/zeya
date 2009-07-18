#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Web music server.

import BaseHTTPServer

import json
import urllib

from rhythmbox import RhythmboxBackend

library_contents = []

class ZeyaHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.serve_static_content('/library.html')
        elif self.path == '/getlibrary':
            self.serve_library()
        elif self.path.startswith('/getcontent?'):
            self.serve_content(urllib.unquote(self.path[12:]))
        else:
            self.serve_static_content(self.path)
    def do_POST(self):
        pass
    def get_content_type(self, path):
        if path.endswith('.html'):
            return 'text/html'
        elif path.endswith('.png'):
            return 'image/png'
        elif path.endswith('.css'):
            return 'text/css'
        elif path.endswith('.ogg'):
            return 'audio/ogg'
        else:
            return 'application/octet-stream'
    def serve_content(self, path):
        self.send_response(200)
        self.send_header('Content-type', 'audio/ogg')
        self.end_headers()
        print 'Starting to serve file...'
        rb.get_content(path, self.wfile)
        print 'Finished.'
        self.wfile.close()
    def serve_library(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(library_repr)
        self.wfile.close()
    def serve_static_content(self, path):
        try:
            with open('resources' + path) as f:
                self.send_response(200)
                self.send_header('Content-type', self.get_content_type(path))
                self.end_headers()
                self.wfile.write(f.read())
                self.wfile.close()
        except IOError:
            self.send_error(404, 'File not found: %s' % (path,))

def main():
    global library_contents, library_repr
    print "Loading library..."
    library_contents = rb.get_library_contents()
    library_repr = json.dumps(library_contents, ensure_ascii=False)
    server = BaseHTTPServer.HTTPServer(('', 8080), ZeyaHandler)
    try:
        print "Ready to serve!"
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()

if __name__ == '__main__':
    rb = RhythmboxBackend()
    main()
