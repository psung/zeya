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


# Utility functions.

import re

def tokenize_filename(filename):
    """
    Return a list such that sorting a list of filenames by tokenize_filename(f)
    yields some "reasonable" result.

    filename: string containing a filename
    """
    # Sort lexicographically by components of the path, except we treat runs of
    # digits as separate components and sort those by numeric value. That way
    # we can, for example, sort "9.ogg" and "10.ogg" in the sensible way.
    def maybe_convert_to_int(s):
        """
        Return int(s) if s represents an integer and s otherwise.

        s: a string
        """
        try:
            return int(s)
        except ValueError:
            # Normalize case so we alphabetize logically.
            return s.lower()
    return [maybe_convert_to_int(s) for s in re.split(r'(/|\d+)', filename)]
