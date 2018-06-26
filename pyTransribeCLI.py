#!/usr/bin/env python
"""
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from __future__ import division, print_function

import argparse
import sys
import time
import urlparse
import urllib


#argv = sys.argv
# work around Gstreamer parsing sys.argv!
#sys.argv = []

import gi
gi.require_version('Gst', '1.0')
#from gi.repository import Gst
from gi.repository import Gtk, GObject, Gst, Gio, Gdk

GObject.threads_init()
Gst.init(None)

#sys.argv = argv


def path2url(path):
    return urlparse.urljoin('file:', urllib.pathname2url(path))


def timestr_to_seconds(timestr):
    l, r = timestr.split(":")
    seconds = float(l) * 60 + float(r)
    seconds_to_timestr(seconds)
    return seconds


def seconds_to_timestr(seconds):
    m = int(seconds) // 60
    s = seconds % 60
    timestr = "{:02d}:{:02.3f}".format(m, s)
    return timestr


def build_bin(file_out, tempo, pitch):
    bin = Gst.Bin()

    # Create elements and add to bin
    el_pitch = Gst.ElementFactory.make("pitch")
    el_pitch.set_property("tempo", tempo)
    el_pitch.set_property("pitch", 2**(pitch/12.0))
    bin.add(el_pitch)

    el_audioconvert = Gst.ElementFactory.make("audioconvert")
    bin.add(el_audioconvert)

    el_wavenc = Gst.ElementFactory.make("wavenc")
    bin.add(el_wavenc)

    el_filesink = Gst.ElementFactory.make("filesink")
    el_filesink.set_property("location", file_out)
    bin.add(el_filesink)

    # Link elements
    el_pitch.link(el_audioconvert)
    el_audioconvert.link(el_wavenc)
    el_wavenc.link(el_filesink)

    # Add a pad
    sink_pad = Gst.GhostPad.new("sink", el_pitch.get_static_pad("sink"))
    bin.add_pad(sink_pad)
    return bin


def process_file(uri_in, file_out, tempo, pitch):
    """
    Inspired by playitslowly pipeline, Copyright (C) 2009 - 2015 Jonas Wagner
    """
    pipeline = Gst.Pipeline()

    # Add playbin to pipeline
    playbin = Gst.ElementFactory.make("playbin")
    playbin.set_property("uri", uri_in)
    pipeline.add(playbin)

    # Connect playbin to bin/sink
    bin = build_bin(file_out, tempo, pitch)
    playbin.set_property("audio-sink", bin)

    loop = GObject.MainLoop()

    def end_of_stream(bus, msg):
        pipeline.set_state(Gst.State.NULL)
        loop.quit()

    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message::eos", end_of_stream)

    pipeline.set_state(Gst.State.PLAYING)
    loop.run()

    """
    # Various attempts to query the playing status, what a mess...
    #import IPython; IPython.embed()
    #status = pipeline.get_state(Gst.CLOCK_TIME_NONE)
    while True:
        print(bus.peek())
        #events = []
        #print(bus.poll(events, 100))
        #print(events)
        #status = pipeline.get_state(Gst.CLOCK_TIME_NONE)
        time_format = Gst.Format(Gst.Format.TIME)
        _, position = playbin.query_position(time_format)
        _, duration = playbin.query_duration(time_format)
        #print(position, duration)
        if position >= duration and duration > 0:
            break
        status = pipeline.get_state(1)
        #print(status)
        time.sleep(0.1)
    """

def post_process(file_out, tempo, trim_from, trim_upto):
    import IPython; IPython.embed()


def parse_args():
    parser = argparse.ArgumentParser(description="Convert audio files with pitch/tempo modifications")
    parser.add_argument(
        "file",
        help="File to convert"
    )
    parser.add_argument(
        "--pitch",
        type=float,
        default=0.0,
        help="Pitch modification in semitones"
    )
    parser.add_argument(
        "--tempo",
        type=float,
        default=1.0,
        help="Tempo factor"
    )
    parser.add_argument(
        "--from",
        dest="trim_from",
        type=str,
        default=None,
        help="Trim output from start",
    )
    parser.add_argument(
        "--upto",
        dest="trim_upto",
        type=str,
        default=None,
        help="Trim output from end",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Name of output file (by default a suffix is added to the given input file)"
    )
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_args()
    if args.out is None:
        args.out = "{} [{:+02.0f}, {}].wav".format(
            args.file[:-4],
            args.pitch,
            args.tempo,
        )

    if args.trim_from is not None:
        args.trim_from = timestr_to_seconds(args.trim_from)
    if args.trim_upto is not None:
        args.trim_upto = timestr_to_seconds(args.trim_upto)

    # Apparently only the input file has to be an URI, not the output.
    args.file = path2url(args.file)
    process_file(args.file, args.out, args.tempo, args.pitch)
    post_process(args.out, args.tempo, args.trim_from, args.trim_upto)
