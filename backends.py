# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Phil Sung, Samson Yeung, Romain Francoise
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

# Common code for library backends.

import fcntl
import os
import signal
import socket
import subprocess
import tagpy
import time

TITLE='title'
ARTIST='artist'
ALBUM='album'

# For Python2.5 compatibility, we create an equivalent to
# subprocess.Popen.terminate (new in Python2.6) and patch it in.
try:
    subprocess.Popen.terminate
except AttributeError:
    def sub_popen_terminate(self):
        # This will only work on Unix-like systems, but it's better than
        # nothing.
        os.kill(self.pid, signal.SIGTERM)
    subprocess.Popen.terminate = sub_popen_terminate

import decoders

# Serve data to the client at a rate of no higher than RATE_MULTIPLIER * (the
# bitrate of the encoded data).
RATE_MULTIPLIER = 2.0

# Attempt to write STREAM_CHUNK_SIZE bytes up to (but possibly less than)
# STREAM_WRITE_FREQUENCY times per second. The maximum possible write rate with
# these parameters is 8192 bytes * 128 Hz = 1MB/sec.
STREAM_CHUNK_SIZE = 8192 #bytes
STREAM_WRITE_FREQUENCY = 128.0 #Hz

class StreamGenerationError(Exception):
    """
    Indicates an error generating a stream for the requested file.
    """
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

def filename_to_stream(filename, out_stream, bitrate, buffered=False):
    print "Handling request for %s" % (filename,)
    try:
        decode_command = decoders.get_decoder(filename)
    except KeyError:
        raise StreamGenerationError(
            "Couldn't play specified format: %r" % (filename,))
    encoder_path = "/usr/bin/oggenc"
    if not os.path.exists(encoder_path):
        raise StreamGenerationError(
            ("No Vorbis encoder found at %s. " % (encoder_path,)) + \
                "Please install 'vorbis-tools'.")
    encode_command = [encoder_path, "-r", "-Q", "-b", str(bitrate), "-"]
    # Pipe the decode command into the encode command.
    p1 = subprocess.Popen(decode_command, stdout=subprocess.PIPE)
    if buffered:
        # Read the entire output and then write it to the output stream.
        p2 = subprocess.Popen(encode_command, stdin=p1.stdout, stdout=subprocess.PIPE)
        out_stream.write(p2.stdout.read())
    else:
        # Stream the encoder output while limiting the total bandwidth used. We
        # do this by writing the encoder output to a pipe and reading from the
        # pipe at a limited rate.
        (read_fd, write_fd) = os.pipe()
        p2 = subprocess.Popen(encode_command, stdin=p1.stdout,
                              stdout=os.fdopen(write_fd, 'wb'))
        # Don't let reads block when we've read to the end of the encoded song
        # data.
        fcntl.fcntl(read_fd, fcntl.F_SETFL, os.O_NONBLOCK)
        try:
            copy_output_with_shaping(read_fd, out_stream, bitrate,
                                     lambda : p2.poll() != None)
        except socket.error:
            p1.terminate()
            p2.terminate()
        # Close the FIFO we opened.
        try:
            os.close(read_fd)
        except OSError:
            pass

def copy_output_with_shaping(read_fd, out_stream, bitrate,
                             encoder_finished_callback = lambda : True):
    """
    Copies data from the input stream with the specified FD to the given output
    stream. Do not copy data faster than BITRATE * RATE_MULTIPLIER bits/second.

    Ceases copying data when the input stream is empty AND
    encoder_finished_callback() evaluates to True in a boolean context.
    """
    bytes_written = 0
    start_time = time.time()
    # Compute the output rate, converting kilobits/sec to bytes/sec.
    max_bytes_per_sec = RATE_MULTIPLIER * bitrate * 1024 / 8
    encoder_finished = False
    while True:
        time.sleep(1/STREAM_WRITE_FREQUENCY)
        # If the average transfer rate exceeds the threshold, sleep for a
        # while longer.
        if bytes_written >= (time.time() - start_time) * max_bytes_per_sec:
            continue
        # Detect when the source (encoder) process has finished. We assume that
        # data written by the encoder is immediately available via os.read.
        # Therefore, if the encoder has finished, and we subsequently cannot
        # read data from the input stream, we can conclude that we have read
        # all the data.
        if encoder_finished_callback():
            encoder_finished = True
        try:
            data = os.read(read_fd, STREAM_CHUNK_SIZE)
        except OSError:
            # OSError will be thrown if we read before the pipe has had any
            # data written to it.
            data = ""
        if encoder_finished and len(data) == 0:
            break
        out_stream.write(data)
        bytes_written = bytes_written + len(data)

# This interface is implemented by all library backends.

class LibraryBackend():
    """
    Object that controls access to a collection of music files.
    """
    def get_library_contents(self):
        """
        Return a list of the available files.

        The return value should be of the form

          [ {'key': ..., 'title': ..., 'artist': ..., 'album': ...},
            ... ]

        where each entry represents one file. The values coresponding to
        'title', 'artist', and 'album' are strings or unicode strings giving
        the song attributes. The value corresponding to 'key' may be passed to
        self.write_content in order to obtain the data for a particular file,
        and the same key appears in the result of get_playlists().

        The items will be displayed to the user in the order that they appear
        here.
        """
        raise NotImplementedError()

    def get_playlists(self):
        """
        Return a list of the available playlists.

        The return value should be of the form

          [ {'name': ..., 'items': [ ... ] },
            ... ]

        where each entry represents one playlist. The 'name' field contains a
        string representing the user-displayable name of the playlist. The
        'items' field is a list of the song keys identifying the songs in the
        playlist, in order.

        NotImplementedError may be thrown if the backend does not have any
        concept of playlists.
        """
        raise NotImplementedError()

    def get_content(self, key, out_stream, bitrate, buffered=False):
        """
        Retrieve the file data associated with the specified key and write an
        audio/ogg encoded version to out_stream.
        """
        # This is a convenience implementation of this method.
        try:
            filename = self.get_filename_from_key(key)
        except KeyError:
            print "Received invalid request for key %r" % (key,)
        try:
            filename_to_stream(filename, out_stream, bitrate, buffered)
        except StreamGenerationError, e:
            print "Error: %s" % (e,)

    def get_filename_from_key(self, key):
        # Retrieve the filename that 'key' is backed by. This is not part of
        # the public API, but is used in the default implementation of
        # get_content.
        #
        # Raise KeyError if the key is not valid.
        raise NotImplementedError()

def extract_metadata(filename, tagpy_module=tagpy):
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
    #   Don't create an entry for it.
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
