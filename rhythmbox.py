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


# Rhythmbox backend.

import os
import subprocess
import urllib

from backend import LibraryBackend

from xml.parsers import expat

# Path to XML file containing Rhythmbox library
RB_DBFILE = '~/.local/share/rhythmbox/rhythmdb.xml'

class RhythmboxDbHandler():
    """
    Parser for Rhythmbox XML files.
    """
    def __init__(self):
        # List containing library metadata (see backend.LibraryBackend for full
        # description).
        self.contents = []
        # Map the keys (ints) to the original file paths.
        self.filelist = []
        self.in_song = False     # Are we inside a <entry type="song"> ?
        self.in_title = False    # Are we inside a <title> ?
        self.in_artist = False   # Are we inside a <artist> ?
        self.in_album = False    # Are we inside a <album> ?
        self.in_location = False # Are we inside a <location> ?
    def startElement(self, name, attrs):
        # Within each <entry type="song">, record the attributes.
        if name == 'entry' and attrs['type'] == 'song':
            self.in_song = True
            self.current_title = ''
            self.current_artist = ''
            self.current_album = ''
            self.current_location = ''
        if name == 'title':
            self.in_title = True
        if name == 'artist':
            self.in_artist = True
        if name == 'album':
            self.in_album = True
        if name == 'location':
            self.in_location = True
    def endElement(self, name):
        if self.in_song and name == 'entry':
            # When a <entry> is closed, construct a new record for the
            # corresponding file.
            self.in_song = False
            if self.current_location.startswith('file://'):
                # The <location> field contains a URL-encoded version of the
                # file path. Use the decoded version in all of our data
                # structures.
                next_index = len(self.filelist)
                path = urllib.unquote(self.current_location[7:])
                self.contents.append(
                    {'title':self.current_title, 'artist':self.current_artist,
                     'album':self.current_album, 'key':next_index})
                self.filelist.append(path)
        if self.in_title and name == 'title':
            self.in_title = False
        if self.in_artist and name == 'artist':
            self.in_artist = False
        if self.in_album and name == 'album':
            self.in_album = False
        if self.in_location and name == 'location':
            self.in_location = False
    def characters(self, ch):
        if self.in_song:
            # Record any text we come across and append it to the Title,
            # Artist, Album, or Location fields as appropriate.
            if self.in_title:
                self.current_title += ch
            if self.in_artist:
                self.current_artist += ch
            if self.in_album:
                self.current_album += ch
            if self.in_location:
                self.current_location += ch
    def getFiles(self):
        return self.filelist
    def getContents(self):
        return self.contents

class RhythmboxBackend(LibraryBackend):
    """
    Object that controls access to a Rhythmbox music collection.
    """
    def __init__(self):
        self._files = set()
        self._contents = None
    def get_library_contents(self):
        # Memoize self._contents and self._files.
        if not self._contents:
            handler = RhythmboxDbHandler()
            p = expat.ParserCreate()
            p.StartElementHandler = handler.startElement
            p.EndElementHandler = handler.endElement
            p.CharacterDataHandler = handler.characters
            p.ParseFile(open(os.path.expanduser(RB_DBFILE)))
            self._contents = handler.getContents()
            self._files = handler.getFiles()
            # Sort the items by filename.
            self._contents.sort(key = (lambda item: self._files[item['key']]))
        return self._contents
    def get_filename_from_key(self, key):
        return self._files[int(key)]
