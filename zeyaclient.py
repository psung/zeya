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
    """
    Return True if the query matches the given song.

    A query might look like "help, the beatles"

    A song is considered to match if each comma-separated component of the
    query appears somewhere in one of the song's metadata fields. Matching is
    case-insensitive.
    """
    parts = [part.strip() for part in query.lower().split(",")]
    return all(part in song['album'].lower() or part in song['title'].lower() \
                   or part in song['artist'].lower() for part in parts)

def run(server_path):
    library_file = urllib2.urlopen(server_path + "/getlibrary")
    library_data = json.loads(library_file.read())
    print "Loaded %d songs from library." % (len(library_data),)
    print 'You can issue queries like: "Beatles" or "help, the beatles"'
    while True:
        # Prompt user for a query...
        query = raw_input("Query? ")
        if not query:
            break
        # ...then play all the songs we can find that match the query.
        matching_songs = \
            [song for song in library_data if song_matches(query, song)]
        for song in matching_songs:
            print "%s - %s" % (song['title'], song['artist'])
            song_url = "%s/getcontent?key=%d" % (server_path, song['key'])
            p = subprocess.Popen(["/usr/bin/ogg123", "-q", song_url])
            try:
                p.communicate()
            except KeyboardInterrupt:
                # TODO: handle Ctrl-C here in a better way. Whenever an
                # interrupt is followed by a new query (raw_input above) we
                # seem to get a spurious EOFError.
                pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Usage: zeyaclient.py http://server:8080"
        sys.exit(1)
    run(sys.argv[1])
