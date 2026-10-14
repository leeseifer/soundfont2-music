# Installed guitar, bass, and drum sounds

The public package bundles **GeneralUser GS 2.0.3** by S. Christian Collins. Both `--font piano` and `--font band` use it by default; select the requested instruments in the score. Bank 0/program 0 is Grand Piano, and program 1 is Bright Grand. An explicit user-supplied SF2 takes priority, and local settings can override each alias. One render uses one bank. To combine sounds from different banks, render aligned stems with their respective fonts and mix them.

The following values were inspected in the downloaded SF2. All programs and channels below are **zero-based**.

## Guitars

| Sound | Bank | Program |
| --- | ---: | ---: |
| Nylon Guitar | 0 | 24 |
| Steel Guitar | 0 | 25 |
| Jazz Guitar | 0 | 26 |
| Clean Guitar | 0 | 27 |
| Muted Guitar | 0 | 28 |
| Overdrive Guitar | 0 | 29 |
| Distortion Guitar | 0 | 30 |
| Guitar Harmonics | 0 | 31 |
| 12-String Guitar | 8 | 25 |
| Hawaiian Guitar | 8 | 26 |
| Chorused Clean Gt. | 8 | 27 |
| Funk Guitar | 8 | 28 |
| Feedback Guitar | 8 | 30 |
| Guitar Feedback | 8 | 31 |
| Clean Guitar 2 | 12 | 27 |
| Ukulele | 8 | 24 |
| Mandolin | 16 | 25 |

Choose nylon/steel for acoustic music, jazz/clean/muted for softer electric parts, and overdrive/distortion for rock. Guitar harmonics and feedback are special articulations, not interchangeable full guitar parts. The bank also has `Wah Guitar (CC21)` at bank 11/program 29, which needs deliberate controller programming for a moving wah effect.

For natural guitar writing, use playable voicings with at most six strings, a plausible register (standard guitar's lowest open note is E2/MIDI 40), and small staggered note starts for strums. A few milliseconds between strings and velocity accents are useful; do not randomly offset the whole groove. Use short damped durations for muted rhythms and longer releases for fingerpicking. These are sampled presets, not a physical guitar performance engine.

## Bass

Bank 0: Acoustic Bass `32`, Finger Bass `33`, Pick Bass `34`, Fretless Bass `35`, Slap Bass 1 `36`, Slap Bass 2 `37`, Synth Bass 1 `38`, Synth Bass 2 `39`.

## Drum kits

Use **channel 9, bank 128** in score JSON. The helper writes the appropriate program change; do not send MIDI controller value 128.

| Kit | Program |
| --- | ---: |
| Standard 1 | 0 |
| Standard 2 | 1 |
| Standard 3 | 2 |
| Room | 8 |
| Power | 16 |
| Electronic | 24 |
| 808/909 | 25 |
| Dance | 26 |
| Jazz | 32 |
| Brush | 40 |
| Orchestral | 48 |
| SFX | 56 |
| CM-64/32L | 127 |

The ordinary kit note map includes:

| Drum | MIDI note |
| --- | ---: |
| Kick Drum 2 / Kick Drum 1 | 35 / 36 |
| Side stick | 37 |
| Snare Drum 1 / Snare Drum 2 | 38 / 40 |
| Hand clap | 39 |
| Low toms | 41 / 43 |
| Closed / pedal / open hi-hat | 42 / 44 / 46 |
| Mid toms | 45 / 47 |
| High toms | 48 / 50 |
| Crash cymbals | 49 / 57 |
| Ride cymbals | 51 / 59 |
| Tambourine | 54 |
| Cowbell | 56 |

Use repeated short notes (roughly 0.08–0.2 beats) for drum hits and vary velocities with the groove. Avoid overlapping repeated notes of the same pitch on one channel. Keep kick/snare accents grounded while leaving space for guitar phrases; use fills to mark phrase endings.

The Brush kit replaces snare articulations with brush sounds; Orchestral, SFX and CM-64/32L have different mappings. Consult the upstream [instrument and note definitions](../assets/soundfonts/generaluser-gs/GeneralUser-GS.ins) for those kits rather than guessing.

## Example commands

```bash
"$SF2_PY" "$SF2_TOOL" compose --font band --score "/output/score.json" --midi "/output/band.mid"
"$SF2_PY" "$SF2_TOOL" render --font band --midi "/output/band.mid" --wav "/output/band.wav"
```

Use a melodic channel such as 0 for guitar, another such as 1 for bass, and channel 9 for drums. Keep the same `--font band` selection in both commands. The normal starting gain is 0.5; adjust it only after checking the rendered level.

Some presets can leave long quiet release tails. Check the rendered duration; for a short preview, retain the musical ending and a suitable decay, then trim excess tail with a brief fade. Preserve the untrimmed render separately. Apply only enough preview gain for comfortable listening and recheck peaks after processing.

## Source and license

- [Author's project](https://www.schristiancollins.com/generaluser)
- [Official repository](https://github.com/mrbumpy409/GeneralUser-GS)
- [Bundled license](../assets/soundfonts/generaluser-gs/LICENSE.txt)
- [Version, source commit and SHA-256 checksums](../assets/soundfonts/generaluser-gs/SOURCE.json)

The author permits private and commercial music creation and use in software projects under the included custom license. It also documents uncertainty about some historical sample provenance; preserve that full notice when distributing the bank. The SF2 was downloaded unmodified. The 13 drum kits are additionally mirrored in bank 120 for compatibility; those duplicates are not extra kits or guitar presets.
