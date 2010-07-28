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


# Logic for selecting which decoder to run for a given file.

import os

# TODO: detect available decoders at startup and disable extensions if they
# can't be played.

# To use any of the command lines, append a filename as the last argument.
decoders = {
    'flac': ("/usr/bin/flac", "-d", "-c", "--totally-silent"),
    'mp3': ("/usr/bin/mpg123", "-s", "-q"),
    'ogg': ("/usr/bin/oggdec", "-Q", "-o", "-"),
    'm4a': ("/usr/bin/faad", "-w", "-q"),
    }

decoder_messages = {
    'flac': "/usr/bin/flac not found. Please install 'flac' to play .flac files.",
    'mp3': "/usr/bin/mpg123 not found. Please install 'mpg123' to play .mp3 files.",
    'ogg': "/usr/bin/oggdec not found. Please install 'vorbis-tools' to play .ogg files.",
    'm4a': "/usr/bin/faad not found. Please install 'faad' to play .m4a files.",
    }

# The set of extensions for which we've warned the user that the decoder is not
# available. We maintain this set so we don't prompt the user more than once
# for the same codec.
prompts_already_issued = set()

def get_extension(filename):
    # Returns the lowercased extension of the filename (e.g. 'ogg').
    # Raises ValueError if the filename is malformed.
    return filename[filename.rfind('.')+1:].lower()

def has_decoder(filename):
    """
    Return whether or not the decoder that would be used to read filename is
    registered and actually present on the system.

    If it isn't, print a warning, but only if no previous warning has been
    issued for the same decoder.
    """
    if not is_decoder_registered(filename):
        return False
    extension = get_extension(filename)
    decoder_path = decoders[extension][0]
    decoder_installed = os.path.exists(decoder_path)
    if not decoder_installed and extension not in prompts_already_issued:
        print "Warning: %s" % (decoder_messages[extension],)
        prompts_already_issued.add(extension)
    return decoder_installed

def is_decoder_registered(filename):
    """
    Returns True if a decoder is registered for the given filename.
    """
    try:
        extension = get_extension(filename)
    except ValueError:
        return False
    return decoders.has_key(extension)

def get_decoder(filename):
    """
    Returns a command line for decoding the given filename.

    This command line can be passed to subprocess.Popen, and writes all data to
    stdout.
    """
    extension = get_extension(filename)
    return list(decoders[extension] + (filename,))
