# coding: utf-8
from __future__ import absolute_import
from __future__ import division

import functools
import math
import sys
import threading
from abc import ABCMeta, abstractmethod
from collections import deque

import attr
import pygame
import six
from typing import TYPE_CHECKING
from six.moves import range

import constants
import helpers
from constants import EVENT_QUEUE_MAX_SIZE, NOTE_EVENTS

if TYPE_CHECKING:
    from typing import Any, Dict, Iterable, Tuple  # noqa


@attr.attrs(slots=True)
class Note(object):
    midi_note = attr.attrib()                  # type: int
    volume = attr.attrib(default=100)          # type: int
    velocity = attr.attrib(default=255)        # type: int
    status = attr.attrib(default=0)            # type: int  # 0=off; 1=pressed; 2=decay;
    is_active = attr.attrib(default=False)     # type: bool
    sample_generator = attr.attrib(init=None)  # type: Iterable[int]


@attr.attrs(slots=True, frozen=True)
class NoteEvent(object):
    event_type = attr.attrib()  # type: str
    note = attr.attrib()        # type: Note


@attr.attrs(slots=True)
@six.add_metaclass(ABCMeta)
class Instrument(object):
    SAMPLES_PER_SECOND = constants.DEFAULT_SAMPLES_PER_SECOND
    SAMPLE_BYTE_WIDTH = constants.DEFAULT_SAMPLE_BYTE_WIDTH
    NUM_AUDIO_CHANNELS = constants.DEFAULT_NUM_AUDIO_CHANNELS

    _notes = attr.attrib(  # type: Dict[int, Note]
        init=False,
        default=attr.Factory(dict),
    )
    _notes_lock = attr.attrib(  # type: threading.Lock
        init=False,
        default=attr.Factory(threading.Lock),
    )
    _notes_event_queue = attr.attrib(  # type: deque
        init=False,
        default=attr.Factory(functools.partial(deque, maxlen=EVENT_QUEUE_MAX_SIZE)),
    )

    @abstractmethod
    def note_on(self, note):
        # type: (Note) -> None
        pass

    @abstractmethod
    def note_off(self, note):
        # type: (Note) -> None
        pass

    @abstractmethod
    def sample_generator(self):
        # type: () -> Callable[Iterator]
        pass

    @abstractmethod
    def get_note(self, midi_note, volume=None, velocity=None):
        # type: (int, Optional[int], Optional[int]) -> Note
        pass


@attr.attrs(slots=True)
class Synth(Instrument):
    NUM_AUDIO_CHANNELS = 1  # e.g. 1=mono; 2=stereo
    POLYPHONY = constants.DEFAULT_POLYPHONY

    stream = attr.attrib(init=False)
    __weakref__ = attr.ib(init=False, hash=False, repr=False, cmp=False)

    def __attrs_post_init__(self, *args, **kwargs):
        # type: (*List[Any],  **Dict[Any]) -> None
        self.stream = helpers.get_pyaudio_stream(
            self.SAMPLES_PER_SECOND,
            self.SAMPLE_BYTE_WIDTH,
            self.NUM_AUDIO_CHANNELS,
            self.sample_generator,
        )

        # initialize all possible notes
        for midi_note in range(256):
            self._notes[midi_note] = self.get_note(midi_note)

    def note_on(self, note):
        # type: (Note) -> None
        note_on_event = NoteEvent(event_type=NOTE_EVENTS['NOTE_ON'], note=note)
        self._notes_event_queue.append(note_on_event)

    def note_off(self, note):
        # type: (Note) -> None
        note_off_event = NoteEvent(event_type=NOTE_EVENTS['NOTE_OFF'], note=note)
        self._notes_event_queue.append(note_off_event)

    def get_note(self, midi_note, volume=None, velocity=None):
        # type: (int, Optional[int], Optional[int]) -> Note
        note = self._notes.get(midi_note)

        if note is None:
            note = Note(midi_note)
        if volume is not None:
            note.volume = volume
        if velocity is not None:
            note.velocity = velocity

        def sample_generator():
            # type: (int, int) -> Iterable[int]
            cycles_per_second = helpers.midi_note_to_frequency(midi_note)
            samples_per_cycle = int(self.SAMPLES_PER_SECOND / cycles_per_second)

            sample_amplitude_array = []  # type: List[int]

            for sample_idx in range(samples_per_cycle):
                # "normalize" the index of this sample as a float between 0 and 1
                normalized_idx = sample_idx / samples_per_cycle
                # calculate the amplitude for this frame as a float between -1 and 1
                # NOTE: this could be approximated for better performance
                relative_amplitide = math.cos(normalized_idx * 2 * math.pi) * -1
                # scale the amplitude to an integer between 0 and 255 (inclusive)
                scaled_amplitude = int(relative_amplitide * 127 + 128)
                # add amplitude to byte array
                sample_amplitude_array.append(scaled_amplitude)

            while True:
                if note.status == 0:
                    yield 0
                else:
                    for sample_amplitude in sample_amplitude_array:
                        yield sample_amplitude
                    if note.status == 2:
                        note.status = 0  # turn note off at end of cycle

        note.sample_generator = sample_generator()

        return note

    def sample_generator(self):
        # type: () -> Iterable[int]
        notes_on = set()  # type: Set[int]
        dead_notes = set()  # type: Set[int]

        while True:
            num_amplitudes = 0
            amplitudes_sum = 0

            # first process the note event queue
            while self._notes_event_queue:
                note_event = self._notes_event_queue.popleft()

                if note_event.event_type == NOTE_EVENTS['NOTE_ON']:
                    note = self._notes[note_event.note.midi_note]
                    note.status = 1
                    notes_on.add(note.midi_note)

                if note_event.event_type == NOTE_EVENTS['NOTE_OFF']:
                    note = self._notes[note_event.note.midi_note]
                    note.status = 2

            for midi_note in dead_notes:
                notes_on.discard(midi_note)
            dead_notes.clear()

            # then play each active note
            for midi_note in notes_on:
                note = self._notes[midi_note]
                sample_amplitude = next(note.sample_generator)

                if note.status == 0:
                    dead_notes.add(midi_note)

                if note.volume:
                    sample_amplitude = sample_amplitude * (note.volume / 255)

                num_amplitudes += 1
                amplitudes_sum += sample_amplitude

            if num_amplitudes:
                combined_samples = int(amplitudes_sum / num_amplitudes)
                yield combined_samples
            else:
                yield 0


def profile(num_runs):
    synth = Synth()
    sample_generator = synth.sample_generator()

    for idx in range(16):
        note = Note(idx)
        synth.note_on(note)

    for run in range(num_runs):
        next(sample_generator)


if __name__ == '__main__':  # noqa
    import argparse
    parser = argparse.ArgumentParser(description='TODO')
    parser.add_argument('--profile', '-p', action='store_true')
    args = parser.parse_args()

    if args.profile:
        import cProfile
        cProfile.run('profile(100000)')
        sys.exit()

    pygame.display.init()  # for some reason pygame events depend on this module
    synth = Synth()

    while True:
        event = pygame.event.wait()

        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        elif event.type == pygame.KEYDOWN:
            if event.key in constants.KEYBOARD_NOTE_MAPPING_QWERTY:
                midi_note = constants.KEYBOARD_NOTE_MAPPING_QWERTY[event.key]
                note = Note(midi_note, volume=255)
                synth.note_on(note)

            elif event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                pygame.quit()
                sys.exit()

        elif event.type == pygame.KEYUP:
            if event.key in constants.KEYBOARD_NOTE_MAPPING_QWERTY:
                midi_note = constants.KEYBOARD_NOTE_MAPPING_QWERTY[event.key]
                note = Note(midi_note)
                synth.note_off(note)
