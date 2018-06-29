# coding: utf-8
from __future__ import division

import attr
import functools
from collections import deque

from typing import TYPE_CHECKING

from python_synth import helpers
from python_synth.constants import ANALOGUE_MAX, NOTE_EVENTS, SAMPLE_BYTE_WIDTH
from python_synth.settings import (
    EVENT_QUEUE_MAX_SIZE,
    NUM_AUDIO_CHANNELS,
    SAMPLES_PER_SECOND,
)

if TYPE_CHECKING:
    from typing import Any, Dict, Iterable, Tuple  # noqa


@attr.attrs(slots=True, frozen=True)
class NoteEvent(object):
    event_type = attr.attrib()  # type: str
    note = attr.attrib()        # type: Note


@attr.attrs
class Processor(object):
    """
    The Processor collects and manages Note objects and processes them to generate a
    stream of samples.
    """

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
        """
        Add a new Note to the queue.
        """
        # type: (Note) -> None
        note_on_event = NoteEvent(event_type=NOTE_EVENTS['NOTE_ON'], note=note)
        self._notes_event_queue.append(note_on_event)

    def note_off(self, note):
        """
        Schedule an existing Note to be removed from the queue.
        """
        # type: (Note) -> None
        note_off_event = NoteEvent(event_type=NOTE_EVENTS['NOTE_OFF'], note=note)
        self._notes_event_queue.append(note_off_event)

    def sample_generator(self):
        """
        Loop through active notes and generate a stream of samples.
        """
        # type: () -> Iterable[int]
        notes_on = set()  # type: Set[Note]
        dead_notes = set()  # type: Set[Note]

        while True:
            sample_volume_max = 0
            sample_volume_sum = 0
            sample_amplitudes = 0

            # process the note event queue until empty
            while self._notes_event_queue:
                note_event = self._notes_event_queue.popleft()

                if note_event.event_type == NOTE_EVENTS['NOTE_ON']:
                    note = note_event.note
                    note.set_key_down()
                    self._notes[note.midi_note] = note
                    notes_on.add(note)

                if note_event.event_type == NOTE_EVENTS['NOTE_OFF']:
                    note = self._notes.pop(note_event.note.midi_note)
                    note.set_key_up()

            # clear any notes that have ended
            if dead_notes:
                for note in dead_notes:
                    notes_on.remove(note)
                dead_notes.clear()

            # then play each active note
            for note in notes_on:
                try:
                    note_sample = next(note)
                except StopIteration:
                    dead_notes.add(note)

                sample_volume_sum += note_sample.volume
                sample_amplitudes += note_sample.volume * note_sample.amplitude

                if note_sample.volume > sample_volume_max:
                    sample_volume_max = note_sample.volume

            if sample_volume_sum:
                weighted_amplitude = sample_amplitudes * sample_volume_max
                weighted_volume = sample_volume_sum * ANALOGUE_MAX
                yield weighted_amplitude // weighted_volume + 127
            else:
                yield 127
