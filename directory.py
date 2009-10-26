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

from backend import LibraryBackend
from common import tokenize_filename

KEY = 'key'
TITLE = 'title'
ARTIST = 'artist'
ALBUM = 'album'

DB = 'db'
KEY_FILENAME = 'key_filename'
MTIMES = 'mtimes'

class DirectoryBackend(LibraryBackend):
    """
    Object that controls access to music in a given directory.
    """
    def __init__(self, media_path, save_db=True):
        self._media_path = os.path.expanduser(media_path)
        self._save_db = save_db
        # Sequence of dicts containing song metadata (key, artist, title, album)
        self.db = []
        # Dict mapping keys to source filenames
        self.key_filename = {}
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
        pickle.dump(self.info, open(self.get_db_filename(), 'wb+'))

    def fill_db(self, previous_db):
        """
        Populate the database, given the output of load_previous_db.
        """
        print "Scanning library..."
        # Iterate over all the files.
        for path, dirs, files in os.walk(self._media_path):
            for filename in sorted(files, key=tokenize_filename):
                filename = os.path.abspath(os.path.join(path, filename))
                # For each file that we encounter, see if we have cached data
                # for it, and if we do, use it instead of calling out to tagpy.
                # previous_db acts as a cache of mtime and metadata, keyed by
                # filename.
                rec_mtime, old_metadata = previous_db.get(filename, (None, None))
                file_mtime = os.stat(filename).st_mtime

                if rec_mtime is not None and rec_mtime >= file_mtime:
                    # Use cached data. However, we potentially renumber the
                    # keys every time, so the old KEY is no good. We'll update
                    # the KEY field later.
                    metadata = old_metadata
                else:
                    # In this branch, we actually need to read the file.
                    try:
                        tag = tagpy.FileRef(filename).tag()
                    except:
                        # If there was any exception, then ignore the file and
                        # continue. Catching ValueError is sufficient to catch
                        # non-audio but we want to not abort from this.
                        continue
                    # Set the artist, title, and album now, and the key below.
                    metadata = { ARTIST: tag.artist if tag is not None else '',
                                 TITLE: \
                                    tag.title if tag is not None and tag.title else \
                                    os.path.basename(filename),
                                 ALBUM: tag.album if tag is not None else '',
                               }

                # Number the keys consecutively starting from 0.
                next_key = len(self.key_filename)
                metadata[KEY] = next_key
                self.db.append(metadata)
                self.key_filename[next_key] = filename
                self.mtimes[filename] = file_mtime

    def get_library_contents(self):
        return self.db

    def get_filename_from_key(self, key):
        return self.key_filename[int(key)]
