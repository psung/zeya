# Rhythmbox backend.

import os
import re
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
        # Maintain a set of just the paths for fast membership tests.
        self.files = set()
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
                path = urllib.unquote(self.current_location[7:])
                self.contents.append(
                    {'title':self.current_title, 'artist':self.current_artist,
                     'album':self.current_album, 'key':path})
                self.files.add(path)
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
        return self.files
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
            # Sort the items by filename.
            self._contents.sort(key = (lambda item: item['key']))
            self._files = handler.getFiles()
        return self._contents
    def get_content(self, key, out_stream):
        # Verify that the key is a path that was already in the collection, so
        # we don't read arbitrary (possibly non-existent or non-music) files.
        if key in self._files:
            print "Handing request for %s" % (key,)
            if key.lower().endswith('.flac'):
                decode_command = ["/usr/bin/flac", "-d", "-c", "--totally-silent", key]
            elif key.lower().endswith('.mp3'):
                decode_command = ["/usr/bin/lame", "-S", "--decode", key, "-"]
            elif key.lower().endswith('.ogg'):
                decode_command = ["/usr/bin/oggdec", "-Q", "-o", "-", key]
            else:
                print "No decode command found for %s" % (key,)
            # Pipe the decode command into the encode command.
            p1 = subprocess.Popen(decode_command, stdout=subprocess.PIPE)
            p2 = subprocess.Popen(["/usr/bin/oggenc", "-Q", "-b", "64", "-"],
                                  stdin=p1.stdout, stdout=out_stream)
        else:
            print "Received invalid request for %r" % (key,)
