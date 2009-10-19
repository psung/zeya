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
import rhythmbox

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
