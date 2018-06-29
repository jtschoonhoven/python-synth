# coding: utf-8
from __future__ import division

from functools import wraps
from threading import Thread

import pyaudio
import six
from six import PY2
from six.moves import queue


from python_synth import constants
from python_synth.settings import AUDIO_STREAM_CHUNK_SIZE, BUFFER_MS, SAMPLES_PER_SECOND


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


def get_samples(sample_generator, num_samples):
    # type: (Iterable[int], int) -> Iterator[int]
    for _ in range(num_samples):
        sample_amplitude = next(sample_generator)
        yield sample_amplitude


def fill_buffer(buf, sample_generator, chunk_size):
    # type: (queue.Queue, int) -> None
    while True:
        sample_iterator = get_samples(sample_generator, chunk_size)
        if PY2:
            chunk = ''.join(chr(sample) for sample in sample_iterator)
        else:
            chunk = bytes(sample_iterator)
        buf.put(chunk, block=True)


def get_pyaudio_stream(
    samples_per_second,  # type: int
    sample_byte_width,   # type: int
    num_audio_channels,  # type: int
    sample_generator,    # type: Callable[Iterator]
):
    # type: (...) -> pyaudio.Stream
    sample_generator = sample_generator()

    buffer_samples = int(SAMPLES_PER_SECOND * (BUFFER_MS / 1000.0)) or 1
    buffer_chunks = (buffer_samples // AUDIO_STREAM_CHUNK_SIZE) or 1
    chunk_buffer = queue.Queue(maxsize=buffer_chunks)

    # populate buffer in a separate thread
    thread = Thread(
        target=fill_buffer,
        args=(chunk_buffer, sample_generator, AUDIO_STREAM_CHUNK_SIZE),
    )
    thread.daemon = True
    thread.start()

    def stream_callback(_, num_samples, *args):
        # type: (None, int, *Any) -> Tuple[bytes, int]
        chunk = chunk_buffer.get(block=True)
        return (chunk, pyaudio.paContinue)

    stream = constants.PYAUDIO.open(
        rate=samples_per_second,
        format=constants.PYAUDIO.get_format_from_width(sample_byte_width),
        channels=num_audio_channels,
        output=True,
        stream_callback=stream_callback,
        frames_per_buffer=AUDIO_STREAM_CHUNK_SIZE,
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
