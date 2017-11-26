from __future__ import division
import math
import pyaudio
from six.moves import range


BITS_PER_BYTE = 8  # for clarity
SAMPLE_BIT_DEPTH = 8  # i.e. each sample is 1 byte
SAMPLES_PER_SECOND = 42100
NOTE_TIME_SECONDS = 1
MIDDLE_C_HZ = 261.625565  # AKA "cycles per second"

SAMPLES_PER_CYCLE = int(math.ceil(SAMPLES_PER_SECOND / MIDDLE_C_HZ))
NUM_SAMPLES = SAMPLES_PER_SECOND * NOTE_TIME_SECONDS
NUM_CYCLES = int(math.ceil(NUM_SAMPLES / SAMPLES_PER_CYCLE))


def play_note():
    audio = pyaudio.PyAudio()

    stream = audio.open(
        format=audio.get_format_from_width(SAMPLE_BIT_DEPTH / BITS_PER_BYTE),
        channels=1,
        rate=SAMPLES_PER_SECOND,
        output=True,
    )

    # byte_array will contain one complete cycle of the waveform
    byte_array = bytearray()

    for sample_idx in range(SAMPLES_PER_CYCLE):
        # "normalize" the index of this sample as a float between 0 and 1
        normalized_idx = sample_idx / SAMPLES_PER_CYCLE
        # calculate the amplitude for this frame as a float between -1 and 1
        relative_amplitide = math.sin(normalized_idx * 2 * math.pi)
        # scale the amplitude to an integer between 0 and 255 (inclusive)
        scaled_amplitude = int(relative_amplitide * 127 + 128)
        # add amplitude to byte array
        byte_array.append(scaled_amplitude)

    # make byte_array read-only so it's compatible with pyaudio
    byte_array = bytes(byte_array)

    for cycles in range(NUM_CYCLES):
        stream.write(byte_array)

    stream.close()
    audio.terminate()


if __name__ == '__main__':
    play_note()
