# Launch Day

Original upbeat guitar, drums and piano cue. D major, 128 BPM, 4/4, 32 bars, exactly 60 seconds in the finished WAV. The MIDI and score remain editable.

| Section | Starts |
| --- | ---: |
| Intro | 0:00.000 |
| Main theme | 0:07.500 |
| Lift | 0:22.500 |
| Full chorus | 0:30.000 |
| Break and build | 0:45.000 |
| Finale | 0:52.500 |

The performance revision preserves the original melody and harmony. Acoustic guitar strokes use standard-tuning string/fret annotations, different down/upstroke string subsets, varied dynamics, grouped microtiming and deliberate damping. Piano has phrase dynamics and selective sustain on both hand channels. The drums keep kick anchors steady, soften hat offbeats, vary snare/fill dynamics, and omit hats beneath crashes. All hats are closed, so this example does not depend on unverified open-hat choke behavior. The clean guitar answers the piano with small single-note bend gestures.

The composition's initial inspiration was short rising gestures answered by another voice and contrasting phrase endings, informed by a Bach Invention No. 8 reference passage. Source notes and its 3/4 meter were not reused. The example's melody, harmony, arrangement and performance are original; that reference MIDI is not included.

## Reproduce

From the repository root, with dependencies installed:

```bash
.venv/bin/python examples/launch-day/render.py --out-dir output/launch-day-finished
```

The script compiles the score, renders five aligned channel stems with the bundled GeneralUser GS, and applies the levels/EQ in `mix.json`. Each stem uses FluidSynth's GeneralUser effects profile, seventh-order interpolation and modest authored reverb sends. No extra convolution room is added. The final tonic arrives at 58.125 seconds; a 0.75-second closing fade completes the 60-second WAV. Raw stems retain their release tails.

The renderer explicitly selects the bundled bank for reproducibility. Local font overrides do not change this example. Synthesizer and FFmpeg versions may affect output samples slightly.

## Verification

The supplied master is stereo PCM16, 44.1 kHz, 60.000 seconds, -1.5 dBTP, -18.78 LUFS, with zero clipped samples and no synthesizer warnings. The score contains 1,576 notes on five instrument channels. Guitar string/fret and same-string overlap checks pass.

Signal and structural checks were performed. Listening review is pending; these measurements do not establish that the revision sounds realistic or better. The SoundFont's sample/articulation limitations still apply. See `verification.json` for the measured result and audio checksum.
