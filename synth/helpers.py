# coding: utf-8
from __future__ import absolute_import
from __future__ import division

from functools import wraps

import pyaudio
import six

import constants


def simple_cache(func):
    # type: (Callable[*Any, **Any]) -> Callable[*Any, **Any]
    """
    A simple (i.e. stupid) unbounded cache.
    Raises TypeError if any argument is unhashable.
    """
    cache = {}

    @wraps(func)
    def decorated_function(*args, **kwargs):
        # type: (*Any, **Any) -> Any
        cache_key = 0

        # stupidly generate a "unique" cache key from arguments
        for arg in args:
            cache_key += hash(arg)
        for _, kwarg in six.iteritems(kwargs):
            cache_key += hash(kwarg)

        # return value from cache if available
        if cache.get(cache_key):
            return cache[cache_key]

        # store value in cache before returning
        return_value = func(*args, **kwargs)
        cache[cache_key] = return_value
        return return_value

    return decorated_function


def get_pyaudio_stream(
    samples_per_second,  # type: int
    sample_byte_width,   # type: int
    num_audio_channels,  # type: int
    sample_generator,    # type: Callable[Iterator]
):
    # type: (...) -> pyaudio.Stream
    generator = sample_generator()

    def stream_callback(_, num_samples, *args):
        # type: (None, int, *Any) -> Tuple[bytes, int]
        def _int_iterator():
            # type: () -> int
            for _ in range(num_samples):
                sample_amplitude = next(generator)
                yield sample_amplitude

        if six.PY2:
            byte_array = ''.join(chr(sample) for sample in _int_iterator())
        else:
            byte_array = bytes(_int_iterator())

        return (byte_array, pyaudio.paContinue)

    stream = constants.PYAUDIO.open(
        rate=samples_per_second,
        format=constants.PYAUDIO.get_format_from_width(sample_byte_width),
        channels=num_audio_channels,
        output=True,
        stream_callback=stream_callback,
    )
    return stream


@simple_cache
def midi_note_to_frequency(midi_note):
    # type: (int) -> float
    # http://glassarmonica.com/science/frequency_midi.php
    frequency_hertz = 27.5 * (2 ** ((midi_note - 21) / 12))
    return frequency_hertz


@simple_cache
def letter_note_to_midi_note(letter_note):
    # type: (str) -> int
    note_part = iter(letter_note)
    base_note = next(note_part).upper()
    midi_note = constants.LETTER_TO_MIDI_NOTE_MAP[base_note]

    for modifier in note_part:
        if modifier in ('b', '♭'):
            midi_note -= 1
        elif modifier in ('#', '♯'):
            midi_note += 1
        else:
            octave = int(modifier)
            # C5 is "middle-C" so no adjustment is needed for C5
            # otherwise octaves are 12 notes apart
            difference = (12 * octave) - (12 * 5)
            midi_note += difference

    return midi_note
