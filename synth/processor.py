# coding: utf-8
from __future__ import absolute_import
from __future__ import division

import attr
import functools
from collections import deque

from typing import TYPE_CHECKING

import helpers
from constants import ADSR_STATUS, NOTE_EVENTS, SAMPLE_BYTE_WIDTH
from settings import EVENT_QUEUE_MAX_SIZE, NUM_AUDIO_CHANNELS, SAMPLES_PER_SECOND

if TYPE_CHECKING:
    from typing import Any, Dict, Iterable, Tuple  # noqa


@attr.attrs(slots=True, frozen=True)
class NoteEvent(object):
    event_type = attr.attrib()  # type: str
    note = attr.attrib()        # type: Note


@attr.attrs(slots=True)
class Processor(object):

    __weakref__ = attr.ib(init=False, hash=False, repr=False, cmp=False)

    _stream = attr.attrib(init=False)
    _notes_event_queue = attr.attrib(  # type: deque
        init=False,
        default=attr.Factory(functools.partial(deque, maxlen=EVENT_QUEUE_MAX_SIZE)),
    )
    _notes = attr.attrib(  # type: Dict[int, Note]
        init=False,
        default=attr.Factory(dict),
    )

    def __attrs_post_init__(self, *args, **kwargs):
        # type: (*List[Any],  **Dict[Any]) -> None
        self._stream = helpers.get_pyaudio_stream(
            SAMPLES_PER_SECOND,
            SAMPLE_BYTE_WIDTH,
            NUM_AUDIO_CHANNELS,
            self.sample_generator,
        )

    def note_on(self, note):
        # type: (Note) -> None
        note_on_event = NoteEvent(event_type=NOTE_EVENTS['NOTE_ON'], note=note)
        self._notes_event_queue.append(note_on_event)

    def note_off(self, note):
        # type: (Note) -> None
        note_off_event = NoteEvent(event_type=NOTE_EVENTS['NOTE_OFF'], note=note)
        self._notes_event_queue.append(note_off_event)

    def sample_generator(self):
        # type: () -> Iterable[int]
        notes_on = set()  # type: Set[int]
        dead_notes = set()  # type: Set[int]

        while True:
            num_amplitudes = 0
            amplitudes_sum = 0

            # process the note event queue
            while self._notes_event_queue:
                note_event = self._notes_event_queue.popleft()

                if note_event.event_type == NOTE_EVENTS['NOTE_ON']:
                    note = note_event.note
                    note.set_adsr_status(ADSR_STATUS['ATTACK'])
                    self._notes[note.midi_note] = note_event.note
                    notes_on.add(note.midi_note)

                if note_event.event_type == NOTE_EVENTS['NOTE_OFF']:
                    note = self._notes[note_event.note.midi_note]
                    note.set_adsr_status(ADSR_STATUS['RELEASE'])

            # clear any notes that have ended
            for midi_note in dead_notes:
                notes_on.discard(midi_note)
            dead_notes.clear()

            # then play each active note
            for midi_note in notes_on:
                note = self._notes[midi_note]
                sample_amplitude = next(note.sample_generator)

                if note.adsr_status == ADSR_STATUS['OFF']:
                    dead_notes.add(midi_note)

                num_amplitudes += 1
                amplitudes_sum += sample_amplitude

            if num_amplitudes:
                combined_samples = amplitudes_sum / num_amplitudes
                scaled_amplitude = int(combined_samples * 127) + 127
                yield scaled_amplitude
            else:
                yield 127
