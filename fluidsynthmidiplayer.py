# -*- coding: utf-8 -*-

import re
import io
import os
import os.path
import sys
import time

from fluidsynthplayer import Player, Synth
from midiplayer import MidiPlayer


PY3 = sys.version_info.major > 2


class FluidSynthMidiPlayer(MidiPlayer):
    def __init__(self, sf2_path):
        super(FluidSynthMidiPlayer, self).__init__()
        self.synth = Synth(samplerate=48000)  # make a synth
        self.driver_name = 'jack' if sys.platform.startswith('linux') else 'dsound'
        self.synth.start(driver=self.driver_name)  # set default output driver and start clock
        self.sfid = self.synth.sfload(sf2_path)
        self.synth.program_select(0, self.sfid, 0, 0)
        self.player = Player(self.synth)  # make a new player
        self.duration_in_ticks = 0  # length of midi file
        self.pause_time = 0  # time in midi ticks where player stopped
        self.set_gain(0.7)

    def set_soundfont(self, sf2_path):
        """Load another sound font."""
        self.sf2 = sf2_path

        if self.sfid >= 0:
            self.synth.sfunload(self.sfid)

        self.sfid = self.synth.sfload(sf2_path)

        if self.sfid < 0:
            # not a sf2 file
            return 0

        self.synth.program_select(0, self.sfid, 0, 0)
        # resume playing at time == 0
        self.pause_time = 0
        return 1

    def Load(self, path):
        """Load a midi file."""
        self.reset()  # reset the player, empty the playlist
        self.pause_time  = 0  # resume playing at time == 0
        self.player.add(path)  # add file to playlist
        self.player.load()  # load first file from playlist

        if self.player.get_status() == 2:
            # not a midi file
            return False

        # get max length of all tracks
        self.duration_in_ticks = self.player.get_duration()
        return True

    def reset(self):
        """Reset the player.

        The only way to empty the playlist.

        """
        self.player.delete()  # delete player
        self.player = Player(self.synth)  # make a new one

    def Play(self):
        if self.is_playing:
            return
        self.player.play(self.pause_time)

    def Pause(self):
        if self.is_playing:
            self.pause_time = self.player.stop()

    def Stop(self):
        if self.is_playing:
            self.player.stop()
        self.pause_time = 0

    def Seek(self, time):
        """Seek to time (in midi ticks)."""
        if time > self.duration_in_ticks or time < 0:
            return
        ticks = self.player.seek(time)
        self.pause_time = time
        return ticks

    def Tell(self):
        """Get play position in midi ticks."""
        return self.player.get_ticks()

    def dispose(self):
        """Free resources."""
        self.player.delete()
        self.synth.delete()

    @property
    def is_playing(self):
        # 0 = ready, 1 = playing, 2 = finished
        return self.player.get_status() == 1

    @property
    def is_paused(self):
        return self.pause_time > 0

    def set_gain(self, gain):
        """Set gain between 0.0 and 1.0."""
        self.player.set_gain(gain)

    def Length(self):
        return self.duration_in_ticks
