import sys

import pygame

from python_synth.helpers import letter_note_to_midi_note
from python_synth.processor import Processor
from python_synth.synth import Synth


KEYBOARD_NOTE_MAPPING = {
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


def run():
    # () -> None
    pygame.display.init()  # for some reason pygame events depend on this module
    synth = Synth()
    processor = Processor()

    while True:
        event = pygame.event.wait()

        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        elif event.type == pygame.KEYDOWN:
            if event.key in KEYBOARD_NOTE_MAPPING:
                midi_note = KEYBOARD_NOTE_MAPPING[event.key]
                note = synth.get_note(midi_note)
                processor.note_on(note)

            elif event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                pygame.quit()
                sys.exit()

        elif event.type == pygame.KEYUP:
            if event.key in KEYBOARD_NOTE_MAPPING:
                midi_note = KEYBOARD_NOTE_MAPPING[event.key]
                note = synth.get_note(midi_note)
                processor.note_off(note)


if __name__ == '__main__':
    run()
