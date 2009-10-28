#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Phil Sung, Samson Yeung, Romain Francoise
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

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn

import getopt
import urllib
import os
import socket
import sys
import tempfile
import traceback
import zlib
try:
    from urlparse import parse_qs
except: # (ImportError, AttributeError):
    from cgi import parse_qs

try:
    import json
    json.dumps
except (ImportError, AttributeError):
    import simplejson as json

import decoders

DEFAULT_PORT = 8080
DEFAULT_BITRATE = 64 #kbits/s
DEFAULT_BACKEND = "rhythmbox"

valid_backends = ['rhythmbox', 'dir']

class BadArgsError(Exception):
    """
    Error due to incorrect command-line invocation of this program.
    """
    def __init__(self, message):
        self.error_message = message
    def __str__(self):
        return "Error: %s" % (self.error_message,)

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """
    HTTP Server that handles requests in separate threads.
    """
    # Allow IPv6 connections if possible.
    if socket.has_ipv6:
        address_family = socket.AF_INET6

def ZeyaHandler(backend, library_repr, resource_basedir, bitrate):
    """
    Wrapper around the actual HTTP request handler implementation class. We
    need to create a closure so that the inner class can receive the following
    data:

    Backend to use.
    Library data.
    Base directory for resources.
    Bitrate for encoding.
    """

    class ZeyaHandlerImpl(BaseHTTPRequestHandler):
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
            # http://host/getcontent?key=N yields an Ogg stream of the file
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
            elif path.endswith('.gif'):
                return 'image/gif'
            elif path.endswith('.css'):
                return 'text/css'
            elif path.endswith('.js'):
                return 'text/javascript'
            elif path.endswith('.ogg'):
                return 'audio/ogg'
            else:
                print ("Warning: couldn't identify content-type for %r, "
                       + "serving as application/octet-stream") % (path,)
                return 'application/octet-stream'
        def serve_content(self, query):
            """
            Serve an audio stream (audio/ogg).
            """
            # The query is of the form key=N or key=N&buffered=true.
            args = parse_qs(query)
            key = args['key'][0] if args.has_key('key') else ''
            # If buffering is activated, encode the entire file and serve the
            # Content-Length header. This increases song load latency because
            # we can't serve any of the file until we've finished encoding the
            # whole thing. However, Chrome needs the Content-Length header to
            # accompany audio data.
            buffered = args['buffered'][0] if args.has_key('buffered') else ''

            self.send_response(200)
            self.send_header('Content-type', 'audio/ogg')
            if buffered:
                # Complete the transcode and write to a temporary file.
                # Determine its length and serve the Content-Length header.
                output_file = tempfile.TemporaryFile()
                backend.get_content(key, output_file, bitrate, buffered=True)
                output_file.seek(0)
                data = output_file.read()
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                # Don't determine the Content-Length. Just stream to the client
                # on the fly.
                self.end_headers()
                backend.get_content(key, self.wfile, bitrate)
            self.wfile.close()

        def send_data(self, ctype, data):
            """
            Send data to the client.

            Use deflate compression if client headers indicate that the
            other end supports it and if it's appropriate for this
            content-type.
            """
            compress_data = \
                (ctype.startswith('text/')
                 and 'Accept-Encoding' in self.headers
                 and 'deflate' in self.headers['Accept-Encoding'].split(','))
            self.send_response(200)
            if compress_data:
                data = zlib.compress(data)
                self.send_header('Content-Encoding', 'deflate')
                self.send_header('Vary', 'Accept-Encoding')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Content-Type', ctype)
            self.end_headers()
            self.wfile.write(data)
            self.wfile.close()

        def serve_library(self):
            """
            Serve a representation of the library.
            """
            self.send_data('text/html', library_repr.encode('utf-8'))

        def serve_static_content(self, path):
            """
            Serve static content from the resources/ directory.
            """
            try:
                # path already has a leading '/' in front of it. Strip it.
                full_path = os.path.join(resource_basedir, path[1:])
                # Ensure that the basedir we use for security checks ends in '/'.
                effective_basedir = os.path.join(resource_basedir, '')
                # Prevent directory traversal attacks. Canonicalize the
                # filename we're going to open and verify that it's inside the
                # resource directory.
                if not os.path.abspath(full_path).startswith(effective_basedir):
                    self.send_error(404, 'File not found: %s' % (path,))
                    return
                with open(full_path) as f:
                    self.send_data(self.get_content_type(path), f.read())
            except IOError:
                traceback.print_exc()
                self.send_error(404, 'File not found: %s' % (path,))

    return ZeyaHandlerImpl

def get_options():
    """
    Parse the arguments and return a tuple (show_help, backend, bitrate, port,
    path), or raise BadArgsError if the invocation was not valid.

    show_help: whether user requested help information
    backend: string indicating backend to use
    bitrate: bitrate for encoded streams (kbits/sec)
    port: port number to listen on
    path: path from which to read music files (for "dir" backend only)
    """
    help_msg = False
    port = DEFAULT_PORT
    backend_type = DEFAULT_BACKEND
    bitrate = DEFAULT_BITRATE
    # This is set to False if --backend is explicitly set
    is_backend_default_value = True
    path = None
    try:
        opts, file_list = getopt.getopt(sys.argv[1:], "b:hp:",
                                        ["help", "backend=", "bitrate=",
                                         "port=", "path="])
    except getopt.GetoptError, e:
        raise BadArgsError(e.msg)
    for flag, value in opts:
        if flag in ("-h", "--help"):
            help_msg = True
        if flag in ("--backend",):
            is_backend_default_value = False
            backend_type = value
            if backend_type not in valid_backends:
                raise BadArgsError("Unsupported backend type %r"
                                   % (backend_type,))
        if flag in ("-b", "--bitrate"):
            try:
                bitrate = int(value)
                if bitrate <= 0:
                    raise ValueError()
            except ValueError:
                raise BadArgsError("Invalid bitrate setting %r" % (value,))
        if flag in ("--path",):
            path = value
        if flag in ("-p", "--port"):
            try:
                port = int(value)
            except ValueError:
                raise BadArgsError("Invalid port setting %r" % (value,))
    if backend_type == 'dir' and path is None:
        raise BadArgsError("'dir' backend requires a path (--path=...)")
    # If --backend is not set explicitly, --path=... implies --backend=dir
    if path is not None and is_backend_default_value:
        backend_type = 'dir'
    return (help_msg, backend_type, bitrate, port, path)

def usage():
    print "Usage: %s [OPTIONS]" % (os.path.basename(sys.argv[0]),)
    print """
Options:

  -h, --help
      Display this help message.

  --backend=BACKEND
      Specify the backend to use. Acceptable values:
        rhythmbox: (default) read from current user's Rhythmbox library
        dir: read a directory's contents, recursively; see --path

  --path=PATH
      Directory in which to look for music. Use with --backend=dir.

  -b, --bitrate=N
      Specify the bitrate for output streams, in kbits/sec. (default: 64)

  -p, --port=PORT
      Listen for requests on the specified port. (default: 8080)"""

def get_backend(backend_type):
    """
    Return a backend object of the requested type.

    backend_type: string giving the backend type to use.
    """
    if backend_type == "rhythmbox":
        # Import the backend modules conditionally, so users don't have to
        # install dependencies unless they are actually used.
        from rhythmbox import RhythmboxBackend
        return RhythmboxBackend()
    elif backend_type == 'dir':
        from directory import DirectoryBackend
        return DirectoryBackend(path)
    else:
        raise ValueError("Invalid backend %r" % (backend_type,))

def run_server(backend, port, bitrate):
    # Read the library.
    print "Loading library..."
    library_contents = backend.get_library_contents()
    # Filter out songs that we won't be able to decode.
    library_contents = \
        [ s for s in library_contents \
              if decoders.has_decoder(backend.get_filename_from_key(s['key'])) ]
    library_repr = json.dumps(library_contents, ensure_ascii=False)
    basedir = os.path.abspath(os.path.dirname(os.path.realpath(sys.argv[0])))
    server = ThreadedHTTPServer(
        ('', port),
        ZeyaHandler(backend, library_repr, os.path.join(basedir, 'resources'),
                    bitrate))
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
        (show_help, backend_type, bitrate, port, path) = get_options()
    except BadArgsError, e:
        print e
        usage()
        sys.exit(1)
    if show_help:
        usage()
        sys.exit(0)
    backend = get_backend(backend_type)
    print "Using %r backend" % (backend_type,)
    run_server(backend, port, bitrate)
