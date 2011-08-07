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
import os.path
import subprocess
import sys
import urllib

from backends import LibraryBackend
from common import tokenize_filename

from xml.parsers import expat

# Path to XML file containing Rhythmbox library
RB_DBFILE = '~/.local/share/rhythmbox/rhythmdb.xml'
# Path to XML file containing Rhythmbox playlists
RB_PLAYLISTFILE = '~/.local/share/rhythmbox/playlists.xml'

class RhythmboxDbHandler():
    """
    Parser for Rhythmbox XML files.
    """
    def __init__(self):
        # List containing library metadata (see backends.LibraryBackend for
        # full description).
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
                path = urllib.unquote(str(self.current_location))[7:]
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

class RhythmboxPlaylistsHandler():
    """
    Parser for Rhythmbox playlist XML files.
    """
    def __init__(self, file_list):
        # Construct a map of filename to key so we can represent playlists as
        # lists of keys.
        self.file_to_key_map = {}
        for key, filename in enumerate(file_list):
            self.file_to_key_map[filename] = key

        self.in_playlist = False
        self.in_location = False
        # List containing library metadata (see backends.LibraryBackend for
        # full description).
        self.playlists = []
        # While parsing each playlist, remember its name and the list of the
        # paths we encounter. When we actually populate the self.playlists
        # object, we'll map those paths back to keys.
        self.current_playlist_name = ""
        self.current_playlist_items = None
    def startElement(self, name, attrs):
        # Within each <entry type="song">, record the attributes.
        if name == 'playlist' and attrs['type'] == 'static':
            self.in_playlist = True
            self.current_playlist_items = []
            self.current_playlist_name = attrs['name']
        if name == 'location':
            self.in_location = True
            self.current_location = ''
    def endElement(self, name):
        if self.in_playlist and name == 'playlist':
            self.in_playlist = False
            playlist_keys = []
            for item_path in self.current_playlist_items:
                if item_path in self.file_to_key_map:
                    playlist_keys.append(self.file_to_key_map[item_path])
                else:
                    print ("Warning: encountered a playlist item that is " +
                           "not in the global database.\n  Path: %r, " +
                           "Playlist: %r.") % \
                           (item_path, self.current_playlist_name)
            self.playlists.append({
                'name' : self.current_playlist_name,
                'items' : playlist_keys})
        if self.in_location and name == 'location':
            self.in_title = False
            if self.current_location.startswith('file://'):
                # The <location> field contains a URL-encoded version of the
                # file path. Use the decoded version in all of our data
                # structures.
                path = urllib.unquote(str(self.current_location))[7:]
                self.current_playlist_items.append(path)
    def characters(self, ch):
        if self.in_location:
            self.current_location += ch
    def getPlaylists(self):
        return self.playlists

class RhythmboxBackend(LibraryBackend):
    """
    Object that controls access to a Rhythmbox music collection.

    infile is used to set the source of the library XML data. If omitted, the
    songs are read from the current user's Rhythmbox library. If provided
    (primarily useful for testing purposes), infile should be a file-like
    object.
    """
    def __init__(self, infile = None):
        self._files = set()
        self._contents = None
        self._playlists = None
        if infile:
            self._dbfile = infile
            return
        rhythmbox_db_path = os.path.expanduser(RB_DBFILE)
        # Handle file-not-found before general IOErrors. If the Rhythmbox
        # DB is missing the user probably doesn't want to use the Rhythmbox
        # backend at all. But if it exists, something else is probably
        # wrong.
        if not os.path.exists(rhythmbox_db_path):
            print "No Rhythmbox DB was found at %r." % (rhythmbox_db_path,)
            print "Consider using --path to read from a directory instead."
            sys.exit(1)
        try:
            self._dbfile = open(rhythmbox_db_path)
        except IOError:
            print "Couldn't read from Rhythmbox DB (%r)." \
                % (rhythmbox_db_path,)
            sys.exit(1)

        rhythmbox_playlist_path = os.path.expanduser(RB_PLAYLISTFILE)
        try:
            self._playlistfile = open(rhythmbox_playlist_path)
        except IOError:
            self._playlistfile = None
            print ("Warning: could not open Rhythmbox playlists.xml file " + \
                       "at %r. Playlists will not be loaded." % \
                       (rhythmbox_playlist_path,))

    def get_library_contents(self):
        # Memoize self._contents and self._files.
        if not self._contents:
            handler = RhythmboxDbHandler()
            p = expat.ParserCreate()
            p.StartElementHandler = handler.startElement
            p.EndElementHandler = handler.endElement
            p.CharacterDataHandler = handler.characters
            p.ParseFile(self._dbfile)
            self._contents = handler.getContents()
            self._files = handler.getFiles()
            # Sort the items by filename.
            self._contents.sort(
                key = (lambda item:
                           tokenize_filename(self._files[item['key']])))
        return self._contents

    def get_playlists(self):
        if not self._contents:
            # Make sure _contents and _files are populated.
            self.get_library_contents()
        if self._playlists is None:
            if self._playlistfile is None:
                self._playlists = []
            else:
                handler = RhythmboxPlaylistsHandler(self._files)
                p = expat.ParserCreate()
                p.StartElementHandler = handler.startElement
                p.EndElementHandler = handler.endElement
                p.CharacterDataHandler = handler.characters
                p.ParseFile(self._playlistfile)
                self._playlists = handler.getPlaylists()
                self._playlists.sort(key = (lambda playlist: playlist['name']))
        return self._playlists

    def get_filename_from_key(self, key):
        try:
            return self._files[int(key)]
        except IndexError:
            raise KeyError("Invalid key: %r" % (key,))
