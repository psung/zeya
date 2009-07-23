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

def filename_to_stream(filename, out_stream):
    try:
        # Obtain the path to the original file.
        print "Handing request for %s" % (filename,)
        if filename.lower().endswith('.flac'):
            decode_command = ["/usr/bin/flac", "-d", "-c", "--totally-silent", filename]
        elif filename.lower().endswith('.mp3'):
            #decode_command = ["/usr/bin/lame", "-S", "--decode", filename, "-"]
            decode_command = ["/usr/bin/mpg321", "-s", "-q", filename]
        elif filename.lower().endswith('.ogg'):
            decode_command = ["/usr/bin/oggdec", "-Q", "-o", "-", filename]
        else:
            print "No decode command found for %s" % (filename,)
        # Pipe the decode command into the encode command.
        p1 = subprocess.Popen(decode_command, stdout=subprocess.PIPE)
        p2 = subprocess.Popen(["/usr/bin/oggenc", "-r", "-Q", "-b", "64", "-"],
                              stdin=p1.stdout, stdout=out_stream)
    except KeyError, ValueError:
        print "Received invalid request for %r" % (key,)

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

    def get_content(self, key, out_stream):
        """
        Retrieve the file data associated with the specified key and write an
        audio/ogg encoded version to out_stream.
        """
        filename_to_stream(self.get_filename_from_key(key), out_stream)

    def get_filename_from_key(self, key):
        raise NotImplementedError()
