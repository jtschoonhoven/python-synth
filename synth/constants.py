import pyaudio


PYAUDIO = pyaudio.PyAudio()

BITS_PER_BYTE = 8

# https://en.wikipedia.org/wiki/Sampling_(signal_processing)#Sampling_rate
SAMPLES_PER_SECOND_OPTIONS = {
    'TELEPHONE_QUALITY': 16000,
    'RADIO_QUALITY': 32000,
    'DIGITAL_STANDARD': 48000,
    'DIGITAL_RECORDING_STANDARD': 96000,
    'HIGH_DEFINITION': 192000,
}

SAMPLE_BIT_DEPTH_OPTIONS = {
    '8_BIT': 8,
    '16_BIT': 16,
    '32_BIT': 32,
}

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

ADSR_STATUS = {
    'OFF': 0,
    'ATTACK': 1,
    'DECAY': 2,
    'SUSTAIN': 3,
    'RELEASE': 4,
}


# SDL enforces a maximum queue size that must be respected
EVENT_QUEUE_MAX_SIZE = 127

DEFAULT_SAMPLES_PER_SECOND = SAMPLES_PER_SECOND_OPTIONS['HIGH_DEFINITION']
DEFAULT_SAMPLE_BIT_DEPTH = SAMPLE_BIT_DEPTH_OPTIONS['8_BIT']
DEFAULT_SAMPLE_BYTE_WIDTH = DEFAULT_SAMPLE_BIT_DEPTH / BITS_PER_BYTE
DEFAULT_NUM_AUDIO_CHANNELS = 1  # e.g. 1=mono; 2=stereo
DEFAULT_POLYPHONY = 8  # num notes that can be played simultaneously
