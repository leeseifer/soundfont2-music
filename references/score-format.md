# Score format

Write an original arrangement as JSON. Existing fixed-tempo scores remain valid. Optional expressive fields below compile directly to MIDI; omitted fields add no humanization or controller changes.

```json
{
  "title": "Small Morning Motif",
  "bpm": 96,
  "beats": 4,
  "time_signature": [4, 4],
  "tracks": [
    {
      "name": "Piano melody",
      "channel": 0,
      "bank": 0,
      "program": 0,
      "volume": 100,
      "pan": 64,
      "notes": [
        {"beat": 0, "duration": 0.9, "pitch": "C5", "velocity": 72},
        {"beat": 1, "duration": 0.9, "pitch": "E5", "velocity": 68},
        {"beat": 2, "duration": 1.8, "pitch": "G5", "velocity": 74}
      ]
    }
  ]
}
```

- `bpm`: 20–300 quarter notes/minute. `beats`: total length in quarter notes, not bars; all note ends must fit. Seconds = `beats * 60 / bpm`, plus release tail after synthesis.
- `time_signature`: optional `[numerator, denominator]`, default `[4,4]`; denominator is a power of two up to 32. It does not change the quarter-note beat unit.
- `channel`: unique integer 0–15 per track. Channel **9** is conventional percussion (human-facing channel 10); use only with a real drum preset.
- `bank`, `program`: actual values from `presets`. This composer writes GS bank messages: melodic banks 0–127; percussion bank 128 on channel 9. For other bank layouts use Mido and an explicit renderer bank mode.
- `volume` and `pan`: optional CC7/CC10, 0–127, default 100/64.
- `beat`: start >= 0. `duration`: positive quarter-note length, at least one MIDI tick (1/480 beat).
- `pitch`: MIDI integer 0–127 or scientific pitch (`C4`, `F#3`, `Bb5`). **C4 = MIDI 60**. A chord uses several notes at the same beat.
- `velocity`: 1–127, default 72. Rests are gaps. Same-pitch overlaps on one channel are rejected to avoid premature note-offs. Different pitches may overlap.
- `release_velocity`: optional 0–127 note-off velocity, default 0. Audible response depends on the instrument.

## Expression and tempo

Optional score-level `tempo_changes` is a list of `{ "beat": 8, "bpm": 116 }`. Beats are still quarter notes; positions quantize to 480 ticks/beat. A change at beat 0 overrides `bpm`; changes must occupy distinct ticks before the score end. Calculate duration across the tempo map or inspect the resulting MIDI. Keep a fixed tempo for a tight groove unless the phrase calls for a change.

Optional fields on a track:

```json
{
  "controllers": [
    {"beat": 0, "control": 11, "value": 105},
    {"beat": 0.08, "control": 64, "value": 127},
    {"beat": 3.85, "control": 64, "value": 0},
    {"beat": 4, "control": 11, "value": 115}
  ],
  "pitch_bend_range": 2,
  "pitch_bends": [
    {"beat": 6, "value": 0},
    {"beat": 6.15, "value": 4096},
    {"beat": 6.45, "value": 0}
  ]
}
```

Controllers use integer CC numbers 0–119 and values 0–127, with CC0/32 reserved for validated bank selection. Common controls: modulation 1, volume 7, pan 10, expression 11, sustain 64, sostenuto 66, soft pedal 67, reverb send 91, chorus send 93. Check the font's response; sending a CC does not establish that it has the desired acoustic effect. Keep melodic note dynamics in velocity rather than using CC11 to simulate piano hammer strength.

Pitch bends use signed MIDI values -8192..8191. `pitch_bend_range` is an integer number of semitones (1–24, default 2) and initializes RPN 0. Do not override RPN/bend sensitivity manually in the same track. Bends affect the whole channel; use separate channels for independent bent notes. Add intermediate bend points for a curve. Piano bends are generally inappropriate. Unsupported guitar slides are not made authentic by a generic bend.

At the same tick, note-offs precede controllers/bends, then note-ons. Equal-priority events preserve authored order. Used sustain/sostenuto controls and bends reset at the score end, after note-offs. Author earlier releases to allow a natural ending. Split piano hands need pedal events on both channels if both should sustain.

## Opt-in performance shaping

```json
{
  "humanize": {"timing_ms": 5, "velocity": 3, "duration_percent": 2, "seed": 17},
  "groove": {"subdivision": 0.5, "timing_ms": [0, 4], "velocity": [0, -4]}
}
```

These are conservative starting points to audition, not universal settings. `humanize` bounds: timing 0–30 ms, velocity 0–12, duration 0–15 percent, nonnegative seed. Groove arrays have 1–32 entries, cycling by the nearest subdivision slot; timing values are -40..40 ms and velocity offsets -30..30. The subdivision is .125..4 quarter-note beats. No variation is applied unless these fields are supplied. Unknown fields inside `humanize`/`groove` are rejected.

Simultaneous notes move as a group. Add the same note-level `group` string to the notes of a strum to preserve their authored internal spacing; use a unique group for each attack. A note with `fixed: true` bypasses shaping, useful for tight kick anchors and the final chord. Controllers and tempo changes keep their authored times. Shaping is deterministic for the same score, channel, and seed, and milliseconds follow the tempo map. Notes are constrained to the score boundary. Same-pitch collisions are rejected after shaping: shorten releases or reduce jitter; the helper does not silently delete or repair notes.

## Optional playability checks

Set track `range: ["E2", "E5"]` to validate register. For annotated guitar parts use:

```json
{
  "guitar": {"tuning": [40,45,50,55,59,64], "max_fret": 24, "max_span": 5},
  "notes": [
    {"beat": 0, "duration": 0.7, "pitch": 52, "velocity": 85,
     "string": 0, "fret": 12, "group": "strum-01"}
  ]
}
```

Strings are numbered 0–5 from low to high. Every note in an annotated guitar track needs `string` and `fret`; pitch must equal tuning plus fret. The helper rejects overlapping notes on one string and excessive fretted span within a `group` (open strings excluded). This is a limited structural check, not proof that a human can finger the entire passage. Muting, position transitions, and chord choice still need musical judgment. Put non-guitar keyswitch/FX notes on a separate appropriately mapped track.

Keep JSON, MIDI, and WAV together. Develop related phrases with rhythmic/melodic variations and planned harmonic resolution. Piano hands may use separate melodic channels with the same preset, allowing independent control and safe repeated-pitch overlaps between hands.

```text
doctor
fonts
presets [--sf2 FILE | --font ALIAS]
inspect-midi --midi FILE
compose --score FILE --midi OUTPUT [--sf2 FILE | --font ALIAS] [--overwrite]
render --midi FILE --wav OUTPUT [--sf2 FILE | --font ALIAS] [--piano]
       [--bank-mode gs|gm|xg|mma] [--gain 0.5] [--rate 44100]
       [--dry] [--overwrite]
       [--profile default|generaluser] [--interpolation 0|1|4|7]
play --audio FILE
```

`--dry` disables reverb/chorus. `--piano` is an intentional arrangement change. Outputs refuse to overwrite files without `--overwrite`. Review synth warnings against channels containing notes: single-instrument SF2 files can warn about unused default drum channels.

Installed `--font band` includes guitar/bass/drum presets; see [installed-sounds.md](installed-sounds.md). Select the same font alias for composing and rendering. `--sf2` and `--font` are mutually exclusive.
