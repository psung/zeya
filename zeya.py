#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Web music server.

import BaseHTTPServer

import json
import urllib

from rhythmbox import RhythmboxBackend

library_contents = []
library_repr = ""

# TODO: support a multithreaded server.

class ZeyaHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """
    Web server request handler.
    """
    def do_GET(self):
        """
        Handle a GET request.
        """
        # http://host/ yields the library main page.
        if self.path == '/':
            self.serve_static_content('/library.html')
        # http://host/getlibrary returns a representation of the music
        # collection.
        elif self.path == '/getlibrary':
            self.serve_library()
        # http://host/getcontent?key yields an Ogg stream of the file
        # associated with the specified key.
        elif self.path.startswith('/getcontent?'):
            self.serve_content(urllib.unquote(self.path[12:]))
        # All other paths are assumed to be static content.
        # http://host/foo is mapped to resources/foo.
        else:
            self.serve_static_content(self.path)
    def get_content_type(self, path):
        """
        Return the MIME type associated with the given path.
        """
        path = path.lower()
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
        """
        Serve an audio stream (audio/ogg).
        """
        self.send_response(200)
        self.send_header('Content-type', 'audio/ogg')
        self.end_headers()
        rb.get_content(path, self.wfile)
        self.wfile.close()
    def serve_library(self):
        """
        Serve a representation of the library.

        We take the output of backend.get_library_contents(), dump it as JSON,
        and give that to the client.
        """
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(library_repr.encode('utf-8'))
        self.wfile.close()
    def serve_static_content(self, path):
        """
        Serve static content from the resources/ directory.
        """
        try:
            # path already has a leading '/' in front of it.
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
    # Read the library.
    print "Loading library..."
    library_contents = rb.get_library_contents()
    library_repr = json.dumps(library_contents, ensure_ascii=False)
    server = BaseHTTPServer.HTTPServer(('', 8080), ZeyaHandler)
    # Start up a web server.
    print "Ready to serve!"
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == '__main__':
    rb = RhythmboxBackend()
    main()
