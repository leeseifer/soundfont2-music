#!/usr/bin/env python3
"""Find theme references and inspect actual note passages in the bundled MIDI library."""
import argparse
from collections import defaultdict, deque
import json
import math
from pathlib import Path
import re
import sys
import unicodedata

from sf2_music import defaults

ROOT = Path(__file__).resolve().parents[1]


def tokens(value):
    plain = unicodedata.normalize("NFKD", value.casefold())
    plain = "".join(c for c in plain if not unicodedata.combining(c))
    return set(re.findall(r"[a-z0-9]+", plain))


def catalog():
    settings = defaults()
    path = Path(settings.get("midi_references", {}).get("catalog", "references/midi-catalog.json")).expanduser()
    return json.loads((path if path.is_absolute() else ROOT / path).read_text())


def select_references(data, theme, limit):
    query = tokens(theme or "")
    expanded = set(query)
    for term in query:
        expanded.update(data.get("theme_aliases", {}).get(term, []))
    ranks = {}
    for term in expanded:
        for index, ref_id in enumerate(data.get("theme_defaults", {}).get(term, [])):
            ranks[ref_id] = max(ranks.get(ref_id, 0), max(1, 10 - index * 2))
    hits = []
    for entry in data["entries"]:
        themes = set(entry["themes"])
        score = 3 * len(expanded & themes) + len(query & tokens(entry["title"]))
        score += len(query & tokens(entry["reference_use"])) + ranks.get(entry["id"], 0)
        if query and entry["id"] in (theme or "").lower():
            score += 100
        if query and not score:
            continue
        hits.append({"id": entry["id"], "title": entry["title"], "themes": entry["themes"],
                     "reference_use": entry["reference_use"], "path": str((ROOT / entry["path"]).resolve()),
                     "score": score, "analysis": entry["analysis"]})
    hits.sort(key=lambda item: (-item["score"], item["id"]))
    return {"query": theme, "match_count": len(hits), "returned": min(limit, len(hits)),
            "rights_status": data["rights"]["status"], "matches": hits[:limit]}


def note_name(note):
    return ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")[note % 12] + str(note // 12 - 1)


def phrase(data, ref_id, start, length, limit, track_filter=None):
    import mido
    entry = next((e for e in data["entries"] if e["id"] == ref_id), None)
    if entry is None:
        raise ValueError(f"Unknown reference ID: {ref_id}; use list to find IDs")
    if not math.isfinite(start) or not math.isfinite(length) or start < 0 or not 0 < length <= 256:
        raise ValueError("Start must be finite and >= 0; beats must be > 0 and <= 256")
    path = (ROOT / entry["path"]).resolve()
    mid = mido.MidiFile(path)
    if mid.type == 2 or mid.ticks_per_beat <= 0:
        raise ValueError("Phrase inspection requires type 0/1 MIDI with PPQN timing")
    if track_filter is not None and not 0 <= track_filter < len(mid.tracks):
        raise ValueError("Track index is outside this MIDI's track list")
    ppq, stop = mid.ticks_per_beat, start + length
    notes, unmatched, overlapping = [], 0, 0

    def record(track, channel, key, first, last, velocity, inferred=False):
        begin, end = first / ppq, last / ppq
        if end <= start or begin >= stop or end <= begin:
            return
        notes.append({"track": track, "channel": channel, "pitch": key,
                      "note": note_name(key), "velocity": velocity,
                      "beat": round(max(begin, start) - start, 6),
                      "duration": round(min(end, stop) - max(begin, start), 6),
                      "source_beat": round(begin, 6), "source_duration": round(end - begin, 6),
                      "carry_in": begin < start, "continues_after_window": end > stop,
                      "end_inferred_from_track_end": inferred})

    last_tick = 0
    for idx, track in enumerate(mid.tracks):
        tick, held = 0, defaultdict(deque)
        for msg in track:
            tick += msg.time
            if track_filter is not None and idx != track_filter:
                continue
            if msg.type == "note_on" and msg.velocity:
                if held[(msg.channel, msg.note)]:
                    overlapping += 1
                held[(msg.channel, msg.note)].append((tick, msg.velocity))
            elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                queue = held[(msg.channel, msg.note)]
                if queue:
                    first, velocity = queue.popleft()
                    record(idx, msg.channel, msg.note, first, tick, velocity)
        last_tick = max(last_tick, tick)
        for (channel, key), queue in held.items():
            for first, velocity in queue:
                unmatched += 1
                record(idx, channel, key, first, tick, velocity, True)
    if start >= last_tick / ppq:
        raise ValueError("Start beat is at or beyond the end of this MIDI")
    metadata, tick = [], 0
    active = {"quarter_note_bpm": 120.0, "time_signature": "4/4", "key_signature_metadata": None}
    for msg in mido.merge_tracks(mid.tracks):
        tick += msg.time
        beat = tick / ppq
        event = None
        if msg.type == "set_tempo":
            event = {"type": msg.type, "quarter_note_bpm": round(mido.tempo2bpm(msg.tempo), 4)}
            if beat <= start:
                active["quarter_note_bpm"] = event["quarter_note_bpm"]
        elif msg.type == "time_signature":
            event = {"type": msg.type, "value": f"{msg.numerator}/{msg.denominator}"}
            if beat <= start:
                active["time_signature"] = event["value"]
        elif msg.type == "key_signature":
            event = {"type": msg.type, "value": msg.key}
            if beat <= start:
                active["key_signature_metadata"] = msg.key
        elif msg.type in ("control_change", "program_change", "pitchwheel"):
            event = {key: value for key, value in msg.dict().items() if key != "time"}
        if event is not None and start <= beat < stop:
            metadata.append({"beat": round(beat - start, 6), **event})
    notes.sort(key=lambda item: (item["beat"], item["track"], item["pitch"]))
    return {"id": entry["id"], "title": entry["title"], "path": str(path),
            "start_quarter_beat": start, "requested_quarter_beats": length,
            "available_quarter_beats": round(min(length, last_tick / ppq - start), 6),
            "active_metadata_at_start": active, "metadata_in_window": metadata,
            "note_count_in_window": len(notes), "notes_returned": min(limit, len(notes)),
            "truncated": len(notes) > limit, "notes": notes[:limit],
            "diagnostics": {"unclosed_notes_in_selected_tracks": unmatched,
                            "same_pitch_overlaps_in_selected_tracks": overlapping},
            "interpretation": "Beats are quarter notes. Durations end at note-off, excluding pedal/release tails. Same-pitch overlaps use FIFO pairing. Boundary notes are clipped for inspection only; source MIDI is unchanged."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    listing = sub.add_parser("list", help="Find theme matches; omit theme to browse the catalog")
    listing.add_argument("--theme")
    listing.add_argument("--limit", type=int, default=5)
    passage = sub.add_parser("phrase", help="Read an actual note passage without changing the MIDI")
    passage.add_argument("--id", required=True)
    passage.add_argument("--start-beat", type=float, default=0)
    passage.add_argument("--beats", type=float, default=16)
    passage.add_argument("--limit", type=int, default=128)
    passage.add_argument("--track", type=int)
    args = parser.parse_args()
    if not 1 <= args.limit <= 2000:
        parser.error("limit must be between 1 and 2000")
    data = catalog()
    result = select_references(data, args.theme, args.limit) if args.command == "list" else phrase(
        data, args.id, args.start_beat, args.beats, args.limit, args.track)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError, EOFError, ImportError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
