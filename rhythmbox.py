# Rhythmbox backend.

import os
import re
import subprocess
import urllib

RB_DBFILE = '~/.local/share/rhythmbox/rhythmdb.xml'

class RhythmboxBackend():
    def __init__(self):
        self._files = set()
        self._contents = None
    def get_library_contents(self):
        if self._contents:
            return self._contents
        contents = []
        files = set()
        with open(os.path.expanduser(RB_DBFILE)) as f:
            in_song = False
            for line in f:
                line = line.strip()
                m = re.match(' *<entry type="(.*)">', line)
                if m:
                    in_song = m.group(1) == 'song'
                    location = ''
                    artist = 'Unknown'
                    album = 'Unknown'
                    title = 'Unknown'

                # TODO: decode properly using an XML parser.
                m = re.match(" *<location>file://(.*)</location>\n?", line)
                if m:
                    location = urllib.unquote(m.group(1))
                m = re.match(" *<title>(.*)</title>\n?", line)
                if m:
                    title = m.group(1)
                m = re.match(" *<artist>(.*)</artist>\n?", line)
                if m:
                    artist = m.group(1)
                m = re.match(" *<album>(.*)</album>\n?", line)
                if m:
                    album = m.group(1)

                if re.match(" *</entry>", line) and in_song:
                    files.add(location)
                    contents.append({ "location": location, "title": title,
                                      "artist": artist, "album": album })
        self._files = files
        self._contents = contents
        return contents
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
