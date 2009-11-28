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

import fcntl
import os
import signal
import socket
import subprocess
import time

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
    encode_command = ["/usr/bin/oggenc", "-r", "-Q", "-b", str(bitrate), "-"]
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
        bytes_written = 0
        start_time = time.time()
        # Compute the output rate, converting kilobits/sec to bytes/sec.
        max_bytes_per_sec = RATE_MULTIPLIER * bitrate * 1024 / 8
        # Don't let reads block when we've read to the end of the encoded song
        # data.
        fcntl.fcntl(read_fd, fcntl.F_SETFL, os.O_NONBLOCK)
        encoder_finished = False
        while True:
            time.sleep(1/STREAM_WRITE_FREQUENCY)
            # If the average transfer rate exceeds the threshold, sleep for a
            # while longer.
            if bytes_written >= (time.time() - start_time) * max_bytes_per_sec:
                continue
            # Detect when the encoder process has finished. We assume that data
            # written by the encoder is immediately available via os.read.
            # Therefore, if the encoder has finished, and we subsequently
            # cannot read data from the input stream, we can conclude that we
            # have read all the data.
            if p2.poll() != None:
                encoder_finished = True
            try:
                data = os.read(read_fd, STREAM_CHUNK_SIZE)
            except OSError:
                # OSError will be thrown if we read before the pipe has had any
                # data written to it.
                data = ""
            if encoder_finished and len(data) == 0:
                break
            try:
                out_stream.write(data)
            except socket.error:
                # The client likely terminated the connection. Abort.
                p1.terminate()
                p2.terminate()
                return
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
        self.write_content in order to obtain the data for a particular file.

        The items will be displayed to the user in the order that they appear
        here.
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
            print "ERROR. %s" % (e,)

    def get_filename_from_key(self, key):
        # Retrieve the filename that 'key' is backed by. This is not part of
        # the public API, but is used in the default implementation of
        # get_content.
        #
        # Raise KeyError if the key is not valid.
        raise NotImplementedError()
