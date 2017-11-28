import pyaudio
import pygame

from helpers import letter_note_to_midi_note

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

DEFAULT_SAMPLES_PER_SECOND = SAMPLES_PER_SECOND_OPTIONS['TELEPHONE_QUALITY']
DEFAULT_SAMPLE_BIT_DEPTH = SAMPLE_BIT_DEPTH_OPTIONS['8_BIT']
DEFAULT_SAMPLE_BYTE_WIDTH = DEFAULT_SAMPLE_BIT_DEPTH / BITS_PER_BYTE
DEFAULT_NUM_AUDIO_CHANNELS = 1  # e.g. 1=mono; 2=stereo
DEFAULT_POLYPHONY = 8  # num notes that can be played simultaneously
NOTE_OFF_SAMPLE_AMPLITUDE = int(2 ** (DEFAULT_SAMPLE_BYTE_WIDTH * BITS_PER_BYTE) / 2)

KEYBOARD_NOTE_MAPPING_QWERTY = {
    pygame.K_a: letter_note_to_midi_note('A4'),
    pygame.K_w: letter_note_to_midi_note('A#4'),
    pygame.K_s: letter_note_to_midi_note('B4'),
    pygame.K_d: letter_note_to_midi_note('C5'),
    pygame.K_r: letter_note_to_midi_note('C#5'),
    pygame.K_f: letter_note_to_midi_note('D5'),
    pygame.K_t: letter_note_to_midi_note('D#5'),
    pygame.K_g: letter_note_to_midi_note('E5'),
    pygame.K_h: letter_note_to_midi_note('F5'),
    pygame.K_u: letter_note_to_midi_note('F#5'),
    pygame.K_j: letter_note_to_midi_note('G5'),
    pygame.K_i: letter_note_to_midi_note('G#5'),
    pygame.K_k: letter_note_to_midi_note('A5'),
    pygame.K_o: letter_note_to_midi_note('A#5'),
    pygame.K_l: letter_note_to_midi_note('B5'),
    pygame.K_SEMICOLON: letter_note_to_midi_note('C6'),
    pygame.K_COLON: letter_note_to_midi_note('C6'),
    pygame.K_COLON: letter_note_to_midi_note('C6'),
    pygame.K_LEFTBRACKET: letter_note_to_midi_note('C6#'),
    pygame.K_QUOTEDBL: letter_note_to_midi_note('D6'),
    pygame.K_QUOTE: letter_note_to_midi_note('D6'),
}
