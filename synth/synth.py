# coding: utf-8
from __future__ import absolute_import
from __future__ import division

import math
import threading
from abc import ABCMeta, abstractmethod

import attr
import six
from typing import TYPE_CHECKING
from six.moves import range

import helpers
from constants import (
    ADSR_STATUS,
    DEFAULT_SAMPLES_PER_SECOND,
    DEFAULT_SAMPLE_BYTE_WIDTH,
    DEFAULT_NUM_AUDIO_CHANNELS,
)

if TYPE_CHECKING:
    from typing import Any, Dict, Iterable, Tuple  # noqa


@attr.attrs(slots=True)
class Note(object):
    midi_note = attr.attrib()                              # type: int
    velocity = attr.attrib(default=255)                    # type: int
    # adsr_status describes the note lifecycle
    # 0=off; 1=attack; 2=decay; 3=sustain; 4=release
    adsr_status = attr.attrib(default=ADSR_STATUS['OFF'])  # type: int
    sample_generator = attr.attrib(init=None)              # type: Iterable[int]


@attr.attrs(slots=True)
@six.add_metaclass(ABCMeta)
class Instrument(object):
    NUM_AUDIO_CHANNELS = DEFAULT_NUM_AUDIO_CHANNELS
    SAMPLE_BYTE_WIDTH = DEFAULT_SAMPLE_BYTE_WIDTH
    SAMPLES_PER_SECOND = DEFAULT_SAMPLES_PER_SECOND

    volume = attr.attrib(default=255)  # type: int

    @abstractmethod
    def get_note(self, midi_note, **kwargs):
        # type: (int, **Any) -> Note
        pass


@attr.attrs(slots=True)
class Synth(Instrument):

    def get_note(self, midi_note, **kwargs):
        # type: (int, **Any) -> Note
        note = Note(midi_note, **kwargs)

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
                relative_amplitide = math.sin(normalized_idx * 2 * math.pi)
                # scale the amplitude to an integer between 0 and 255 (inclusive)
                scaled_amplitude = int(relative_amplitide * 127)
                # apply instrument volume
                volumized_amplitude = scaled_amplitude * (self.volume // 255)
                # apply note velocity
                velocitized_amplitude = volumized_amplitude * (note.velocity // 255)
                # add amplitude to byte array
                sample_amplitude_array.append(velocitized_amplitude)

            while True:
                if note.adsr_status == ADSR_STATUS['OFF']:
                    yield 0
                else:
                    for sample_amplitude in sample_amplitude_array:
                        yield sample_amplitude
                    if note.adsr_status == ADSR_STATUS['RELEASE']:
                        note.adsr_status = ADSR_STATUS['OFF']

        note.sample_generator = sample_generator()

        return note
