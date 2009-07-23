#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Phil Sung
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
except AttributeError:
    import simplejson as json

from rhythmbox import RhythmboxBackend
from directory import SingleRecursedDir

# Store the state of the library.
library_contents = []
library_repr = ""

valid_backends = ['rhythmbox', 'directory']

class BadArgsError(Exception):
    """
    Error due to incorrect command-line invocation of this program.
    """
    def __init__(self):
        pass

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
    Parse the arguments and return a tuple (show_help, backend), or raise
    BadArgsError if the invocation was not valid.

    show_help: whether user requested help information
    backend: string containing backend to use (only supported value right now
             is "rhythmbox"
    """
    help_msg = False
    backend_type = "rhythmbox"
    try:
        opts, file_list = getopt.getopt(sys.argv[1:], "h",
                                        ["help", "backend="])
    except getopt.GetoptError:
        raise BadArgsError()
    for flag, value in opts:
        if flag in ("-h", "--help"):
            help_msg = True
        if flag in ("--backend"):
            backend_type = value
        if backend_type not in valid_backends:
            raise BadArgsError()
    return (help_msg, backend_type)

def usage():
    print "Usage: zeya.py [-h|--help] [--backend=rhythmbox]"

def main():
    global library_contents, library_repr
    # Read the library.
    print "Loading library..."
    library_contents = backend.get_library_contents()
    library_repr = json.dumps(library_contents, ensure_ascii=False)
    # TODO: allow setting port via --port flag.
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
    try:
        (show_help, backend_type) = getOptions()
    except BadArgsError:
        usage()
        sys.exit(1)
    if show_help:
        usage()
        sys.exit(0)
    print "Using %r backend" % (backend_type,)
    if backend_type == "rhythmbox":
        backend = RhythmboxBackend()
    elif backend_type == 'directory':
        backend = SingleRecursedDir('/vid/fragmede/music/pink/')
    main()
