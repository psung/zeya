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

# pls backend

import os.path
import sys
import urllib

from backends import LibraryBackend
from backends import extract_metadata

class PlsPlaylist(object):
    def __init__(self, filename, file_obj):
        """
        Parses data from FILE_OBJ (a file-like object), which contains a
        playlist in PLS format. FILENAME is the path of the input playlist file
        (used for evaluating the absolute filename of each file).
        """
        self._title = "(Untitled)"
        self._filenames = []
        for line_number, line in enumerate(file_obj):
            if line.startswith('X-GNOME-Title='):
                self._title = line[14:].rstrip('\r\n').decode('UTF-8')
            if line.startswith('File'):
                try:
                    # Parse the filename from the line.
                    path = line.rstrip('\r\n')[line.index("=") + 1:]
                    if path.startswith("file:///"):
                        # Is this (which leaves a leading '/') going to be
                        # problematic for Windows systems)?
                        abs_path = urllib.unquote(path[7:])
                    else:
                        abs_path = os.path.normpath(
                            os.path.join(os.getcwd(), os.path.dirname(filename), path))
                    self._filenames.append(abs_path)
                except ValueError:
                    print "Warning: malformed line in %s:%d: %r" % \
                        (filename, line_number+1, line.strip())
                    continue

    def get_title(self):
        """
        Returns the title of this playlist.
        """
        return self._title

    def get_filenames(self):
        """
        Returns the sequence of filenames represented by the playlist.
        """
        return self._filenames

class PlsBackend(LibraryBackend):
    def __init__(self, file_path=None):
        self.pls_file = file_path
        # Check if the file exists so that we can fail-fast if necessary.
        if not os.path.exists(self.pls_file):
            print "Error: no pls file was found at %r." % (self.pls_file,)
            print "Please check the pls file location, or try --backend=dir instead."
            sys.exit(1)

    def get_library_contents(self):
        # Sequence of dicts containing the metadata for all the songs.
        library = []
        # Dict mapping keys to the original filenames.
        self.file_list = {}
        next_index = 0
        try:
            playlist = PlsPlaylist(self.pls_file, open(self.pls_file))
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
                % (self.pls_file,)
            sys.exit(1)

    def get_filename_from_key(self, key):
        return self.file_list[int(key)]
