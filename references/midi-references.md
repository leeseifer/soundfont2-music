# Public-domain MIDI references by theme

The default catalog includes **23 source-documented public-domain MIDI references from 22 Mutopia editions**. They cover calm, romance, fantasy, suspense, mourning, comedy, dance, orchestral entrances and marches. The [full catalog](midi-catalog.md) links each edition; [JSON](midi-catalog.json) retains source URLs, hashes, measured notes, quality checks and opening-passage snapshots.

Each imported edition explicitly labels the contributor's edition Public Domain. The MIDI is downloaded from that edition and preserved unchanged. [Mutopia's licensing page](https://www.mutopiaproject.org/legal.html#publicdomain) explains the dedication. This does not cover every file on Mutopia. Newly acquired musical references and samples must have an explicit public-domain dedication or CC0 covering the actual edition/library; free access, an old composition, CC BY or CC BY-SA alone do not qualify.

## Find and inspect

Use the configured Python and absolute helper path, or run these commands from the checkout:

```bash
python scripts/midi_references.py list --theme "fantasy theatre" --limit 3
python scripts/midi_references.py phrase --id mp-248-adagio --start-beat 0 --beats 16
python scripts/midi_references.py list --theme "romantic" --rights source-documented
```

Default searches use `source-documented`. The optional `public-domain` filter also admits user-declared public-domain entries in a separately supplied personal catalog, but not unknown or attribution/share-alike entries. Configure a personal catalog through Git-ignored `local-defaults.json`; preserve its rights provenance per entry.

The original MIT **Launch Day** example remains in the repository. It is not labeled public domain and is excluded from public-domain searches. Inspect it explicitly with `phrase --id launch-day` when requested.

| Scene | Starting references |
| --- | --- |
| Calm, dreamy, reflective | `mp-38` Gymnopédie No. 2; `mp-3` Bach Double Concerto Largo |
| Winter, intimate interior | `mp-1171` The Seasons: January |
| Magic, overture | `mp-248-allegro` Magic Flute; `mp-2014` March of the Dwarfs |
| Ceremonial entrance | `mp-248-adagio` Magic Flute; `mp-1410` Transit of Venus |
| Suspense, chase | `mp-1888` Mountain King; `mp-2014` March of the Dwarfs |
| Mourning, tragedy | `mp-247` Åse's Death |
| Romance, longing | `mp-911` Beethoven Romance Op. 50; `mp-944` Op. 40 |
| Comic procession | `mp-1806` Wooden Soldiers |
| Dance, ballet | `mp-281` Anitra's Dance; `mp-896` Neapolitan Dance |
| Carnival, celebration | `mp-1398` The Seasons: February; `mp-781` Wedding Day |
| Triumph, parade | `mp-626` Stars and Stripes; `mp-2157` Tenth Regiment |
| Folk, nostalgia | `mp-2080` Old French Song |
| Flowing outdoor motion | `mp-803` The Seasons: August; `mp-29` Bach Concerto |

## Apply the reference

Choose one or two suitable references and inspect the actual passage before claiming to use it. Mood tags suggest compositional uses, not listening ratings. Whole works can contrast sharply. `phrase` reads notes, durations, velocities, tracks and timing metadata. Quarter-note BPM is not automatically the perceived pulse in 6/8 or 12/8. Reduce the window or increase `--limit` if output is truncated.

For a new original theme, borrow a specific musical feature and write new material. For direct playback or arrangements, name the work and edition. Adapt piano textures to actual instrumental ranges, voice count and articulation capabilities; author percussion deliberately. Save a `reference-use.json` beside generated work with selected IDs, inspected windows, rights status, borrowed features and original-versus-arrangement mode.

New imports passed type/PPQN parsing, nonempty notes, balanced note-on/off events, hash verification and opening-passage inspection. Their performances are score-generated; author expressive dynamics for new music. Listening review has not been performed. Gymnopédie No. 1 (Mutopia 37) was excluded because its MIDI contains two unmatched note-off events.

The Magic Flute references are two named sections, not a complete overture file. Bach entries identify movements. Fairest of the Fair is a wind score, not every original band part. Neapolitan Dance's MIDI labels its lead flute while its page lists trumpet; select the intended instrument deliberately.
