import cProfile
import io
import pstats
import time
from collections import deque

from python_synth.constants import LETTER_TO_MIDI_NOTE_MAP
from python_synth.processor import Processor
from python_synth.synth import Synth

NOTE_DELAY_SECONDS = 0.8
MAX_NOTES_ON = 8


def run():
    # type: () -> None
    processor = Processor()
    synth = Synth()
    notes_on = deque()

    for midi_note in LETTER_TO_MIDI_NOTE_MAP.values():
        if len(notes_on) == MAX_NOTES_ON:
            note = notes_on.popleft()
            processor.note_off(note)

        note = synth.get_note(midi_note)
        processor.note_on(note)
        notes_on.append(note)
        time.sleep(NOTE_DELAY_SECONDS)

    for note in notes_on:
        time.sleep(NOTE_DELAY_SECONDS)
        processor.note_off(note)


if __name__ == '__main__':
    profiler = cProfile.Profile()
    profiler.enable()
    run()
    profiler.disable()
    file_obj = io.StringIO()
    stats = pstats.Stats(profiler, stream=file_obj).sort_stats('cumulative')
    stats.print_stats()
    print(file_obj.getvalue())
