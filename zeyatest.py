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


# Test suite for Zeya.

import unittest

import decoders
import directory
import options
import rhythmbox

class FakeTagpy():
    """
    Fake object that can be a stand-in for the tagpy module, but which returns
    a fixed tag object.
    """
    def __init__(self, retval):
        self.retval = retval
    def FileRef(self, filename):
        class FakeTag():
            # Avoid shadowing the outer instance of 'self', so we can read from
            # it.
            def tag(inner_self):
                return self.retval
        return FakeTag()

class TagData():
    """
    Tag object that holds metadata for a single song.
    """
    def __init__(self, artist, title, album):
        self.artist = artist
        self.title = title
        self.album = album

class CommonTest(unittest.TestCase):
    def test_tokenization(self):
        """
        Test that our tokenization method yields a correct ordering of songs.
        """
        # Note, filename1 > filename2
        filename1 = "/home/phil/9 - something.ogg"
        filename2 = "/home/phil/10 - something.ogg"
        t1 = rhythmbox.tokenize_filename(filename1)
        t2 = rhythmbox.tokenize_filename(filename2)
        self.assertTrue(t1 < t2)

class DecodersTest(unittest.TestCase):
    def test_extensions(self):
        """
        Test decoders.get_extension.
        """
        self.assertEqual("mp3", decoders.get_extension("/path/to/SOMETHING.MP3"))
    def test_has_decoder(self):
        """
        Test decoders.has_decoder.
        """
        self.assertTrue(decoders.has_decoder("/path/to/something.mp3"))
        self.assertFalse(decoders.has_decoder("/path/to/something.m4a"))
    def test_get_decoder(self):
        """
        Test decoders.get_decoder
        """
        self.assertTrue(decoders.get_decoder("/path/to/SOMETHING.MP3")[0]
                        .startswith("/usr/bin"))

class DirectoryBackendTest(unittest.TestCase):
    def test_with_metadata(self):
        tagpy = FakeTagpy(TagData(artist="Beatles", title="Ticket to Ride",
                                  album="Help!"))
        metadata = directory.extract_metadata("/dev/null", tagpy)
        self.assertEqual("Ticket to Ride", metadata[directory.TITLE])
        self.assertEqual("Beatles", metadata[directory.ARTIST])
        self.assertEqual("Help!", metadata[directory.ALBUM])
    def test_without_metadata(self):
        tagpy = FakeTagpy(None)
        metadata = directory.extract_metadata("/the/path/to/Song.flac", tagpy)
        self.assertEqual("Song.flac", metadata[directory.TITLE])
        self.assertEqual("", metadata[directory.ARTIST])
        self.assertEqual("path/to", metadata[directory.ALBUM])
    def test_short_path(self):
        tagpy = FakeTagpy(None)
        metadata = directory.extract_metadata("/music/Song.flac", tagpy)
        self.assertEqual("music", metadata[directory.ALBUM])
    def test_noalbum_path(self):
        tagpy = FakeTagpy(TagData(artist="Beatles", title=None, album=None))
        metadata = directory.extract_metadata("/music/Song.flac", tagpy)
        self.assertEqual("", metadata[directory.ALBUM])
    def test_decode_filename(self):
        tagpy = FakeTagpy(None)
        metadata = directory.extract_metadata("/path/to/\xe4\xb8\xad.flac", tagpy)
        self.assertEqual(u"\u4e2d.flac", metadata[directory.TITLE])
    def test_album_name_from_path_unicode(self):
        value1 = directory.album_name_from_path(
            TagData(artist="Beatles", title=None, album=None),
            "/path/to/music")
        self.assertTrue(type(value1) == unicode)
        self.assertEqual(u'', value1)
        value2 = directory.album_name_from_path(None, "/path/\xc3\x84/music")
        self.assertEqual(u'path/\u00c4', value2)
        value3 = directory.album_name_from_path(None, "/\xc3\x84/music")
        self.assertEqual(u'\u00c4', value3)

class OptionsTest(unittest.TestCase):
    def test_default(self):
        params = options.get_options([])
        self.assertFalse(params[0])
        self.assertEqual('dir', params[1])
        self.assertEqual('.', params[4])
    def test_get_help(self):
        params = options.get_options(["--help"])
        self.assertTrue(params[0])
    def test_path(self):
        params = options.get_options(["--path=/foo/bar"])
        self.assertEqual('/foo/bar', params[4])
    def test_backend(self):
        params = options.get_options(["--backend=rhythmbox"])
        self.assertEqual('rhythmbox', params[1])
    def test_bad_backend(self):
        try:
            params = options.get_options(["--backend=invalid"])
            self.fail("get_options should have raised BadArgsError")
        except options.BadArgsError:
            pass
    def test_bitrate(self):
        params = options.get_options(["-b128"])
        self.assertEqual(128, params[2])
    def test_bad_bitrate(self):
        try:
            params = options.get_options(["--bitrate=0"])
            self.fail("get_options should have raised BadArgsError")
        except options.BadArgsError:
            pass
    def test_port(self):
        params = options.get_options(["-p9999"])
        self.assertEqual(9999, params[3])
    def test_bad_port(self):
        try:
            params = options.get_options(["--port=p"])
            self.fail("get_options should have raised BadArgsError")
        except options.BadArgsError:
            pass

class RhythmboxTest(unittest.TestCase):
    def test_read_library(self):
        """
        Verify that the contents of the Rhythmbox XML library are read
        correctly.
        """
        backend = rhythmbox.RhythmboxBackend(open("testdata/rhythmbox.xml"))
        library = backend.get_library_contents()
        self.assertEqual(u'Help!', library[0]['album'])
        self.assertEqual(u'The Beatles', library[0]['artist'])
        self.assertEqual(u'Help!', library[0]['title'])
        key1 = library[0]['key']
        self.assertEqual('/tmp/Beatles, The/Help.flac',
                         backend.get_filename_from_key(key1))
        # Test correct handling of songs and filenames with non-Latin
        # characters.
        self.assertEqual(u'', library[1]['album'])
        self.assertEqual(u'', library[1]['artist'])
        self.assertEqual(u'\u4e2d\u6587', library[1]['title'])
        key2 = library[1]['key']
        self.assertEqual(u'/tmp/\u4e2d\u6587.flac'.encode('UTF-8'),
                         backend.get_filename_from_key(key2))

if __name__ == "__main__":
    unittest.main()
