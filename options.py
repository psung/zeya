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


# Code for parsing command-line options.

import getopt
import os
import sys

DEFAULT_PORT = 8080
DEFAULT_BITRATE = 64 #kbits/s
DEFAULT_BACKEND = 'dir'

valid_backends = ['rhythmbox', 'dir', 'playlist']

class BadArgsError(Exception):
    """
    Error due to incorrect command-line invocation of this program.
    """
    def __init__(self, message):
        self.error_message = message
    def __str__(self):
        return "Error: %s" % (self.error_message,)

def get_options(remaining_args):
    """
    Parse the arguments and return a tuple (show_help, backend, bitrate, port,
    path, basic_auth_file), or raise BadArgsError if the invocation was not
    valid.

    show_help: whether user requested help information
    backend: string indicating backend to use
    bitrate: bitrate for encoded streams (kbits/sec)
    bind_address: IPv4/IPv6 address to bind to
    port: port number to listen on
    path: path from which to read music files (for "dir" and "playlist" backends only)
    basic_auth_file: file handle from which to read basic auth config, or None.
    """
    # TODO: make this return a more useful data structure, e.g. a dict or an
    # object. Returning a huge tuple is kind of unwieldy.
    help_msg = False
    bind_address = ''
    port = DEFAULT_PORT
    backend_type = DEFAULT_BACKEND
    bitrate = DEFAULT_BITRATE
    path = None
    basic_auth_file = None
    try:
        opts, file_list = getopt.getopt(
            remaining_args, "b:hp:",
            ["help", "backend=", "bitrate=", "bind_address=", "port=", "path=",
             "basic_auth_file="])
    except getopt.GetoptError, e:
        raise BadArgsError(e.msg)
    for flag, value in opts:
        if flag in ("-h", "--help"):
            help_msg = True
        if flag in ("--backend",):
            backend_type = value
            if backend_type not in valid_backends:
                raise BadArgsError("Unsupported backend type %r"
                                   % (backend_type,))
        if flag in ("--basic_auth_file",):
            try:
                basic_auth_file = open(value, 'r')
            except:
                raise BadArgsError("Could not read auth file %s" % (value,))
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
        if flag in ("--bind_address",):
            bind_address = value
    if backend_type not in ('dir', 'playlist') and path is not None:
        print "Warning: --path was set but is ignored for --backend=%s" \
            % (backend_type,)
    if backend_type == 'dir' and path is None:
        path = os.getcwd()
    if backend_type == 'playlist' and path is None:
        raise BadArgsError("Specify --path for playlist backend")
    return (help_msg, backend_type, bitrate, bind_address, port, path, basic_auth_file)

def print_usage():
    print "Usage: %s [OPTIONS]" % (os.path.basename(sys.argv[0]),)
    print """
Options:

  -h, --help
      Display this help message.

  --backend=BACKEND
      Specify the backend to use. Acceptable values:
        dir: (default) read a directory's contents recursively; see --path
        rhythmbox: read from current user's Rhythmbox library
        playlist: read from the playlist (m3u) file specified by --path

  --path=PATH
      For --backend=dir, the directory in which to look for music. (Default: ./)
      For --backend=playlist, the absolute path to a .m3u file, or a .pls file

  -b, --bitrate=N
      Specify the bitrate for output streams, in kbits/sec. (default: 64)

  --bindaddress=bindaddress
      Specify the IPv4/IPv6 address to bind to (default: bind to everything)

  -p, --port=PORT
      Listen for requests on the specified port. (default: 8080)

  --basic_auth_file=FILENAME
      Require basic HTTP authentication and only allow users named in the
      specified file. The file should be in 'htpasswd' format."""
