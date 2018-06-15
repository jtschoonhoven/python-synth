# coding: utf-8
from __future__ import absolute_import
from __future__ import division

import math
from abc import ABCMeta, abstractmethod

import attr
import six
from typing import TYPE_CHECKING
from six.moves import range

import helpers
from constants import ADSR_STATUS
from settings import SAMPLES_PER_SECOND

if TYPE_CHECKING:
    from typing import Any, Dict, Iterable, Tuple  # noqa


DEFAULT_ATTACK_MS = 10
DEFAULT_DECAY_MS = 10
DEFAULT_SUSTAIN_LEVEL = 127
DEFAULT_RELEASE_MS = 10


@attr.attrs(slots=True)
class Note(object):
    midi_note = attr.attrib()                                         # type: int
    velocity = attr.attrib(default=255)                               # type: int
    attack_ms = attr.attrib(default=DEFAULT_ATTACK_MS)                # type: int
    decay_ms = attr.attrib(default=DEFAULT_DECAY_MS)                  # type: int
    sustain_level = attr.attrib(default=DEFAULT_SUSTAIN_LEVEL)        # type: int
    release_ms = attr.attrib(default=DEFAULT_RELEASE_MS)              # type: int
    sample_generator = attr.attrib(init=None)                         # type: Iterablew[int]  # noqa
    # adsr_status describes the note lifecycle
    # 0=off; 1=attack; 2=decay; 3=sustain; 4=release
    adsr_status = attr.attrib(default=ADSR_STATUS['OFF'], init=None)  # type: int
    # adsr_sample_index is how long the note has been in its current status
    _adsr_sample_index = attr.attrib(default=0, init=None)            # type: int
    _num_attack_samples = attr.attrib(init=None)                      # type: int
    _num_decay_samples = attr.attrib(init=None)                       # type: int
    _num_release_samples = attr.attrib(init=None)                     # type: int

    def __attrs_post_init__(self, *args, **kwargs):
        # type: (*List[Any],  **Dict[Any]) -> None
        self._num_attack_samples = (self.attack_ms * SAMPLES_PER_SECOND) // 1000 or 1
        self._num_decay_samples = (self.decay_ms * SAMPLES_PER_SECOND) // 1000 or 1
        self._num_release_samples = (self.release_ms * SAMPLES_PER_SECOND) // 1000 or 1

    def set_adsr_status(self, adsr_status):
        # type: (str) -> None
        self.adsr_status = adsr_status
        self._adsr_sample_index = 0

    def incr_adsr_sample_index(self):
        # NOTE: the *processor* is responsible for setting "ATTACK" and "RELEASE"
        if self.adsr_status == ADSR_STATUS['ATTACK']:
            if self._adsr_sample_index == self._num_attack_samples:
                self.set_adsr_status(ADSR_STATUS['DECAY'])

        elif self.adsr_status == ADSR_STATUS['DECAY']:
            if self._adsr_sample_index == self._num_decay_samples:
                self.set_adsr_status(ADSR_STATUS['SUSTAIN'])

        elif self.adsr_status == ADSR_STATUS['RELEASE']:
            if self._adsr_sample_index == self._num_release_samples:
                self.set_adsr_status(ADSR_STATUS['OFF'])

        self._adsr_sample_index += 1

    def get_envelope_amplitude_multiplier(self):
        # type: () -> float
        if self.adsr_status == ADSR_STATUS['OFF']:
            return 0

        elif self.adsr_status == ADSR_STATUS['ATTACK']:
            env_multiplier = self._adsr_sample_index / self._num_attack_samples

        elif self.adsr_status == ADSR_STATUS['DECAY']:
            decay_percent = self._adsr_sample_index / self._num_decay_samples
            sustain_subtractor = (255 - self.sustain_level) * decay_percent
            env_multiplier = (255 - sustain_subtractor) / 255

        elif self.adsr_status == ADSR_STATUS['SUSTAIN']:
            env_multiplier = self.sustain_level / 255

        elif self.adsr_status == ADSR_STATUS['RELEASE']:
            release_percent = self._adsr_sample_index / self._num_release_samples
            release_subtractor = self.sustain_level * release_percent
            env_multiplier = (self.sustain_level - release_subtractor) / 255

        return env_multiplier


@attr.attrs(slots=True)
@six.add_metaclass(ABCMeta)
class Instrument(object):
    volume = attr.attrib(default=255)  # type: int

    @abstractmethod
    def get_note(self, midi_note, **kwargs):
        # type: (int, **Any) -> Note
        pass


@attr.attrs(slots=True)
class Synth(Instrument):
    ATTACK_MS = DEFAULT_ATTACK_MS
    DECAY_MS = DEFAULT_DECAY_MS
    SUSTAIN_LEVEL = DEFAULT_SUSTAIN_LEVEL
    RELEASE_MS = DEFAULT_RELEASE_MS

    def get_note(self, midi_note, **kwargs):
        # type: (int, **Any) -> Note
        note = Note(midi_note, **kwargs)

        def sample_generator():
            # type: (int, int) -> Iterable[int]
            cycles_per_second = helpers.midi_note_to_frequency(midi_note)
            samples_per_cycle = int(SAMPLES_PER_SECOND // cycles_per_second)

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
                    continue

                for sample_amplitude in sample_amplitude_array:
                    yield int(sample_amplitude * note.get_envelope_amplitude_multiplier())
                    note.incr_adsr_sample_index()

        note.sample_generator = sample_generator()

        return note
