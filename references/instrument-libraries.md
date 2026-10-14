# Optional instrument libraries and SFZ

GeneralUser GS is the bundled default for piano and band arrangements; local settings may override it. Improve performance before attributing all limitations to the bank. Larger file size alone does not establish quality.

For a candidate instrument, record source/version/license, supported note range, velocity layers, repeated-note variants, release samples, articulation mappings, controllers, and the engine actually tested. Use a repeated-note phrase, a soft-to-loud phrase, a legato/strum phrase where applicable, and a release/pedal test. Unsupported mappings and absent sample files are blockers for claiming that capability. Do not describe generic CC/bend approximations as sampled articulations.

## SFZ renderer

`sf2_music.py doctor` reports whether `sfizz_render` or `sfizz-render` is installed. It is optional and independent of FluidSynth. Install/build it only when this workflow is needed; [sfizz build documentation](https://www.sfz.tools/sfizz/development/build/) describes the offline renderer (`SFIZZ_RENDER`). This skill does not automatically install it or download libraries.

```bash
"$SF2_PY" "$SF2_AUDIO" render-sfz --sfz "/library/instrument.sfz" --midi "/output/theme.mid" --channel 0 --wav "/output/piano-sfz.wav"
```

Use one SFZ instrument per render. For multi-instrument MIDI, `--channel` is required (0–15); extraction preserves timing/controllers. For a single-channel file it can be omitted. `--renderer /absolute/path/sfizz_render` chooses an installed renderer explicitly. `--rate` supports 44100 or 48000. SFZ scores may be authored as MIDI directly; the SF2 score compiler still validates bank/program assignments against an SF2 and is not a universal SFZ articulation compiler.

The wrapper writes an SFZ log, checks nonempty PCM, and refuses clipping or reported sampler warnings. Missing renderer fails clearly without falling back to a different instrument. Logs cannot prove every opcode behaved correctly: audition mapped techniques and inspect the SFZ's required extensions. If the SFZ render clips, reduce instrument output using its supported controls before rendering again; postprocessing cannot restore clipped samples. The source SFZ, samples, and MIDI remain untouched.

## Candidates researched 2026-10-14, not installed by this update

- [Salamander Grand Piano](https://github.com/sfzinstruments/SalamanderGrandPiano): 16 recorded velocity layers and release/resonance material. This remapping uses SFZ v2 plus ARIA extensions and explicitly targets sforzando/ARIA. Do not assume the complete mapping works in sfizz; choose a compatible mapping or verify the necessary opcodes and audio. Retain the exact sample license and attribution.
- [Ample Guitar M Lite](https://www.amplesound.net/en/pro-pd.asp?id=7): a separate free guitar plugin with sustain, hammer-on/pull-off, legato slide, palm mute, and pop articulations. Requires a plugin host, its library, and its own mappings; it cannot be loaded into FluidSynth or the SFZ wrapper. Its free fingerstyle library differs from the paid strum/pick libraries. Evaluate this as a separate optional workflow, not an installed skill capability.
- For drums, prefer verified multi-dynamic recordings with alternate strikes and hi-hat choke behavior. The [SFZ drum guide](https://sfzformat.com/tutorials/drum_basics/) explains velocity layers and `seq_length`/`seq_position` round robins. Keep provenance for any added sample pack and do not invent round-robin recordings from one sample.
