# Stems, mixing, and listening comparisons

Use a Python environment with `scripts/requirements.txt` installed. Set `SF2_AUDIO` to the absolute path of `scripts/music_audio.py`. FFmpeg is required for mixing/comparisons. Commands refuse existing output files; stems/comparison folders must be new or empty. Keep source MIDI, score, raw audio, and reports.

## Render profile

`sf2_music.py render --font band ... --profile generaluser --interpolation 7` applies the GeneralUser author's reverb/chorus settings and high-quality interpolation. This changes rendering, not performance or sample content. The profile sets polyphony to 512. It is optional, font-specific, and recorded in the render report. `--dry` turns off effects even when a profile is selected. Settings are written to an isolated configuration; global FluidSynth settings are not edited. Read the log for unsupported settings.

## Aligned dry stems

```bash
"$SF2_PY" "$SF2_AUDIO" stems --font band --midi "/output/theme.mid" --out-dir "/output/stems" --interpolation 7
```

One stem is produced per MIDI channel, numbered 1–16 in filenames and 0–15 in JSON. All retain source time zero, tempo maps, and selected-channel controller/program events, including notes on that channel spread across multiple tracks. Different channels of one instrument remain separate; combine them in the mix. Release tails may differ in length. `stems.json` records alignment and audio stats; generated `mix.json` can be used immediately. It compensates any per-stem safety gain reduction to preserve intended relative balance.

Channel extraction refuses SysEx or nonzero MIDI-port routing because those can change channel interpretation. Inspect/convert such routing explicitly before separating it. Rendering the original MIDI directly still preserves it. Stem synthesis may differ slightly from one-pass synthesis because effect/voice state is separate; do not claim sample-identical reconstruction.

To use different fonts for different instruments, rerender the extracted channel MIDI with its verified font into a new WAV, then point the mix to it. Verify the bank/program mapping first. A piano-only font does not inherit the original bank's programs automatically.

## Mix

```bash
"$SF2_PY" "$SF2_AUDIO" mix --config "/output/mix.json" --wav "/output/theme-mixed.wav"
```

Paths in JSON resolve relative to that JSON file; absolute paths also work.

```json
{
  "tracks": [
    {"path": "stems/channel-01.wav", "gain_db": -1, "balance": 0.1,
     "highpass_hz": 45, "eq": [{"hz": 240, "gain_db": -1.5, "q": 0.8}], "room_send": 0.12},
    {"path": "stems/channel-03.wav", "gain_db": -2, "balance": -0.25, "room_send": 0.08},
    {"path": "stems/channel-10.wav", "gain_db": -3, "room_send": 0.04}
  ],
  "room_ir": "/path/to/verified-room-impulse.wav",
  "tail_seconds": 2,
  "peak_dbfs": -1.5,
  "duration_seconds": 60,
  "fade_out_seconds": 0.75
}
```

Omit `room_ir` and sends if no suitable licensed impulse response is available; the helper does not fabricate room recordings. The example settings are audition starting points. `balance` is stereo balance (-1 left, 1 right), not a mono panner. The room uses one shared convolution bus with independent sends; input stems should be dry. Select `tail_seconds` to cover the chosen room decay. EQ/high-pass are optional. Existing wet audio can also be mixed, but adding more ambience needs judgment.

The mix runs internally in floating point, resamples to stereo 44.1 kHz, and applies only the global attenuation necessary to respect the selected true-peak target before PCM16 output. It does not maximize loudness or automatically compress. Original clipping in a source cannot be repaired this way. Plan note releases before `duration_seconds`; a fade is not a replacement for a musical ending. `fade_out_seconds` requires a duration. The report records processing and signal checks; it does not certify musical quality.

## Fair comparison

```bash
"$SF2_PY" "$SF2_AUDIO" compare --a "/output/baseline.wav" --b "/output/revised.wav" --start 8 --duration 12 --out-dir "/output/comparison"
```

Outputs: `A.wav`, `B.wav`, `A-then-B.wav` (0.6-second gap), and `comparison.json`. Select the same 3–120 second passage in both files. The helper measures integrated LUFS, applies a constant gain to each, and verifies a match within 0.2 LU. Default target is -20 LUFS; both are lowered together if either needs more peak headroom. No limiting is used, preserving dynamic differences. Input alignment is not automatically corrected; choose corresponding passages.

Listen for repeated-note artifacts, natural guitar transitions, piano pedal/release behavior, drum balance, and arrangement clarity. Also compare at least one passage with the other instruments muted. Keep the musical phrase, register, and mix comparable when testing sample libraries. Record the listener, chosen version, observations, and any remaining issues in the comparison report. If no audition is available, keep the review pending and report that limitation rather than marking realism passed.

Sources: [GeneralUser settings](https://github.com/mrbumpy409/GeneralUser-GS/blob/main/documentation/README.md), [FluidSynth manual](https://www.fluidsynth.org/wiki/UserManual/), [FFmpeg audio filters](https://ffmpeg.org/ffmpeg-filters.html).
