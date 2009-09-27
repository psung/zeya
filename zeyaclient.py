#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Console frontend to Zeya server.
#
# Usage:
#   zeyaclient.py http://server.local:8080

import subprocess
import sys
import urllib2

try:
    import json
    json.dumps
except (ImportError, AttributeError):
    import simplejson as json

def song_matches(query, song):
    parts = [part.strip() for part in query.lower().split(",")]
    # Song matches if each comma-delimited part of the query is found somewhere
    # in the song metadata (album, title, or artist).
    return all(part in song['album'].lower() or part in song['title'].lower() \
                   or part in song['artist'].lower() for part in parts)

def run(server_path):
    library_file = urllib2.urlopen(server_path + "/getlibrary")
    library_data = json.loads(library_file.read())
    print "Loaded %d songs from library." % (len(library_data),)
    while True:
        query = raw_input("Query? ")
        if not query:
            break
        try:
            for song in library_data:
                if song_matches(query, song):
                    print "%s - %s" % (song['title'], song['artist'])
                    song_url = "%s/getcontent?key=%d" % \
                        (server_path, song['key'])
                    p = subprocess.Popen(["/usr/bin/ogg123", "-q", song_url])
                    p.communicate()
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    run(sys.argv[1])
