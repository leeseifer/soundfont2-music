# Third-party notices

## GeneralUser GS 2.0.3

By **S. Christian Collins**. The files in `assets/soundfonts/generaluser-gs/` are distributed under the original [GeneralUser GS license](assets/soundfonts/generaluser-gs/LICENSE.txt), not this repository's MIT license. The SoundFont, instrument definitions and license are unmodified; pinned source URLs, version and SHA-256 checksums are in [SOURCE.json](assets/soundfonts/generaluser-gs/SOURCE.json).

The author permits music creation, including commercial music, and use in software projects. The original license also describes uncertainty about some historical sample provenance. The complete notice is retained.

[Author's homepage](https://www.schristiancollins.com/generaluser) · [Upstream repository](https://github.com/mrbumpy409/GeneralUser-GS)

## VSCO 2 Community Edition

The curated orchestral mappings and samples are by Versilian Studios, recorded by Sam Gossner and Simon Dalzell, with sample cutting by Elan Hickler. They are released under [CC0 1.0](assets/sfz/vsco-2-ce/LICENSE), separately from this repository's MIT code license. Upstream credits and documentation are retained. The pinned [source manifest](assets/sfz/vsco-2-ce/SOURCE.json) records the SFZ commit and per-file checksums.

The 59 mappings and notices are tracked in Git. Approximately 1.9 GiB of WAV samples are restored from the pinned publisher source by `scripts/fetch_assets.py --library orchestra`. The original files are unmodified. [Publisher](https://versilian-studios.com/vsco-community/) · [Upstream](https://github.com/sgossner/VSCO-2-CE).

## Mutopia public-domain MIDI references

The 23 MIDI references come from 22 editions whose contributors explicitly dedicated their editions to the public domain. They are not relicensed under the repository's MIT license. Each reference retains its source page, download URL, source-page snapshot and checksum in the [catalog](references/midi-catalog.json); the MIDI files are unmodified. [Mutopia's public-domain dedication](https://www.mutopiaproject.org/legal.html#publicdomain) explains this status. It does not apply to every file on Mutopia.

## Runtime dependencies

Mido, FluidSynth, FFmpeg and optional sfizz are installed separately and retain their upstream licenses. Their source or binaries are not bundled here.
