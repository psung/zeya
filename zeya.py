#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Phil Sung, Samson Yeung
#
# This file is part of Zeya.
#
# Zeya is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# Zeya is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Zeya. If not, see <http://www.gnu.org/licenses/>.


# Zeya - a web music server.

# Work with python2.5
from __future__ import with_statement

import BaseHTTPServer

import getopt
import urllib
import sys
try:
    import json
    json.dumps
except (ImportError, AttributeError):
    import simplejson as json

DEFAULT_PORT = 8080
DEFAULT_BACKEND = "rhythmbox"

# Store the state of the library.
library_contents = []
library_repr = ""

valid_backends = ['rhythmbox', 'dir']

class BadArgsError(Exception):
    """
    Error due to incorrect command-line invocation of this program.
    """
    def __init__(self, message):
        self.error_message = message
    def __str__(self):
        return "Error: %s" % (self.error_message,)

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
        backend.get_content(path, self.wfile)
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
            # TODO - fix this by reading from sys.argv[0] so resources is found properly
            # path already has a leading '/' in front of it.
            with open('resources' + path) as f:
                self.send_response(200)
                self.send_header('Content-type', self.get_content_type(path))
                self.end_headers()
                self.wfile.write(f.read())
                self.wfile.close()
        except IOError:
            self.send_error(404, 'File not found: %s' % (path,))

def getOptions():
    """
    Parse the arguments and return a tuple (show_help, backend, port), or raise
    BadArgsError if the invocation was not valid.

    show_help: whether user requested help information
    backend: string containing backend to use (only supported value right now
             is "rhythmbox")
    port: port number to listen on
    """
    help_msg = False
    port = DEFAULT_PORT
    backend_type = DEFAULT_BACKEND
    path = None
    try:
        opts, file_list = getopt.getopt(sys.argv[1:], "hp:",
                                        ["help", "backend=", "port=", "path="])
    except getopt.GetoptError:
        raise BadArgsError("Unsupported options")
    for flag, value in opts:
        if flag in ("-h", "--help"):
            help_msg = True
        if flag in ("--backend"):
            backend_type = value
            if backend_type not in valid_backends:
                raise BadArgsError("Unsupported backend type")
        if flag in ("--path"):
            path = value
        if flag in ("-p", "--port"):
            try:
                port = int(value)
            except ValueError:
                raise BadArgsError("Invalid port setting %r" % (value,))
    if backend_type == 'directory' and path is None:
        raise BadArgsError("Directory backend needs a path (--path)")
    return (help_msg, backend_type, port, path)

def usage():
    print "Usage: zeya.py [-h|--help] [--backend=rhythmbox] [--port] [--path]"

def main(port):
    global library_contents, library_repr
    # Read the library.
    print "Loading library..."
    library_contents = backend.get_library_contents()
    library_repr = json.dumps(library_contents, ensure_ascii=False)
    server = BaseHTTPServer.HTTPServer(('', port), ZeyaHandler)
    print "Listening on port %d" % (port,)
    # Start up a web server.
    print "Ready to serve!"
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == '__main__':
    try:
        (show_help, backend_type, port, path) = getOptions()
    except BadArgsError, e:
        print e
        usage()
        sys.exit(1)
    if show_help:
        usage()
        sys.exit(0)
    print "Using %r backend" % (backend_type,)
    if backend_type == "rhythmbox":
        # Import the backend modules conditionally, so users don't have to
        # install dependencies unless they are actually used.
        from rhythmbox import RhythmboxBackend
        backend = RhythmboxBackend()
    elif backend_type == 'dir':
        from directory import DirectoryBackend
        backend = DirectoryBackend(path)
    main(port)
