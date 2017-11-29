from __future__ import division

import functools
import math
import time
import random

import pyaudio
import six
from six.moves import range


BITS_PER_BYTE = 8  # for clarity
SAMPLE_BIT_DEPTH = 8  # i.e. each sample is 1 byte
SAMPLES_PER_SECOND = 192000  # "high def"

MIDDLE_C_HZ = 261.625565  # AKA "cycles per second"
MIDDLE_E_HZ = 329.63


def sine_generator(frequency_hz):
    # type: (float) -> int
    """
    Generate one complete cycle of the waveform, yielding one sample at a time.
    """
    sample_array = []  # type: List[int]
    samples_per_cycle = int(SAMPLES_PER_SECOND / frequency_hz)

    for sample_idx in range(samples_per_cycle):
        # "normalize" the index of this sample as a float between 0 and 1
        normalized_idx = sample_idx / samples_per_cycle
        # calculate the amplitude for this frame as a float between -1 and 1
        relative_amplitide = math.sin(normalized_idx * 2 * math.pi)
        # scale the amplitude to an integer between 0 and 255 (inclusive)
        scaled_amplitude = int(relative_amplitide * 127 + 128)
        # add amplitude to byte array
        sample_array.append(scaled_amplitude)

    while True:
        for sample in sample_array:
            yield sample


def octaves_generator(frequency):
    # type: (float) -> int
    num_octaves = 3
    sine_generators = []

    for octave in range(num_octaves):
        generator = sine_generator(frequency)
        sine_generators.append(generator)
        frequency *= 2

    while True:
        amplitudes_sum = 0

        for generator in sine_generators:
            amplitudes_sum += next(generator)

        yield int(amplitudes_sum / len(sine_generators))


def stream_callback(sample_generator, _, num_samples, *args):
    # type: (Iterable[int], None, int, *Any) -> Tuple[bytes, int]
    """
    Populates the buffer of a pyaudio.Stream. Called in a separate thread.
    """
    byte_array = bytearray()

    for _ in range(num_samples):
        sample = next(sample_generator)
        if six.PY2:
            sample = chr(sample)
        byte_array.append(sample)

    # cast to read-only bytes object
    byte_array = bytes(byte_array)

    return (byte_array, pyaudio.paContinue)


def play_notes():
    # type: () -> None
    streams = []
    audio = pyaudio.PyAudio()

    for _ in range(3):
        frequency_hz = random.random() * 1000 + 100
        sample_generator = octaves_generator(frequency_hz)
        cb = functools.partial(stream_callback, sample_generator)

        stream = audio.open(
            format=audio.get_format_from_width(SAMPLE_BIT_DEPTH / BITS_PER_BYTE),
            channels=1,
            rate=SAMPLES_PER_SECOND,
            output=True,
            stream_callback=cb,
        )

        streams.append(stream)

    for stream in streams:
        while stream.is_active():
            time.sleep(0.1)

        stream.stop_stream()
        stream.close()

        stream.stop_stream()
        stream.close()

    audio.terminate()


if __name__ == '__main__':
    play_notes()
