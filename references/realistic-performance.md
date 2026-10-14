# Instrument performance

Use for new acoustic/band writing and realism revisions. Keep the user's meter, mood, instruments, and timing constraints. Realism is a listening judgment; use the checks below to prevent obvious performance errors.

## Guitar

- Plan string/fret positions and economical chord transitions. Use the score's optional guitar annotations for explicit range, same-string, and span checks. A maximum of six simultaneous pitches alone does not establish playability.
- Author down/up strokes with different subsets of strings, velocities, durations, and spacing. A modest strum might span roughly 15–45 ms; choose by tempo and articulation, then audition. Group a stroke before adding timing variation so it stays coherent.
- End a ringing string when it is fretted again or deliberately muted. Open strings may ring across chords when harmonically intentional. Repeated short sustained samples are only an approximation to palm muting.
- Use actual muted, slide, hammer-on, harmonic, or noise samples only when mapped and verified. GeneralUser's Steel Guitar is a sustained preset; its separate Muted Guitar is not a complete acoustic palm-mute engine. Record limitations instead of inventing keyswitches.
- Ordinary MIDI bend affects an entire channel. Isolate a single-string bend on another channel when other notes should remain steady. A sampled slide or legato transition can sound different from a bend.

## Piano

- Establish melody/accompaniment balance through velocities and register; shape each phrase's rise and release. Small hand/chord offsets can be appropriate, but strong rhythmic passages may be tight.
- Write pedal changes around actual harmony and texture. Release old pedal around a chord change, then repedal as appropriate. Avoid permanently sustaining a busy arrangement. CC64 provides sustain in FluidSynth; half-pedal, repedaling, resonance, and release noises require specifically verified instrument/engine support.
- Check leaps and stretches in each hand. Separate hands can use independent channels, but pedal/expression events must be repeated on the channels that need them.
- Use note duration for articulation and retain adequate tail. Controller volume changes do not recreate the timbre of a different hammer strike.

## Drums and bass

- Build a repeatable accent pattern first; vary phrase endings and fill intensity. Add soft ghost notes only where stylistically useful. Keep kick anchors stable; hats and snare may have distinct, modest timing profiles.
- Check whether simultaneous snare/tom/cymbal hits fit the intended number of hands; feet can operate kick/pedal-hat. A cymbal crash commonly replaces that hand's hat hit. Separate percussion overdubs may intentionally add limbs.
- Verify hi-hat choking/exclusive groups in the chosen kit; ensure a closed/pedal hat stops an open hat when intended. Do not assume note-offs alone choke every percussion preset.
- Velocity layers change the recorded strike; round robins provide different recordings at a similar strength. Random velocity changes cannot add recordings missing from a bank. Avoid large random pitch changes as a substitute.
- Bass should coordinate with kick and harmony, with deliberate note lengths and occasional approaches; respect instrument register and plucking articulation. Do not add bass when the requested instrumentation excludes it.

## References and revision

Reference MIDI can inform motifs and phrase shape. A reference in one instrument or style does not establish playability or groove for another. When useful, inspect user-supplied or appropriately licensed instrument-specific MIDI performances, and record their provenance. Copy timing/dynamic ideas deliberately without labeling an unchanged source an original work.

Use small, reproducible shaping amounts; protect anchors and endings. Broad independent random jitter can destroy the pocket or dismantle a chord. Do not randomize existing MIDI by default. Compare an unchanged baseline to one deliberate change at a time at matched loudness, using `music_audio.py compare`.

## Research basis (checked 2026-10-14)

- [Ableton groove manual](https://www.ableton.com/en/live-manual/12/using-grooves/): independent timing/velocity controls and instrument-specific groove.
- [Ample Guitar M Lite](https://www.amplesound.net/en/pro-pd.asp?id=7): string-aware performance, strum gestures, and sampled articulation examples. These capabilities are not attributed to GeneralUser.
- [SFZ drum and round-robin guide](https://sfzformat.com/tutorials/drum_basics/): dynamic layers and alternate sampled strikes.
- [GeneralUser documentation](https://github.com/mrbumpy409/GeneralUser-GS/blob/main/documentation/README.md): bank-specific synthesis/effects guidance.
