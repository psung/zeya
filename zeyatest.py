#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Test suite for Zeya.

import unittest

import rhythmbox

class RhythmboxTest(unittest.TestCase):
    def testtokenization(self):
        # Note, filename1 > filename2
        filename1 = "/home/phil/9 - something.ogg"
        filename2 = "/home/phil/10 - something.ogg"
        t1 = rhythmbox.tokenize_filename(filename1)
        t2 = rhythmbox.tokenize_filename(filename2)
        self.assertTrue(t1 < t2)

if __name__ == "__main__":
    unittest.main()
