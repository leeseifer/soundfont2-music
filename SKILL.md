---
name: soundfont2-music
description: Compose expressive piano, guitar, bass, and drum themes, render MIDI with SoundFont 2 (.sf2), mix instrument stems, and compare performance revisions. Includes optional SFZ rendering for suitable instrument libraries. Use for SoundFont/SF2 music requests, including the misspelling soundfront. Does not generate speech or arbitrary recorded ambience.
---

# SoundFont 2 Music

Turn a theme description into an original MIDI arrangement and playable WAV, or render an existing MIDI with the user's SoundFont. The SF2 supplies instruments; the MIDI supplies notes and timing. Codex composes the music; the helper validates and renders it.

## Local setup and inputs

- Read [defaults.json](defaults.json) and, if present, `local-defaults.json`. Local settings recursively override the portable defaults. Settings paths are relative to this skill; explicit command-line paths are relative to the working directory. Both bundled font aliases use GeneralUser GS; choose a piano preset for piano-only requests. Explicit user files take priority. Recheck paths and never silently substitute another SoundFont.
- Helper: `scripts/sf2_music.py`. It needs Python 3.10+, Mido, and `fluidsynth` for rendering. Playback can be inline; direct speaker playback uses `afplay` on macOS or `ffplay` elsewhere.
- Run `doctor` and `presets` first. Preset numbers are **zero-based**. A bank can contain just one instrument: do not assume General MIDI coverage or invent instruments from preset numbers alone.
- Run `fonts` to list installed banks. Piano remains the default. For guitar, bass, drums, or a band arrangement, select `--font band` on both compose and render. Read [references/installed-sounds.md](references/installed-sounds.md) for verified presets and drum notes. Explicit user SoundFonts take precedence.
- If dependencies are missing, use an isolated environment, e.g. `python3 -m venv ~/.cache/soundfont2-music/venv`, then its Python's `-m pip install -r scripts/requirements.txt`. On macOS install FluidSynth and FFmpeg with `brew install fluid-synth ffmpeg`; use the available package manager elsewhere. Do not replace an existing working environment.
- If the supplied/default SF2 is unavailable, ask for the file or its path. For a ZIP, list entries and extract only the selected SF2 into an output folder, avoiding traversal paths.
- Put outputs in a new named folder at the requested destination. Otherwise use `~/Music/SoundFont2/<descriptive-name>-<timestamp>/`. Keep generated music outside an unrelated code repository.

Examples assume `SF2_PY` is the verified interpreter and `SF2_TOOL` is the absolute helper path. Quote paths.

```bash
"$SF2_PY" "$SF2_TOOL" doctor
"$SF2_PY" "$SF2_TOOL" fonts
"$SF2_PY" "$SF2_TOOL" presets --sf2 "/path/to/instruments.sf2"
```

## Compose from a theme

Infer mood, tempo, key, duration, instrumentation, and whether this is a cue or repeating background from the request. Unless specified, make a roughly 20-second original cue and state the choices briefly. A “forest” theme means music evoking that setting; actual rain/birds need suitable samples or another workflow.

**References:** the public package includes an original upbeat band example. Read [references/midi-references.md](references/midi-references.md), query `scripts/midi_references.py list --theme "<mood>"`, and inspect a relevant passage with `phrase` when useful. If no suitable match exists, compose original material without forcing the example into the requested mood. User-selected references and requests to avoid references take priority. Record the source, rights provenance, inspected passage, and borrowed ideas beside the output. Do not label an unchanged source as an original composition.

Inspect instruments, then write `score.json` using [references/score-format.md](references/score-format.md). With a piano-only SF2, arrange for piano. Choose a recognizable motif, harmonic movement, phrasing, and an intentional ending. Use controlled velocity/timing variation when appropriate. Random notes or an unvaried arpeggio alone are not a finished theme. Adapt to the user's duration rather than forcing a fixed template.

For new acoustic or band compositions, read [references/realistic-performance.md](references/realistic-performance.md) for instrument-specific phrasing, groove, damping, and sample capability checks. Shape the performance deliberately; optional seeded humanization supplements authored dynamics. The score supports pedal/expression controllers, pitch bends, tempo changes, and annotated guitar validation. Existing scores retain their behavior when these fields are omitted. Preserve the requested pulse and duration; rubato is optional, not a realism requirement.

```bash
"$SF2_PY" "$SF2_TOOL" compose --score "/output/score.json" --midi "/output/theme.mid"
"$SF2_PY" "$SF2_TOOL" render --midi "/output/theme.mid" --wav "/output/theme.wav"
```

Both commands use the default SF2 unless `--sf2` or `--font` overrides it; use the same SF2 for both. For example, add `--font band` to both commands for guitars and drums. Score duration is musical time; WAV duration also includes instrument release/reverb. For exact durations, plan a note-free ending and finish audio deliberately. For seamless loops, preserve beat-exact length, handle tails across the boundary, and check the repeat; the ordinary renderer does not certify seamless loops.

## Realism, mixing, and comparisons

Read [references/render-and-compare.md](references/render-and-compare.md) when refining realism or mixing a band. `scripts/music_audio.py` provides `stems`, `mix`, and `compare`. Keep aligned dry stems and use conservative per-instrument EQ/levels; an optional supplied room impulse response provides shared ambience with separate sends. Match loudness before choosing between revisions. The comparison report stays `pending` until a listener or an available audio-review tool actually evaluates it.

For GeneralUser GS, the renderer offers `--profile generaluser` with the author's effects settings and `--interpolation 7` for high-quality offline sampling. Treat these as auditionable choices, not proof of realism. Use `--dry` for stems; do not add room effects twice. Other fonts and existing-MIDI playback keep the default renderer configuration unless deliberately changed.

For more detailed samples, read [references/instrument-libraries.md](references/instrument-libraries.md). `music_audio.py render-sfz` uses an optional installed sfizz renderer and one verified SFZ instrument per render. Do not silently replace the chosen SoundFont, download a large library, or invent articulations/round robins a library lacks. Document the library, license/provenance, supported controllers, and compatibility actually verified.

## Render existing MIDI

```bash
"$SF2_PY" "$SF2_TOOL" inspect-midi --midi "/input/song.mid"
"$SF2_PY" "$SF2_TOOL" render --midi "/input/song.mid" --wav "/output/song.wav"
```

Preserve source notes, tempo changes, expression, and instrument assignments by default. Use `--bank-mode gs|gm|xg|mma` when the source requires it (default GS). MIDI type 2 and SMPTE timing require conversion in a suitable MIDI tool first.

For an existing MIDI with guitar/drum or other ensemble assignments and no user-specified SF2, select the installed `--font band` to preserve that arrangement, and name the bank used. Do not replace requested instruments with piano just because the piano is the default.

If the SF2 lacks required instruments, explain the mismatch. When a piano arrangement is requested or clearly implied, use `--piano`: this saves a derived `.piano.mid`, assigns bank 0/program 0 to melodic channels, drops channel 10 percussion, and removes SysEx. Disclose these changes. Do not silently pass a piano arrangement off as the original orchestration. Advanced SysEx drum routing needs separate inspection.

## Verify and play

The renderer checks for nonempty PCM audio, reports duration/peak/RMS, and reduces gain if peaks approach clipping. Read the `.render.json` and `.fluidsynth.log` next to the WAV: missing presets, dropped channels, or synth warnings need review even if audio exists. Fix relevant issues and rerender. If a quiet SF2 produces a faint preview, raise `--gain` and recheck. Signal checks do not establish musical quality; listen when audio inspection is available and otherwise label that limitation honestly.

Provide a playable embed with an **absolute** path: `![Theme preview](/absolute/path/theme.wav)`. Include a MIDI link when useful. For explicit speaker playback, run `play --audio "/absolute/path/theme.wav"`; do not change system volume. Prefer the inline player for deliverables. Claim speaker playback only if the player was actually run.

WAV is the master. If MP3 is requested and FFmpeg is present, convert with `ffmpeg -nostdin -i input.wav -codec:a libmp3lame -q:a 2 output.mp3` and verify the file. Retain MIDI and score for revisions; keep original SF2/MIDI inputs intact.

References: [FluidSynth CLI](https://www.fluidsynth.org/wiki/UserManual/), [bank selection](https://www.fluidsynth.org/api/settings_synth.html), [Mido MIDI files](https://mido.readthedocs.io/en/stable/files/midi.html).
