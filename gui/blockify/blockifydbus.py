"""spotifydbus

Usage:
    spotifydbus (toggle | next | prev | stop | play) [-v...] [options]
    spotifydbus get [title | artist | length | status | all] [-v...] [options]
    spotifydbus (openuri <uri> | seek <secs> | setpos <pos>) [-v...] [options]

Options:
    -l, --log=<path>  Enables logging to the logfile/-path specified.
    -q, --quiet       Don't print anything to stdout.
    -v                Verbosity of the logging module, up to -vvv.
    -h, --help        Show this help text.
    --version         Show current version of spotifydbus.
"""
import logging
import os
import re
import sys

import dbus


try:
    from docopt import docopt
except ImportError:
    print "ImportError: Please install docopt to use the DBus CLI."


log = logging.getLogger("dbus")


class BlockifyDBus(object):
    "Wrapper for Spotify's DBus interface."

    def __init__(self, bus=None):
        self.obj_path = "/org/mpris/MediaPlayer2"
        self.prop_path = "org.freedesktop.DBus.Properties"
        self.player_path = "org.mpris.MediaPlayer2.Player"
        self.spotify_path = None

        if not bus:
            bus = dbus.SessionBus()
        self.session_bus = bus

        for name in bus.list_names():
            if re.match(r".*mpris.*spotify", name):
                self.spotify_path = str(name)

        if self.is_running():
            self.proxy = self.session_bus.get_object(self.spotify_path,
                                                     self.obj_path)
            self.properties = dbus.Interface(self.proxy, self.prop_path)
            self.player = dbus.Interface(self.proxy, self.player_path)
        else:
            self.properties = None
            self.player = None
            self.proxy = None
            log.error("Spotify not found in DBus session. Is it running?")

    def is_running(self):
        "TODO: Make this not redundant"
        if self.spotify_path is None:
            return False
        return True

    def get_property(self, key):
        "Gets the value from any available property."
        if self.is_running():
            return self.properties.Get(self.player_path, key)

    def set_property(self, key, value):
        "Sets the value for any available property."
        if self.is_running():
            return self.properties.Set(self.player_path, key, value)

    def playpause(self):
        "Toggles the current song between Play and Pause."
        if self.is_running():
            can_pause = self.get_property("CanPause")
            can_play = self.get_property("CanPlay")
            if can_pause and can_play:
                self.player.PlayPause()
            else:
                log.warn("Cannot Play/Pause")

    def play(self):
        "DEFUNCT: Tries to play the current title."
        if self.is_running():
            can_play = self.get_property("CanPlay")
            if can_play:
                self.player.Play()
            else:
                log.warn("Cannot Play")

    def stop(self):
        "Tries to stop playback. PlayPause is probably preferable."
        if self.is_running():
            self.player.Stop()

    def next(self):
        "Tries to skip to next song."
        if self.is_running():
            can_next = self.get_property("CanGoNext")
            if can_next:
                self.player.Next()
            else:
                log.warn("Cannot Go Next")

    def prev(self):
        "Tries to go back to last song."
        if self.is_running():
            can_prev = self.get_property("CanGoPrevious")
            if can_prev:
                self.player.Previous()
            else:
                log.warn("Cannot Go Previous.")

    def set_position(self, track, position):
        if self.is_running():
            self.player.SetPosition(track, position)

    def open_uri(self, uri):
        if self.is_running():
            self.player.OpenUri(uri)

    def seek(self, seconds):
        "DEFUNCT: Calls seek method."
        if self.is_running():
            can_seek = self.get_property("CanSeek")
            if can_seek:
                self.player.Seek(seconds)
            else:
                log.warn("Cannot Seek.")

    def get_song_status(self):
        "Get current PlaybackStatus (Paused/Playing...)."
        if self.is_running():
            return self.get_property("PlaybackStatus")

    def get_song_length(self):
        "Gets the length of current song from metadata (in seconds)."
        if self.is_running():
            metadata = self.get_property("Metadata")
            if metadata:
                return int(metadata["mpris:length"] / 1000000)

    def get_song_title(self):
        "Gets title of current song from metadata"
        if self.is_running():
            metadata = self.get_property("Metadata")
            if metadata:
                return metadata["xesam:title"].encode("utf-8")

    def get_song_album(self):
        "Gets album of current song from metadata"
        if self.is_running():
            metadata = self.get_property("Metadata")
            if metadata:
                return metadata["xesam:album"].encode("utf-8")

    def get_song_artist(self):
        "Gets the artist of current song from metadata"
        if self.is_running():
            metadata = self.get_property("Metadata")
            if metadata:
                return str(metadata["xesam:artist"][0])

    def print_info(self):
        "Print all the DBus info we can get our hands on."
        try:
            interfaces = self.properties.GetAll(self.player_path)
            metadata = self.get_property("Metadata")

            i_keys = list(map(str, interfaces.keys()))
            i_keys.remove("Metadata")
            i_keys.sort()

            for i in i_keys:
                if len(i) < 7:
                    print i, "\t\t= ", self.get_property(i)
                else:
                    print i, "\t= ", self.get_property(i)

            print ""

            d_keys = list(metadata.keys())
            d_keys.sort()

            for k in d_keys:
                d = k.split(":")[1]

                if d == "artist":
                    print d, "\t\t= ", metadata[k][0]
                # elif d == "length":
                elif len(d) < 7:
                    print d, "\t\t= ", metadata[k]
                else:
                    print d, "\t= ", metadata[k]
        except AttributeError as e:
            log.error("Could not get properties: {}".format(e))


def init_logger(logpath=None, loglevel=1, quiet=False):
    "Initializes the logger for system messages."
    logger = logging.getLogger()

    # Set the loglevel.
    if loglevel > 3:
        loglevel = 3  # Cap at 3 to avoid index errors.
    levels = [logging.ERROR, logging.WARN, logging.INFO, logging.DEBUG]
    logger.setLevel(levels[loglevel])

    logformat = "%(asctime)-14s %(levelname)-8s %(message)s"

    formatter = logging.Formatter(logformat, "%Y-%m-%d %H:%M:%S")

    if not quiet:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        log.debug("Added logging console handler.")
        log.info("Loglevel is {}.".format(levels[loglevel]))
    if logpath:
        try:
            logfile = os.path.abspath(logpath)
            file_handler = logging.FileHandler(logfile)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            log.debug("Added logging file handler: {}.".format(logfile))
        except IOError:
            log.error("Could not attach file handler.")


def main():
    "Entry point for the CLI DBus interface."
    args = docopt(__doc__, version="0.2")
    init_logger(args["--log"], args["-v"], args["--quiet"])
    spotify = BlockifyDBus()

    if args["toggle"]:
        spotify.playpause()
    elif args["next"]:
        spotify.next()
    elif args["prev"]:
        spotify.prev()
    elif args["play"]:
        spotify.play()
    elif args["stop"]:
        spotify.stop()

    if args["openuri"]:
        spotify.open_uri(args["<uri>"])
    elif args["seek"]:
        spotify.seek(args["<secs>"])
    elif args["setpos"]:
        spotify.set_pos(args["<pos>"])

    if args["title"]:
        print spotify.get_song_title()
    elif args["artist"]:
        print spotify.get_song_artist()
    elif args["status"]:
        print spotify.get_song_status()
    elif args["all"]:
        spotify.print_info()
    elif args["get"]:
        length = spotify.get_song_length()
        m, s = divmod(length, 60)
        if args["length"]:
            print "{}m{}s ({})".format(m, s, length)
        else:
            rating = spotify.get_property("Metadata")["xesam:autoRating"]
            artist = spotify.get_song_artist()
            title = spotify.get_song_title()
            album = spotify.get_song_album()
            state = spotify.get_song_status()
            print "{} - {} ({}), {}m{}s, {} ({})".format(artist, title, album,
                                                         m, s, rating, state)


if __name__ == "__main__":
    main()
