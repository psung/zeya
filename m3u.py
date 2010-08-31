# -*- coding: utf-8 -*-
#
# Copyright (C) 2009, 2010 Amit Saha
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

# m3u backend

import os.path
import sys

from backends import LibraryBackend
from backends import extract_metadata

class M3uPlaylist(object):
    def __init__(self, filename, file_obj):
        """
        Parses data from FILE_OBJ (a file-like object), which contains a
        playlist in M3U format.
        """
        self._filename = filename
        self._filenames = []
        for line in file_obj:
            if not line.startswith('#'):
                rel_path = line.rstrip('\r\n')
                abs_path = os.path.normpath(os.path.join(
                        os.getcwd(), os.path.dirname(filename), rel_path))
                self._filenames.append(abs_path)

    def get_title(self):
        """
        Returns the title of this playlist.
        """
        # M3U doesn't provide for specifying the title. Just use the basename
        # of the file as the title of the playlist.
        return os.path.basename(self._filename).decode('UTF-8')

    def get_filenames(self):
        """
        Returns the sequence of filenames represented by the playlist.
        """
        return self._filenames

class M3uBackend(LibraryBackend):
    def __init__(self, file_path=None):
        self.m3u_file = file_path
        # Check if the file exists so that we can fail-fast if necessary.
        if not os.path.exists(self.m3u_file):
            print "Error: no m3u file was found at %r." % (self.m3u_file,)
            print "Please check the m3u file location, or try --backend=dir instead."
            sys.exit(1)

    def get_library_contents(self):
        # Sequence of dicts containing the metadata for all the songs.
        library = []
        # Dict mapping keys to the original filenames.
        self.file_list = {}
        next_index = 0
        try:
            playlist = M3uPlaylist(self.m3u_file, open(self.m3u_file))
            for filename in playlist.get_filenames():
                try:
                    metadata = extract_metadata(os.path.abspath(filename))
                except ValueError:
                    continue
                metadata['key'] = next_index
                self.file_list[next_index] = filename
                library.append(metadata)
                next_index = next_index + 1
            return library
        except IOError:
            print "Error: could not read the specified playlist (%r)" \
                % (self.m3u_file,)
            sys.exit(1)

    def get_filename_from_key(self, key):
        return self.file_list[int(key)]
