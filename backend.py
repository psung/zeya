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

import subprocess

import decoders

class StreamGenerationError(Exception):
    """
    Indicates an error generating a stream for the requested file.
    """
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

def filename_to_stream(filename, out_stream, buffered = False):
    print "Handling request for %s" % (filename,)
    try:
        decode_command = decoders.getDecoder(filename)
    except KeyError:
        raise StreamGenerationError(
            "Couldn't play specified format: %r" % (filename,))
    encode_command = ["/usr/bin/oggenc", "-r", "-Q", "-b", "64", "-"]
    # Pipe the decode command into the encode command.
    p1 = subprocess.Popen(decode_command, stdout=subprocess.PIPE)
    if buffered:
        # Read the entire output and then write it to the output stream.
        p2 = subprocess.Popen(encode_command, stdin=p1.stdout, stdout=subprocess.PIPE)
        out_stream.write(p2.stdout.read())
    else:
        # Stream the encoder output directly.
        p2 = subprocess.Popen(encode_command, stdin=p1.stdout, stdout=out_stream)

# This interface is implemented by all library backends.

class LibraryBackend():
    """
    Object that controls access to a collection of music files.
    """
    def get_library_contents(self):
        """
        Return a list of the available files.

        The return value should be of the form

          [ {'key': ..., 'title': ..., 'artist': ..., 'album': ...},
            ... ]

        where each entry represents one file. The values coresponding to
        'title', 'artist', and 'album' are strings or unicode strings giving
        the song attributes. The value corresponding to 'key' may be passed to
        self.write_content in order to obtain the data for a particular file.

        The items will be displayed to the user in the order that they appear
        here.
        """
        raise NotImplementedError()

    def get_content(self, key, out_stream, buffered = False):
        """
        Retrieve the file data associated with the specified key and write an
        audio/ogg encoded version to out_stream.
        """
        # This is a convenience implementation of this method.
        try:
            filename = self.get_filename_from_key(key)
        except KeyError:
            print "Received invalid request for key %r" % (key,)
        try:
            filename_to_stream(filename, out_stream, buffered)
        except StreamGenerationError, e:
            print "ERROR. %s" % (e,)

    def get_filename_from_key(self, key):
        # Retrieve the filename that 'key' is backed by. This is not part of
        # the public API, but is used in the default implementation of
        # get_content.
        #
        # Raise KeyError if the key is not valid.
        raise NotImplementedError()
