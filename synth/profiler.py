from synth import Note, Synth


NUM_RUNS = 10000


if __name__ == '__main__':
    synth = Synth()
    sample_generator = synth.sample_generator()

    for idx in range(16):
        note = Note(idx)
        synth.note_on(note)

    for run in range(NUM_RUNS):
        next(note.sample_generator)
