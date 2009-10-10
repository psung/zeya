#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Test suite for Zeya.

import unittest

import rhythmbox

class RhythmboxTest(unittest.TestCase):
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
