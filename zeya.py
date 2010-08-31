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

import base64
import crypt
import getopt
import os
import re
import socket
import sys
import tempfile
import traceback
import urllib
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

import backends
import decoders
import options

b64dict = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
auth = 'Authorization'
no_auth_rval = \
"""
<!DOCTYPE html>
    <HTML>
        <HEAD>
            <TITLE>Error</TITLE>
            <meta http-equiv="Content-Type" content="text/html;charset=utf-8"/>
        </HEAD>
        <BODY><H1>401 Unauthorized.</H1></BODY>
    </HTML>
"""

# Auth types
NO_AUTH = None
BASIC_AUTH = 'basic'

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
    def server_bind(self):
        HTTPServer.server_bind(self)

class IPV6ThreadedHTTPServer(ThreadedHTTPServer):
    # Allow IPv6 connections if possible.
    if socket.has_ipv6:
        address_family = socket.AF_INET6

    def server_bind(self):
        if socket.has_ipv6:
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        ThreadedHTTPServer.server_bind(self)

user_pass_regexp = re.compile('([^:]):(.*)$')
def split_user_pass(data):
    """ Split the given data into user and password. """
    return user_pass_regexp.search(data).groups()

def ZeyaHandler(backend, library_repr, resource_basedir, bitrate,
                auth_type=None, auth_data=None):
    """
    Wrapper around the actual HTTP request handler implementation class. We
    need to create a closure so that the inner class can receive the following
    data:

    Backend to use.
    Library data.
    Base directory for resources.
    Bitrate for encoding.
    Authentication data.
    """

    class ZeyaHandlerImpl(BaseHTTPRequestHandler, object):
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

            # TODO: send error 500 when we encounter an error during the
            # decoding phase. This is needed for reliable client-side error
            # dialogs.
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
                output_file.seek(0)
                try:
                    backends.copy_output_with_shaping(
                        output_file.fileno(), self.wfile, bitrate)
                except socket.error:
                    pass
                output_file.close()
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

    class ZeyaBasicAuthHandlerImpl(ZeyaHandlerImpl):
        def __init__(self, *args, **kwargs):
            self.auth_regexp = re.compile('Basic ([%s[]*)' % b64dict)
            super(ZeyaBasicAuthHandlerImpl, self).__init__(*args, **kwargs)

        def send_no_auth(self):
            """
            Send an unauthorized required page.
            """
            self.send_response(401)
            self.send_header('Content-type', 'text/html')
            self.send_header('Content-Length', str(len(no_auth_rval)))
            self.send_header('WWW-Authenticate', 'Basic realm="Zeya Secure"')
            self.end_headers()
            self.wfile.write(no_auth_rval)

        def authorized(self):
            """
            Return true if self.headers has valid authentication information.
            """
            if auth in self.headers and self.auth_regexp.match(self.headers[auth]):
                encoded_auth = self.auth_regexp.sub('\\1', self.headers[auth])
                decoded_auth = base64.b64decode(encoded_auth)
                client_user, client_pass = split_user_pass(decoded_auth)
                if client_user in auth_data:
                    client_crypt_pass = crypt.crypt(\
                            client_pass, auth_data[client_user][:2])
                    return client_crypt_pass == auth_data[client_user]
            return False

        def do_GET(self):
            """
            Handle a GET request, sending an authentication required header if
            not authenticated.
            """
            if self.authorized():
                ZeyaHandlerImpl.do_GET(self)
            else:
                self.send_no_auth()

    if auth_type == BASIC_AUTH:
        print 'Using Basic Auth Handler...'
        return ZeyaBasicAuthHandlerImpl
    return ZeyaHandlerImpl

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
    elif backend_type == 'playlist':
        if path.lower().endswith('m3u'):
            from m3u import M3uBackend
            return M3uBackend(path)
        else:
            from pls import PlsBackend
            return PlsBackend(path)
    else:
        raise ValueError("Invalid backend %r" % (backend_type,))

def run_server(backend, bind_address, port, bitrate, basic_auth_file=None):
    # Read the library.
    print "Loading library..."

    library_contents = backend.get_library_contents()
    if not library_contents:
        print "Warning: no tracks were found. Check that you've specified " \
            + "the right backend/path."
    # Filter out songs that we won't be able to decode.
    filtered_library_contents = \
        [ s for s in library_contents \
              if decoders.has_decoder(backend.get_filename_from_key(s['key'])) ]
    if not filtered_library_contents and library_contents:
        print "Warning: no playable tracks were found. You may need to " \
            "install one or more decoders."

    try:
        playlists = backend.get_playlists()
    except NotImplementedError:
        playlists = None

    output = { 'library': filtered_library_contents,
               'playlists': playlists }

    library_repr = json.dumps(output, ensure_ascii=False)
    basedir = os.path.abspath(os.path.dirname(os.path.realpath(sys.argv[0])))

    auth_data = None
    if basic_auth_file is not None:
        auth_data = {}
        for line in basic_auth_file:
            s_user, s_pass = split_user_pass(line.rstrip())
            auth_data[s_user] = s_pass
    zeya_handler = ZeyaHandler(backend,
                               library_repr,
                               os.path.join(basedir, 'resources'),
                               bitrate,
                               auth_type=NO_AUTH if basic_auth_file is None else BASIC_AUTH,
                               auth_data=auth_data,
                               )
    try:
        server = IPV6ThreadedHTTPServer((bind_address, port), zeya_handler)
    except socket.error:
        # One possible failure mode (among many others...) is that IPv6 is
        # disabled, which manifests as a socket.error. If this happens, attempt
        # to bind only on IPv4.
        server = ThreadedHTTPServer((bind_address, port), zeya_handler)

    if bind_address != '':
        print "Binding to address %s" % bind_address

    print "Listening on port %d" % (port,)
    # Start up a web server.
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == '__main__':
    try:
        (show_help, backend_type, bitrate, bind_address, port, path, basic_auth_file) = \
            options.get_options(sys.argv[1:])
    except options.BadArgsError, e:
        print e
        options.print_usage()
        sys.exit(1)
    if show_help:
        options.print_usage()
        sys.exit(0)
    print "Using %r backend." % (backend_type,)
    try:
        backend = get_backend(backend_type)
    except IOError, e:
        print e
        sys.exit(1)
    run_server(backend, bind_address, port, bitrate, basic_auth_file)
