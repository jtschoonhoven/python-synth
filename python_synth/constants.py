import pyaudio

from python_synth.settings import SAMPLE_BIT_DEPTH


PYAUDIO = pyaudio.PyAudio()

BITS_PER_BYTE = 8

LETTER_TO_MIDI_NOTE_MAP = {
    'C': 60,
    'C#': 61,
    'D': 62,
    'D#': 63,
    'E': 64,
    'F': 65,
    'F#': 66,
    'G': 67,
    'G#': 68,
    'A': 69,
    'A#': 70,
    'B': 71,
}

NOTE_EVENTS = {
    'NOTE_ON': 0,
    'NOTE_OFF': 1,
}

KEY_STATUS = {
    'KEY_UP': 0,
    'KEY_DOWN': 1,
}

ADSR_STATUS = {
    'OFF': 0,
    'ATTACK': 1,
    'DECAY': 2,
    'SUSTAIN': 3,
    'RELEASE': 4,
}

# an "analogue" is an instrument setting that varies within a range e.g. velocity
# it's called an "analogue" because its use mimics an analogue dial or signal
ANALOGUE_MIN = 0
ANALOGUE_MAX = 256

AMPLITUDE_MIN = SAMPLE_BIT_DEPTH // -2
AMPLITUDE_MAX = SAMPLE_BIT_DEPTH // 2

# SDL enforces a maximum queue size that must be respected
SAMPLE_BYTE_WIDTH = SAMPLE_BIT_DEPTH / BITS_PER_BYTE
