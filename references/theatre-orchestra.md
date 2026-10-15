# Theatre orchestra: installed CC0 palette

Use for theatre pits, ballet scenes, overtures and chamber-orchestra themes. **VSCO 2 Community Edition** is [released by Versilian Studios under CC0](https://versilian-studios.com/vsco-community/). The curated subset has 59 standalone SFZ patches and 1,933 samples, about 1.89 GiB. Mappings and notices are tracked; restore samples with `scripts/fetch_assets.py --library orchestra`. It is pinned to SFZ commit `6dd651d55dde97fd4028699be9d4481f26917891`; files are unmodified. License, credits and per-file hashes are in `assets/sfz/vsco-2-ce/SOURCE.json` and `LICENSE`.

The [patch catalog](orchestra-catalog.md) and [JSON mappings](orchestra-catalog.json) provide actual ranges, layers, alternate strikes and percussion assignments. Every patch passed sample/header checks, key/velocity coverage and actual sfizz rendering with dynamic, repeated, sustained/released notes and range endpoints. **Technical qualification passed; listening approval is pending.** Successful rendering does not establish musical realism.

## Choose instruments

| Family | Available instruments | Starting IDs |
| --- | --- | --- |
| Strings | Solo violin; violin, viola and cello sections; double bass | `SViolinVib`, `ViolinEnsSusVib`, `ViolaEnsSusVib`, `CelloEnsSusVib`, `ContrabassSusNV` |
| Short/plucked strings | Pizzicato and spiccato | `ViolinEnsPizz`, `CelloEnsPizz`, `ViolinEnsSpic`, `ContrabassSpic` |
| Tremolo strings | Solo and section variants | `ViolinEnsTrem`, `ViolaEnsTrem`, `CelloEnsTrem`, `ContrabassTrem` |
| Woodwinds | Piccolo, flute, oboe, clarinet, bassoon | `PiccoloSus`, `FluteSusNV`, `OboeSusNV`, `ClarinetSus`, `BassoonSus` |
| Brass | Horn, trumpet, trombone, tuba; selected mutes/short notes | `FHornSus`, `TrumpetSus`, `TromboneSus`, `TubaSus`, `TrumpetHarmonMuteSus` |
| Plucked/keys | Harp, upright piano, pipe organ | `Harp`, `UprightPiano`, `OrganQuiet`, `OrganLoud` |
| Mallets/bells | Glockenspiel, marimba, xylophone, tubular bells | `Glockenspiel`, `Marimba`, `Xylophone`, `TubularBells` |
| Percussion | Timpani hits/rolls and orchestral percussion | `Timpani`, `TimpaniRolls`, `GM-StylePerc` |

This covers core acoustic orchestra families. It does not add a sampled choir, saxophone section or every extended technique. Existing GeneralUser band sounds remain available under their own license. Neither GeneralUser nor Grandpno is relabeled CC0; use the new CC0 patches for strictly public-domain sample content.

## Render and mix

Use the configured Python and absolute helper path:

```bash
"$SF2_PY" "$SF2_AUDIO" instruments --family strings
"$SF2_PY" "$SF2_AUDIO" render-sfz --instrument ViolinEnsSusVib --midi "/output/strings.mid" --channel 0 --wav "/output/strings.wav"
"$SF2_PY" "$SF2_AUDIO" render-sfz --instrument FluteSusNV --midi "/output/flute.mid" --wav "/output/flute.wav"
"$SF2_PY" "$SF2_AUDIO" mix --config "/output/mix.json" --wav "/output/theatre.wav"
```

`instruments` lists qualified mappings. Each SFZ render loads one instrument; use separate aligned MIDI/stems for instrument/articulation changes. Author SFZ MIDI directly with Mido, or deliberately use the score compiler for a GM sketch before routing parts to SFZ. The SF2 compiler validates an SF2, not SFZ ranges or articulations. Check notes against `note_range` and percussion `mapped_keys`; preserve absolute timing across stems. See [render-and-compare.md](render-and-compare.md).

Qualification used sfizz 1.2.3. Install its offline renderer separately and put it on PATH, or configure `sfz_renderer` in private `local-defaults.json`; `doctor` checks it. No Kontakt or plugin host is needed. `--sfz` still accepts explicit user-selected files. Do not pass SFZ files to FluidSynth or invent GM program numbers for these patches.

## Write to the recordings' strengths

- Strings have recorded sustain/vibrato, short, pizzicato and tremolo variants; use separate articulation stems. No mapped true legato transitions are claimed. Alternate strikes exist only where the catalog records them.
- These mappings use finite, unlooped recordings. Long holds can decay/end before MIDI note-off. Inspect `sample_duration_seconds_range` and the actual region/sample before writing long sustains; phrase and rearticulate deliberately.
- Woodwind/brass dynamics have limited, note-dependent recorded layers. CC7/CC11 change engine volume, not recorded modwheel timbre crossfades. Leave breathing space and respect actual mapping limits, which can differ by articulation.
- Harp, piccolo and several mallets have sparse sampling or one dynamic layer. Use them as appropriate color without claiming detailed velocity realism. Upright piano has three mapped dynamic bands but no mapped sampled pedal/release/resonance set.
- `GM-StylePerc` is not a promise of every GM note. Consult `percussion_note_map` for actual drums, cymbals, triangle and other recordings. Timpani is a separate pitched patch; rolls have a separate patch.
- Raw levels vary substantially. Start conservatively, measure and balance stems, and preserve headroom in the combined orchestra. Shared room processing is optional; retain dry auditions when judging samples.

For calm scenes, try flute or solo violin over light strings and harp. Comedy suits short bassoon/clarinet phrases and pizzicato. Suspense suits sparse low strings, tremolo and restrained timpani. Ceremonial entrances can use horn/trumpet phrases with strings and measured percussion. Let orchestral density change with the scene rather than playing every family continuously.
