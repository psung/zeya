# Rhythmbox backend.

import os
import re
import subprocess
import urllib

from xml.parsers import expat

RB_DBFILE = '~/.local/share/rhythmbox/rhythmdb.xml'

class RhythmboxDbHandler():
    def __init__(self):
        self.files = set()
        self.contents = []
        self.in_song = False
        self.in_title = False
        self.in_artist = False
        self.in_album = False
        self.in_location = False
    def startElement(self, name, attrs):
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
            self.in_song = False
            if self.current_location.startswith('file://'):
                path = urllib.unquote(self.current_location[7:])
                self.contents.append({ 'title': self.current_title,
                                       'artist': self.current_artist,
                                       'album': self.current_album,
                                       'location': path })
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

class RhythmboxBackend():
    def __init__(self):
        self._files = set()
        self._contents = None
    def get_library_contents(self):
        if not self._contents:
            handler = RhythmboxDbHandler()
            p = expat.ParserCreate()
            p.StartElementHandler = handler.startElement
            p.EndElementHandler = handler.endElement
            p.CharacterDataHandler = handler.characters
            p.ParseFile(open(os.path.expanduser(RB_DBFILE)))
            self._contents = handler.getContents()
            self._files = handler.getFiles()
        return self._contents
    def get_content(self, key, out_stream):
        if key in self._files:
            print key
            if key.endswith('.flac'):
                decode_command = "/usr/bin/flac -d -c --totally-silent \"%s\""
            elif key.endswith('.mp3'):
                decode_command = "/usr/bin/lame -S --decode \"%s\" -"
            print decode_command
            p = subprocess.Popen((decode_command % (key,)) + " | /usr/bin/oggenc -Q -b 64 -",
                                 bufsize = 100000, stdout = out_stream, shell = True)
