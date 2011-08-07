# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Samson Yeung, Phil Sung
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


# Directory backend.
#
# Files in the specified directory are read for artist/title/album tag which is
# then saved in a database (zeya.db) stored in that directory.

import os
import tagpy
import pickle

from backends import LibraryBackend
from backends import extract_metadata
from common import tokenize_filename
from m3u import M3uPlaylist
from pls import PlsPlaylist

KEY = 'key'

DB = 'db'
KEY_FILENAME = 'key_filename'
MTIMES = 'mtimes'

class DirectoryBackend(LibraryBackend):
    """
    Object that controls access to music in a given directory.
    """
    def __init__(self, media_path, save_db=True):
        """
        Initializes a DirectoryBackend that reads from the specified directory.

        save_db can be set to False to prevent the db from being written back
        to disk. This is probably only useful for debugging purposes.
        """
        self._media_path = os.path.expanduser(media_path)
        self._save_db = save_db
        # Sequence of dicts containing song metadata (key, artist, title, album)
        self.db = []
        # Playlists
        self._playlists = []
        # Dict mapping keys to source filenames and vice versa
        self.key_filename = {}
        self.filename_key = {}
        # Dict mapping filenames to mtimes
        self.mtimes = {}

        self.setup_db()

    def get_db_filename(self):
        return os.path.join(self._media_path, 'zeya.db')

    def setup_db(self):
        # Load the previous database from file, and convert it to a
        # representation where it can serve as a metadata cache (keyed by
        # filename) when we load the file collection.
        previous_db = self.load_previous_db()
        self.fill_db(previous_db)
        if self._save_db:
            self.save_db()

    def load_previous_db(self):
        """
        Read the existing database on disk and return a dict mapping each
        filename to the (mtime, metadata) associated with the filename.
        """
        filename_to_metadata_map = {}
        try:
            # Load the old data structures from file.
            info = pickle.load(open(self.get_db_filename(), 'r'))
            key_to_metadata_map = {}
            prev_mtimes = info[MTIMES]
            # Construct a map from keys to metadata.
            for db_entry in info[DB]:
                key_to_metadata_map[db_entry[KEY]] = db_entry
            # Construct a map from filename to (mtime, metadata) associated
            # with that file.
            for (key, filename) in info[KEY_FILENAME].iteritems():
                filename_to_metadata_map[filename] = \
                    (prev_mtimes[filename], key_to_metadata_map[key])
        except IOError:
            # Couldn't read the file. Just return an empty data structure.
            pass
        return filename_to_metadata_map

    def save_db(self):
        self.info = {DB: self.db,
                     MTIMES: self.mtimes,
                     KEY_FILENAME: self.key_filename}
        try:
            pickle.dump(self.info, open(self.get_db_filename(), 'wb+'))
        except IOError, e:
            print "Warning: the metadata cache could not be written to disk:"
            print "  " + str(e)
            print "(Zeya will continue, but the directory will need to be",
            print "re-scanned the next time Zeya is run.)"

    def write_metadata(self, filename, previous_db):
        """
        Obtains and writes the metadata for the specified FILENAME to the
        database. The metadata may be found by looking in the cache
        (PREVIOUS_DB), and failing that, by pulling the metadata from the file
        itself.

        Returns the key associated with the filename.
        """
        if filename in self.filename_key:
            # First, if the filename is already in our database, we don't have
            # to do anything. We can encounter the same filename twice if a
            # playlist contains a reference to a file we've already scanned.
            key = self.filename_key[filename]
        else:
            # The filename is not in the database. We have to obtain a metadata
            # entry, either by reading it out of our cache, or by calling out
            # to tagpy.
            #
            # previous_db acts as a cache of mtime and metadata, keyed by
            # filename.
            rec_mtime, old_metadata = previous_db.get(filename, (None, None))
            file_mtime = os.stat(filename).st_mtime

            if rec_mtime is not None and rec_mtime >= file_mtime:
                # Use cached data. However, we potentially renumber the keys
                # every time the program runs, so the old KEY is no good. We'll
                # fix up the KEY field below.
                metadata = old_metadata
            else:
                # In this branch, we actually need to read the file and
                # extract its metadata.
                metadata = extract_metadata(filename)

            # Assign a key for this song. These are just integers assigned
            # sequentially.
            key = len(self.key_filename)
            metadata[KEY] = key

            self.db.append(metadata)
            self.key_filename[key] = filename
            self.filename_key[filename] = key
            self.mtimes[filename] = file_mtime

        return key

    def fill_db(self, previous_db):
        """
        Populate the database, given the output of load_previous_db.
        """
        # By default, os.walk will happily accept a non-existent directory and
        # return an empty sequence. Detect the case of a non-existent path and
        # bail out early.
        if not os.path.exists(self._media_path):
            raise IOError("Error: directory %r doesn't exist." % (self._media_path,))
        print "Scanning for music in %r..." % (os.path.abspath(self._media_path),)
        # Iterate over all the files.
        try:
            all_files_recursively = os.walk(self._media_path, followlinks=True)
        except TypeError:
            # os.walk in Python 2.5 and earlier don't support the followlinks
            # argument. Fall back to not including it (in this case, Zeya will
            # not index music underneath symlinked directories).
            all_files_recursively = os.walk(self._media_path)
        for path, dirs, files in all_files_recursively:
            # Sort dirs so that subdirectories will subsequently be visited
            # alphabetically (see os.walk).
            dirs.sort(key=tokenize_filename)
            for filename in sorted(files, key=tokenize_filename):
                filename = os.path.abspath(os.path.join(path, filename))

                # Skip broken symlinks
                if not os.path.exists(filename):
                    continue

                if filename.lower().endswith('.m3u') or filename.lower().endswith('.pls'):
                    # Encountered a playlist file.
                    try:
                        fileobj = open(filename)
                    except IOError:
                        print "Error opening playlist file: %r" % (filename,)
                        continue
                    if filename.lower().endswith('.m3u'):
                        playlist = M3uPlaylist(filename, fileobj)
                    elif filename.lower().endswith('.pls'):
                        playlist = PlsPlaylist(filename, fileobj)
                    items = []
                    for song_filename in playlist.get_filenames():
                        try:
                            song_key = self.write_metadata(
                                song_filename, previous_db)
                        except (OSError, ValueError):
                            continue
                        items.append(song_key)
                    self._playlists.append(
                        {'name' : playlist.get_title(), 'items': items})
                else:
                    # Encountered what is possibly a regular music file.
                    try:
                        self.write_metadata(filename, previous_db)
                    except (OSError, ValueError):
                        continue

    def get_library_contents(self):
        return self.db

    def get_playlists(self):
        return self._playlists

    def get_filename_from_key(self, key):
        return self.key_filename[int(key)]
