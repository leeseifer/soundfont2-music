# SoundFont 2 Music

A portable Codex skill for creating expressive instrumental themes and rendering MIDI locally. Write a score, shape the performance, render instrument stems, mix a WAV, and compare revisions at matched loudness.

Includes **GeneralUser GS 2.0.3** for piano, guitars, bass and drums, plus **Launch Day**, an original 60-second upbeat guitar/drums/piano example in 4/4 at 128 BPM.

[Listen to Launch Day](examples/launch-day/launch-day.wav) · [Editable score](examples/launch-day/score.json) · [MIDI](examples/launch-day/launch-day.mid) · [Skill instructions](SKILL.md)

## Install

Requires Python 3.10+, Mido and FluidSynth. Mixing and comparison require FFmpeg. No cloud audio service or API key is needed. The bundled SoundFont is about 31 MiB.

Clone into an unused skill folder; if you already have this skill, keep your existing local settings and assets when updating.

```bash
git clone https://github.com/leeseifer/soundfont2-music.git ~/.codex/skills/soundfont2-music
cd ~/.codex/skills/soundfont2-music
python3 -m venv .venv
.venv/bin/python -m pip install -r scripts/requirements.txt
```

On macOS:

```bash
brew install fluid-synth ffmpeg
```

On Debian/Ubuntu:

```bash
sudo apt-get install fluidsynth ffmpeg python3-venv
```

Check the installation:

```bash
.venv/bin/python scripts/sf2_music.py doctor
.venv/bin/python scripts/sf2_music.py presets --font band
```

Then invoke **$soundfont2-music** in Codex, for example:

> Create a 60-second excited theme in 4/4 with guitar, drums and piano. Use playable guitar voicings, phrase dynamics and a clean ending. Provide a WAV and MIDI.

The command-line tools also work without Codex.

## Try the example

From the repository folder, choose new output paths:

```bash
.venv/bin/python scripts/sf2_music.py compose --font band \
  --score examples/launch-day/score.json --midi output/launch-day.mid
.venv/bin/python scripts/sf2_music.py render --font band \
  --midi output/launch-day.mid --wav output/launch-day-raw.wav \
  --profile generaluser --interpolation 7
```

The MIDI is 60 seconds; a raw render includes release tails. To reproduce the finished 60-second example, including its stem balance, EQ and fade:

```bash
.venv/bin/python examples/launch-day/render.py --out-dir output/launch-day-finished
```

The output directory must be new or empty. [Example notes](examples/launch-day/README.md) explain the performance and verification.

## What it supports

- SF2 preset inspection, score-to-MIDI compilation, rendering and playback.
- Authored velocities, sustain/expression controllers, pitch bends, tempo changes and seeded timing variation that keeps strums together.
- Optional guitar string/fret, range and same-string overlap checks.
- Aligned dry stems, per-instrument levels/EQ, optional shared room convolution with your own impulse response, and true-peak headroom checks.
- Loudness-matched A/B audio clips with listening status kept separate from signal checks.
- An optional sfizz wrapper for one compatible SFZ instrument per render; sfizz and sample libraries are not included.

Read [score format](references/score-format.md), [instrument performance](references/realistic-performance.md), [mixing and comparison](references/render-and-compare.md), and [optional libraries](references/instrument-libraries.md) as needed.

These are sampled instruments, not a physical performance engine. Timing variation cannot create missing round-robin recordings or articulations. The guitar validator is not a full fingering solver. Musical quality still needs listening. The optional SFZ integration has dependency/error checks; no SFZ library has been auditioned as part of this release.

## Personal settings

[defaults.json](defaults.json) works after cloning, from any working directory. Both `piano` and `band` aliases use the bundled GeneralUser bank. To prefer another piano, create an untracked `local-defaults.json`:

```json
{
  "soundfont": "/path/to/piano.sf2",
  "soundfonts": {
    "piano": {"name": "My piano", "path": "/path/to/piano.sf2"}
  }
}
```

Local values recursively override defaults; unspecified aliases remain available. Settings paths are relative to this skill, while explicit command-line paths are relative to the current directory. Keep personal reference files outside this repository; [reference setup](references/midi-references.md) is optional.

## Tests

```bash
.venv/bin/python -m unittest discover -s scripts -p test_music.py -v
```

The suite covers MIDI events/timing, performance groups, guitar validation, portable configuration, real SF2 rendering, stem mixing, convolution and loudness matching. Audio tests need FluidSynth and FFmpeg; otherwise they are skipped. Listen to the delivered music separately from these automated checks.

## License

Code, documentation and original Launch Day example: [MIT](LICENSE). GeneralUser GS has its own [included license and notices](THIRD_PARTY_NOTICES.md). See the [author's homepage](https://www.schristiancollins.com/generaluser) for the SoundFont project.
