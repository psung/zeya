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

def album_name_from_path(tag, filename):
    """
    Returns an appropriate Unicode string to use for the album name if the tag
    is empty.
    """
    if tag is not None and (tag.artist or tag.album):
        return u''
    # Use the trailing components of the path.
    path_components = [x for x in os.path.dirname(filename).split(os.sep) if x]
    if len(path_components) >= 2:
        return os.sep.join(path_components[-2:]).decode("UTF-8")
    elif len(path_components) == 1:
        return path_components[0].decode("UTF-8")
    return u''

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
        print "Scanning for music in %r..." % (os.path.abspath(self._media_path),)
        # Iterate over all the files.
        for path, dirs, files in os.walk(self._media_path):
            # Sort dirs so that subdirectories will subsequently be visited
            # alphabetically (see os.walk).
            dirs.sort(key=tokenize_filename)
            for filename in sorted(files, key=tokenize_filename):
                filename = os.path.abspath(os.path.join(path, filename))
                # For each file that we encounter, see if we have cached data
                # for it, and if we do, use it instead of calling out to tagpy.
                # previous_db acts as a cache of mtime and metadata, keyed by
                # filename.
                rec_mtime, old_metadata = previous_db.get(filename, (None, None))
                file_mtime = os.stat(filename).st_mtime

                # Set the artist, title, and album in this block, and the key
                # below.
                if rec_mtime is not None and rec_mtime >= file_mtime:
                    # Use cached data. However, we potentially renumber the
                    # keys every time, so the old KEY is no good. We'll update
                    # the KEY field later.
                    metadata = old_metadata
                else:
                    # In this branch, we actually need to read the file and
                    # extract its metadata.
                    try:
                        metadata = extract_metadata(filename)
                    except ValueError:
                        # If there was any exception, then ignore the file and
                        # continue.
                        continue

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

def extract_metadata(filename, tagpy_module = tagpy):
    """
    Returns a metadata dictionary (a dictionary {ARTIST: ..., ...}) containing
    metadata (artist, title, and album) for the song in question.

    filename: a string supplying a filename.
    tagpy_module: a reference to the tagpy module. This can be faked out for
    unit testing.
    """
    # tagpy can do one of three things:
    #
    # * Return legitimate data. We'll load that data.
    # * Return None. We'll assume this is a music file but that it doesn't have
    #   metadata. Create an entry for it.
    # * Throw ValueError. We'll assume this is not something we could play.
    #   Don't create an enty for it.
    try:
        tag = tagpy_module.FileRef(filename).tag()
    except:
        raise ValueError("Error reading metadata from %r" % (filename,))
    # If no metadata is available, set the title to be the basename of the
    # file. (We have to ensure that the title, in particular, is not empty
    # since the user has to click on it in the web UI.)
    metadata = {
        TITLE: os.path.basename(filename).decode("UTF-8"),
        ARTIST: '',
        ALBUM: album_name_from_path(tag, filename),
        }
    if tag is not None:
        metadata[ARTIST] = tag.artist
        # Again, do not allow metadata[TITLE] to be an empty string, even if
        # tag.title is an empty string.
        metadata[TITLE] = tag.title or metadata[TITLE]
        metadata[ALBUM] = tag.album or metadata[ALBUM]
    return metadata
