# MIDI references

The public catalog includes the original **Launch Day** example, licensed with this repository. Reference use is optional and should suit the requested mood. A private reference collection is not required.

```bash
"$SF2_PY" /path/to/soundfont2-music/scripts/midi_references.py list --theme excited
"$SF2_PY" /path/to/soundfont2-music/scripts/midi_references.py phrase --id launch-day --start-beat 16 --beats 8
```

`phrase` reads actual notes, channel/track assignments, tempo and controller events. Beat values use quarter notes. `--track` restricts inspection to one zero-based MIDI track; `--limit` controls returned notes.

To use your own collection, create a catalog following `midi-catalog.json` and point `midi_references.catalog` to it in an untracked `local-defaults.json`. Catalog and entry paths are relative to the skill unless absolute. Keep titles, IDs, themes, provenance and rights accurate. Keep private reference files outside the repository. Rights metadata records your provenance; the helper does not verify licensing.

For an original piece, record the reference passage and musical ideas used, then compose new material. For a requested arrangement, identify the source and preserve its attribution.
