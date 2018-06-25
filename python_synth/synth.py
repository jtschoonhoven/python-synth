# coding: utf-8
from __future__ import division

import math
import random
from abc import ABCMeta, abstractmethod

import attr
import six
from typing import NamedTuple, TYPE_CHECKING
from six.moves import range

from python_synth import helpers
from python_synth.constants import ADSR_STATUS, ANALOGUE_MAX
from python_synth.exceptions import SynthError
from python_synth.settings import SAMPLES_PER_SECOND
from python_synth.validators import validate_analogue, validate_milliseconds

if TYPE_CHECKING:
    from typing import Any, Dict, Iterable, Tuple  # noqa


DEFAULT_ATTACK_MS = 100
DEFAULT_DECAY_MS = 100
DEFAULT_RELEASE_MS = 100
DEFAULT_SUSTAIN_LEVEL = 200


"""
A Note object produces a stream of NoteSamples. A sample is generally described only
by its amplitude, but when combining multiple samples one must also know the *volume*
of each. The result amplitude is a weighted average of individual amplitudes weighted
by the volume.

NOTE: instantiating a NamedTuple is 2X slower than a builtin tuple. The added clarity
is worth it for now, but should be changed in a future optimization.
"""
NoteSample = NamedTuple(
    'NoteSample',
    [
        ('amplitude', int),  # int between SAMPLE_BIT_DEPTH/-2 and SAMPLE_BIT_DEPTH/2
        ('volume', int),     # int between ANALOG_MIN and ANALOG_MAX
    ],
)


@attr.s(slots=True, hash=True)
class Note(object):
    """
    A Note is an iterator that returns NoteSamples. There will be one Note for every time
    a key is pressed on the keyboard.

    Note objects should only be created via the `get_note` method on an Instrument class.
    It is the Instrument's job to provision the Note with a `sample_generator`.

    Keep in mind that any mutable attribute in the class *must* be excluded from
    comparison with cmp=False, or else the class won't hash properly.

    # TODO: add support for velocity (and decide how it links to ADSR)
    """
    midi_note = attr.ib()  # type: int
    sample_generator = attr.ib(
        repr=None,
        cmp=False,
    )  # type: Iterable[int]

    # adsr public methods
    attack_ms = attr.ib(
        default=DEFAULT_ATTACK_MS,
        validator=validate_milliseconds,
    )  # type: int
    decay_ms = attr.ib(
        default=DEFAULT_DECAY_MS,
        validator=validate_milliseconds,
    )  # type: int
    release_ms = attr.ib(
        default=DEFAULT_RELEASE_MS,
        validator=validate_milliseconds,
    )  # type: int
    sustain_level = attr.ib(
        default=DEFAULT_SUSTAIN_LEVEL,
        validator=validate_analogue,
    )  # type: int

    # private attributes set on initialization
    _sample_idx = attr.ib(init=None, cmp=False)          # type: int
    _release_sample_idx = attr.ib(init=None, cmp=False)  # type: int
    _volume = attr.ib(init=None, cmp=False)              # type: int
    _adsr_status = attr.ib(init=None, cmp=False)         # type: int

    # computed volume envelopes
    _sample_idx_volume_map = attr.ib(
        init=None,
        repr=None,
        cmp=False,
    )  # type: Dict[int, int]
    _release_sample_idx_volume_map = attr.ib(
        init=None,
        repr=None,
        cmp=False,
    )  # type: Dict[int, int]

    # ADSR constants
    _num_attack_samples = attr.ib(init=None, repr=None, cmp=False)   # type: int
    _num_decay_samples = attr.ib(init=None, repr=None, cmp=False)    # type: int
    _num_release_samples = attr.ib(init=None, repr=None, cmp=False)  # type: int
    _decay_start_idx = attr.ib(init=None, repr=None, cmp=False)      # type: int
    _sustain_start_idx = attr.ib(init=None, repr=None, cmp=False)    # type: int

    def __attrs_post_init__(self, *args, **kwargs):
        """
        Set private attributes.
        """
        # type: (*List[Any],  **Dict[Any]) -> None
        self._sample_idx = 0
        self._release_sample_idx = 0
        self._volume = 0
        self._adsr_status = ADSR_STATUS['OFF']

        # precalculate useful ADSR values
        self._num_attack_samples = (self.attack_ms * SAMPLES_PER_SECOND) // 1000
        self._num_decay_samples = (self.decay_ms * SAMPLES_PER_SECOND) // 1000
        self._num_release_samples = (self.release_ms * SAMPLES_PER_SECOND) // 1000
        self._decay_start_idx = self._num_attack_samples + 1
        self._sustain_start_idx = self._decay_start_idx + self._num_decay_samples

        # precompute volume envelope changes
        self._sample_idx_volume_map = self._get_sample_idx_volume_map(
            self._num_attack_samples,
            self._num_decay_samples,
            self.sustain_level,
        )
        self._release_sample_idx_volume_map = {}

    def __iter__(self):
        """
        Implementing __iter__ defines this class as an iterator.
        """
        # type: () => Note
        return self

    def __next__(self):
        """
        For Python 2 compatibility. Alias of self.next.
        """
        # type: () -> NoteSample
        return self.next()

    def __hash__(self):
        """
        Notes are always unique: return a random 64-bit integer.
        """
        # type: () -> int
        return random.randint(0, 2**64)

    def set_key_down(self):
        """
        Activate note when keyboard key is pressed.
        This must be called *before* iterating through samples.
        """
        # type: () -> None
        self._adsr_status = ADSR_STATUS['ATTACK']

    def set_key_up(self):
        """
        Release note when keyboard key is raised.
        """
        # type: () -> None
        self._adsr_status = ADSR_STATUS['RELEASE']
        self._release_sample_idx_volume_map = self._get_release_sample_idx_volume_map(
            self.release_ms,
            self._volume,
        )

    def next(self):
        """
        Return the next NoteSample or raise StopIteration.
        """
        # type: () -> NoteSample
        sample = next(self.sample_generator)
        volume = self._volume

        # increment indices
        if self._adsr_status == ADSR_STATUS['RELEASE']:
            self._release_sample_idx += 1
        self._sample_idx += 1

        # update ADSR status for next iteration
        next_adsr_status = self._get_new_adsr_status(
            self._adsr_status,
            self._sample_idx,
            self._release_sample_idx,
            self._decay_start_idx,
            self._sustain_start_idx,
            self._num_release_samples,
        )
        if next_adsr_status is not None:
            self._adsr_status = next_adsr_status
            if next_adsr_status == ADSR_STATUS['OFF']:
                raise StopIteration()

        # update volume for next iteration
        next_volume = self._get_new_volume(
            self._sample_idx,
            self._release_sample_idx,
            self._sample_idx_volume_map,
            self._release_sample_idx_volume_map,
            self._adsr_status,
            self.sustain_level,
        )
        if next_volume is not None:
            self._volume = next_volume

        return NoteSample(sample, volume)

    @staticmethod
    def _get_new_volume(
        sample_idx,                     # type: int
        release_sample_idx,             # type: int
        sample_idx_volume_map,          # type: Dict[int, int]
        release_sample_idx_volume_map,  # type: Dict[int, int]
        adsr_status,                    # type: int
        sustain_level,                  # type: int
    ):
        """
        Return the volume for the given sample index.
        """
        # type: (...) -> Optional[int]
        if sample_idx in sample_idx_volume_map:
            return sample_idx_volume_map[sample_idx]

        if release_sample_idx in release_sample_idx_volume_map:
            return release_sample_idx_volume_map[release_sample_idx]

        if adsr_status == ADSR_STATUS['OFF']:
            raise SynthError('volume cannot change while note is off')

    @staticmethod
    def _get_new_adsr_status(
        old_adsr_status,      # type: int
        sample_idx,           # type: int
        release_sample_idx,   # type: int
        decay_start_idx,      # type: int
        sustain_start_idx,    # type: int
        num_release_samples,  # type: int
    ):
        """
        Return the ADSR status for the given sample index.
        """
        # type: (...) -> int
        if old_adsr_status == ADSR_STATUS['ATTACK']:
            if sample_idx == decay_start_idx:
                return ADSR_STATUS['DECAY']

        if old_adsr_status == ADSR_STATUS['DECAY']:
            if sample_idx == sustain_start_idx:
                return ADSR_STATUS['SUSTAIN']

        if old_adsr_status == ADSR_STATUS['RELEASE']:
            if release_sample_idx == num_release_samples:
                return ADSR_STATUS['OFF']

        if old_adsr_status == ADSR_STATUS['OFF']:
            raise SynthError('ADSR cannot change while note is off')

    @staticmethod
    def _get_sample_idx_volume_map(num_attack_samples, num_decay_samples, sustain_level):
        # type: (int, int, int) -> Dict[int, int]
        """
        Return a dict of {sample_idx: volume} where each entry represents a volume change
        at the given sample. Anything that can be precomputed, should be, this included.

        # TODO: make this nonlinear
        """
        volume_map = {}  # Dict[int, int]
        attack_sustain_volume_diff = ANALOGUE_MAX - sustain_level

        # case: attack has more samples than volume changes
        if num_attack_samples > ANALOGUE_MAX:
            samples_per_volume_increase = num_attack_samples // ANALOGUE_MAX

            for volume in range(ANALOGUE_MAX + 1):
                sample_idx = volume * samples_per_volume_increase
                volume_map[sample_idx] = volume

        # case: attack has fewer samples than volume changes
        else:
            volume_increase_per_sample = ANALOGUE_MAX // num_attack_samples

            for sample_idx in range(num_attack_samples):
                volume = sample_idx * volume_increase_per_sample
                volume_map[sample_idx] = volume

        # case: no decay
        if attack_sustain_volume_diff == 0:
            return volume_map

        # case: decay has more samples than volume changes
        if num_decay_samples > attack_sustain_volume_diff:
            samples_per_volume_decrease = num_decay_samples // attack_sustain_volume_diff

            for volume in range(ANALOGUE_MAX, sustain_level - 1, -1):
                decay_idx = samples_per_volume_decrease * (ANALOGUE_MAX - volume)
                sample_idx = decay_idx + num_attack_samples
                volume_map[sample_idx] = volume

        # case: decay has fewer samples than volume changes
        else:
            volume_decrease_per_sample = attack_sustain_volume_diff // num_decay_samples

            for sample_idx in range(num_decay_samples):
                volume = ANALOGUE_MAX - (sample_idx * volume_decrease_per_sample)
                volume_map[sample_idx] = volume

        return volume_map

    @staticmethod
    def _get_release_sample_idx_volume_map(release_ms, start_volume):
        """
        Return a dict of {sample_idx: volume} where each entry represents a volume change
        at the given sample. This cannot be computed until the KEY_UP event is received.

        # TODO: make this nonlinear
        """
        # type: (int, int) -> Dict[int, int]
        volume_map = {}  # Dict[int, int]
        num_release_samples = (release_ms * SAMPLES_PER_SECOND) // 1000

        # no further changes needed if volume is already at 0
        if start_volume == 0:
            return volume_map

        # release: more samples than volume changes
        if num_release_samples > start_volume:
            samples_per_volume_decrease = num_release_samples // start_volume

            for volume in range(start_volume, -1, -1):
                sample_idx = samples_per_volume_decrease * (start_volume - volume)
                volume_map[sample_idx] = volume

        # release: fewer samples than volume changes
        else:
            volume_decrease_per_sample = start_volume // num_release_samples

            for sample_idx in range(num_release_samples):
                volume = start_volume - (sample_idx * volume_decrease_per_sample)
                volume_map[sample_idx] = volume

        return volume_map


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

    @staticmethod
    def get_note(midi_note, **kwargs):
        # type: (int, **Any) -> Note

        @helpers.simple_cache
        def sample_generator(midi_note):
            # type: () -> Iterable[int]
            sample_amplitude_array = []  # type: List[int]
            cycles_per_second = helpers.midi_note_to_frequency(midi_note)
            samples_per_cycle = int(SAMPLES_PER_SECOND // cycles_per_second)

            for sample_idx in range(samples_per_cycle):
                # "normalize" the idx of this sample as a float between 0 and 1
                normalized_idx = sample_idx / samples_per_cycle
                # calculate the amplitude for this frame as a float between -1 and 1
                # NOTE: this could be approximated for better performance
                relative_amplitide = math.sin(normalized_idx * 2 * math.pi)
                # scale the amplitude to an integer between 0 and 255 (inclusive)
                scaled_amplitude = int(relative_amplitide * 127)
                # add amplitude to byte array
                sample_amplitude_array.append(scaled_amplitude)

            while True:
                for sample_amplitude in sample_amplitude_array:
                    yield sample_amplitude

        return Note(midi_note, sample_generator(midi_note), **kwargs)
