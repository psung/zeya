#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Phil Sung
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


# Console frontend to Zeya server.
#
# Usage:
#   zeyaclient.py http://server.local:8080
#
# zeyaclient prompts the user for a query, and all songs matching the query are
# played. The query may be matched against the title, artist, or album of the
# song.

import getopt
import os
import readline # Modifies the behavior of raw_input.
import signal
import subprocess
import sys
import time
import urllib2

try:
    import json
    json.dumps
except (ImportError, AttributeError):
    import simplejson as json

class BadArgsError(Exception):
    """
    Error due to incorrect command-line invocation of this program.
    """
    def __init__(self, message):
        self.error_message = message
    def __str__(self):
        return "Error: %s" % (self.error_message,)

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

# TODO: refactor the parts that directly interact with the server into a
# separate module.
def run(server_path):
    try:
        library_file = urllib2.urlopen(server_path + "/getlibrary")
    except ValueError, e:
        print "Error: %r is not a valid server name." % (server_path,)
        if not server_path.lower().startswith("http://"):
            print "Don't forget to precede the server name with 'http://'."
        print "(The full error text was: '%s')" % (e,)
        sys.exit(1)
    except urllib2.URLError, e:
        print "Error: %s" % (e.reason,)
        sys.exit(1)
    library_data = json.loads(library_file.read())['library']
    print "Loaded %d songs from library." % (len(library_data),)
    print 'You can issue queries like: "Beatles" or "help, the beatles"'
    while True:
        # Prompt user for a query...
        try:
            query = raw_input("\rQuery? ")
        except:
            # User pressed C-d or C-c.
            print
            break
        if not query:
            break
        # ...then play all the songs we can find that match the query.
        matching_songs = \
            [song for song in library_data if song_matches(query, song)]
        for song in matching_songs:
            print "\r%s - %s" % (song['title'], song['artist'])
            song_url = "%s/getcontent?key=%d" % (server_path, song['key'])
            p = subprocess.Popen(["/usr/bin/ogg123", "-q", song_url])
            try:
                p.communicate()
            except KeyboardInterrupt:
                # After a single ^C, skip to the next song.
                os.kill(p.pid, signal.SIGTERM)
                try:
                    time.sleep(0.5)
                except KeyboardInterrupt:
                    # If ^C^C is typed (within 0.5 sec) then break out back to
                    # the prompt.
                    break

def get_options(remaining_args):
    """
    Parse the arguments and return a tuple (show_help, server), or raise
    BadArgsError if the invocation was not valid.

    show_help: whether user requested help information
    server: Zeya server to connect to
    """
    help_msg = False
    try:
        opts, file_list = getopt.getopt(remaining_args, "h", ["help"])
    except getopt.GetoptError, e:
        raise BadArgsError(e.msg)
    for flag, value in opts:
        if flag in ("-h", "--help"):
            help_msg = True
    if help_msg:
        # With --help, it's ok if the user enters no server path.
        return (help_msg, None)
    # file_list should contain be a singleton list with the remote server.
    if len(file_list) == 0:
        raise BadArgsError("Expected server path")
    if len(file_list) > 1:
        raise BadArgsError("Unexpected argument after server")
    return (help_msg, file_list[0])

def print_usage():
    print "Usage: %s http://server:8080" % (os.path.basename(sys.argv[0]),)

if __name__ == "__main__":
    try:
        show_help, server = get_options(sys.argv[1:])
    except BadArgsError, e:
        print e
        print_usage()
        sys.exit(1)
    if show_help:
        print_usage()
        sys.exit(0)
    run(server)
