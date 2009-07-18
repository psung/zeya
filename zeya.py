#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Web music server.

import BaseHTTPServer

import json
import os
import re
import subprocess
import urllib

RB_DBFILE = '~/.local/share/rhythmbox/rhythmdb.xml'

library_contents = []

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

class ZeyaHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.serve_static_content('/library.html')
        elif self.path == '/getlibrary':
            self.serve_library()
        elif self.path.startswith('/getcontent?'):
            self.serve_content(urllib.unquote(self.path[12:]))
        else:
            self.serve_static_content(self.path)
    def do_POST(self):
        pass
    def get_content_type(self, path):
        if path.endswith('.html'):
            return 'text/html'
        elif path.endswith('.png'):
            return 'image/png'
        elif path.endswith('.css'):
            return 'text/css'
        elif path.endswith('.ogg'):
            return 'audio/ogg'
        else:
            return 'application/octet-stream'
    def serve_content(self, path):
        self.send_response(200)
        self.send_header('Content-type', 'audio/ogg')
        self.end_headers()
        print 'Starting to serve file...'
        rb.get_content(path, self.wfile)
        print 'Finished.'
        self.wfile.close()
    def serve_library(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        json.dump(library_contents, self.wfile, ensure_ascii=False)
        self.wfile.close()
    def serve_static_content(self, path):
        try:
            with open('resources' + path) as f:
                self.send_response(200)
                self.send_header('Content-type', self.get_content_type(path))
                self.end_headers()
                self.wfile.write(f.read())
                self.wfile.close()
        except IOError:
            self.send_error(404, 'File not found: %s' % (path,))

def main():
    global library_contents
    library_contents = rb.get_library_contents()
    server = BaseHTTPServer.HTTPServer(('', 8080), ZeyaHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()

if __name__ == '__main__':
    rb = RhythmboxBackend()
    main()
