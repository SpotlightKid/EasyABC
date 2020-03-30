#!/usr/bin/env python
"""Python bindings for FluidSynth MIDI Player

Released under the LGPL
Copyright 2012, Willem Vree

"""

import os
import sys
import time

from ctypes import c_char_p, c_double, c_int, c_void_p

from fluidsynth import Synth, cfunc

if sys.version_info.major > 2:
    def b(s):
        return s.encode("latin-1")
else:
    def b(s):
        return s

revModels = ['Model 1', 'Model 2', 'Model 3', 'Model 4', 'Model 5']
# room size (0.0-1.2), damping (0.0-1.0), width (0.0-100.0), level (0.0-1.0)
revmods = {k: v for k,v in zip(revModels, [(0.2, 0.0, 0.5, 0.9),
                                           (0.4, 0.2, 0.5, 0.8),
                                           (0.6, 0.4, 0.5, 0.7),
                                           (0.8, 0.7, 0.5, 0.6),
                                           (0.8, 0.0, 0.5, 0.5)])}

new_fluid_file_renderer = cfunc('new_fluid_file_renderer', c_void_p,
                                ('synth', c_void_p, 1))

new_fluid_player = cfunc('new_fluid_player', c_void_p,
                         ('synth', c_void_p, 1))

delete_fluid_file_renderer = cfunc('delete_fluid_file_renderer', c_void_p,
                                   ('dev', c_void_p, 1))

delete_fluid_player = cfunc('delete_fluid_player', c_void_p,
                            ('player', c_void_p, 1))

fluid_file_renderer_process_block = cfunc('delete_fluid_player', c_void_p,
                                          ('dev', c_void_p, 1))

fluid_file_set_encoding_quality = cfunc('fluid_file_set_encoding_quality', c_void_p,
                                        ('dev', c_void_p, 1),
                                        ('q', c_double, 1))

fluid_player_add = cfunc('fluid_player_add', c_int,
                         ('player', c_void_p, 1),
                         ('midifile', c_char_p, 1))

fluid_player_get_status = cfunc('fluid_player_get_status', c_int,
                                ('player', c_void_p, 1))

fluid_player_get_current_tick = cfunc('fluid_player_get_current_tick', c_int,
                                      ('player', c_void_p, 1))

fluid_player_join = cfunc('fluid_player_join', c_int,
                          ('player', c_void_p, 1))

fluid_player_play = cfunc('fluid_player_play', c_int,
                          ('player', c_void_p, 1))

fluid_player_seek = cfunc('fluid_player_seek', c_int,
                          ('player', c_void_p, 1),
                          ('ticks', c_int, 1))

fluid_player_stop = cfunc('fluid_player_stop', c_int,
                          ('player', c_void_p, 1))

fluid_player_get_total_ticks = cfunc('fluid_player_get_total_ticks', c_int,
                                     ('player', c_void_p, 1))


class Player(object):
    """Interface for the FluidSynth internal MIDI player."""

    def __init__(self, flsynth):
        self.flsynth = flsynth # an instance of class Synth
        self.player = new_fluid_player(self.flsynth.synth)

    def add(self, midifile):
        """Add midifile to the playlist."""
        fluid_player_add(self.player, b(midifile))

    def play(self, offset=0):
        """Start playing at time == offset in midi ticks."""
        ticks = self.seek(offset)
        fluid_player_play(self.player)
        #~ print 'cur ticks at play', ticks

    def stop(self):
        """Stop playing and return position in midi ticks."""
        fluid_player_stop(self.player)
        self.flsynth.all_notes_off(-1)  # -1 == all channels
        return self.get_ticks()

    def wait(self):
        """Wait until player is finished."""
        fluid_player_join(self.player)

    def get_status(self):
        """Get player status.

        1 == playing, 2 == player finished

        """
        return fluid_player_get_status(self.player)

    def get_ticks(self):
        """Get current position in midi ticks."""
        t = fluid_player_get_current_tick(self.player)
        return t

    def seek(self, ticks_p):
        """Go to position ticks_p (in midi ticks)."""
        self.flsynth.all_notes_off(-1)  # -1 == all channels
        ticks = fluid_player_seek(self.player, ticks_p)
        return ticks

    def seekW(self, ticks_p):
        """Go to position ticks_p (in midi ticks) and wait until seeked."""
        self.flsynth.all_notes_off(-1)   # -1 == all channels
        ticks = fluid_player_seek(self.player, ticks_p)
        n = 0
        while abs(ticks - ticks_p) > 100 and n < 100:
            time.sleep(0.01)
            ticks = self.get_ticks()
            n += 1          # time out after 1 sec
        return ticks

    def load(self):
        """Load a midi file from the playlist (to determine its length)."""
        pass

    def get_duration(self):
        """Get duration of a midi track in ticks."""
        return fluid_player_get_total_ticks(self.player)

    def delete(self):
        delete_fluid_player(self.player)

    def renderLoop(self, quality = 0.5, callback=None):
        """Render midi file to audio file."""
        renderer = new_fluid_file_renderer(self.flsynth.synth)
        if not renderer:
            print('failed to create file renderer')
            return

        fluid_file_set_encoding_quality(renderer, quality)
        # get block size (samples are rendered one block at a time)
        k = self.flsynth.settings('audio.period-size')
        n = 0  # sample counter
        while self.get_status() == 1:
            # render one block
            if fluid_file_renderer_process_block(renderer) != 0:
                print('renderer_loop error')
                break

            # increment with period size
            n += k
            if callback:
                # for progress reporting
                callback(n)

        delete_fluid_file_renderer(renderer)
        return n

    def set_render_mode(self, file_name, file_type):
        """Set audio file and audio type.

        Should be called before the renderLoop.

        """
        st = self.flsynth.setting
        st("audio.file.name", file_name)
        st("audio.file.type", file_type)
        st("player.timing-source", "sample")
        st("synth.parallel-render", 1)

    def set_reverb(self, name):
        """Change reverb model parameters."""
        roomsize, damp, width, level = revmods.get(name, revmods [name])
        self.flsynth.set_reverb(roomsize, damp, width, level)

    def set_chorus(self, nr, level, speed, depth_ms, type):
        """Change chorus model pararmeters."""
        self.flsynth.set_chorus(nr, level, speed, depth_ms, type)

    def set_reverb_level(self, newlev):
        """Set reverb level 0-127 on all midi channels."""
        self.flsynth.set_reverb_level(newlev)

    def set_chorus_level(self, newlev):
        """Set chorus level 0-127 on all midi channels."""
        self.flsynth.set_chorus_level(newlev)

    def set_gain(self, gain):
        """Set master volume 0-10."""
        self.flsynth.setting('synth.gain', gain)
