#!/usr/bin/env python3
"""Inspect SoundFonts, compile a score, and render/play MIDI locally."""
import argparse
from array import array
import json
import math
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import wave

from performance import TempoMap, performed_notes, validate_playability

ROOT = Path(__file__).resolve().parents[1]


def emit(data):
    print(json.dumps(data, indent=2, ensure_ascii=False))


def defaults():
    """Load portable defaults, then recursively overlay private local settings."""
    def merge(base, override):
        for key, val in override.items():
            if isinstance(val, dict) and isinstance(base.get(key), dict):
                merge(base[key], val)
            else:
                base[key] = val
        return base

    settings = {}
    for name in ("defaults.json", "local-defaults.json"):
        path = ROOT / name
        if path.exists():
            data = json.loads(path.read_text())
            if not isinstance(data, dict):
                raise ValueError(f"{name} must contain a JSON object")
            merge(settings, data)
    return settings


def configured_path(path):
    """Settings paths are relative to the skill; explicit CLI paths use cwd."""
    result = Path(path).expanduser()
    return result if result.is_absolute() else ROOT / result


def source(path):
    if not path:
        raise ValueError("Supply --sf2 or set soundfont in local-defaults.json")
    result = Path(path).expanduser().resolve()
    if not result.is_file():
        raise ValueError(f"File not found: {result}")
    return result


def output(path, overwrite=False):
    result = Path(path).expanduser().resolve()
    if result.exists() and not overwrite:
        raise ValueError(f"Output exists: {result}; choose another name or --overwrite")
    result.parent.mkdir(parents=True, exist_ok=True)
    return result


def soundfont(args):
    if args.sf2:
        return source(args.sf2)
    if args.font:
        fonts = defaults().get("soundfonts", {})
        if args.font not in fonts:
            raise ValueError(f"Unknown font '{args.font}'. Available: {', '.join(fonts)}")
        return source(font_path(fonts[args.font]))
    configured = defaults().get("soundfont")
    return source(configured_path(configured) if configured else None)


def font_path(entry):
    return configured_path(entry["path"])


def font_options(parser):
    options = parser.add_mutually_exclusive_group()
    options.add_argument("--sf2", help="Explicit SoundFont file path")
    options.add_argument("--font", help="Installed font alias; see the fonts command")


def presets(path):
    # Seek through RIFF chunks without reading sample payloads into memory.
    with path.open("rb") as stream:
        header = stream.read(12)
        if len(header) != 12 or header[:4] != b"RIFF" or header[8:] != b"sfbk":
            raise ValueError("Not a SoundFont RIFF/sfbk file")
        limit = struct.unpack("<I", header[4:8])[0] + 8
        if limit > path.stat().st_size:
            raise ValueError("Truncated SoundFont")

        def chunks(start, end):
            offset = start
            while offset + 8 <= end:
                stream.seek(offset)
                kind, size = struct.unpack("<4sI", stream.read(8))
                begin, finish = offset + 8, offset + 8 + size
                if finish > end:
                    raise ValueError("SoundFont chunk exceeds its parent")
                yield kind, begin, size
                offset = finish + (size % 2)

        for kind, begin, size in chunks(12, limit):
            stream.seek(begin)
            if kind != b"LIST" or size < 4 or stream.read(4) != b"pdta":
                continue
            for subkind, substart, subsize in chunks(begin + 4, begin + size):
                if subkind != b"phdr":
                    continue
                if subsize < 76 or subsize % 38:
                    raise ValueError("Invalid preset header table")
                stream.seek(substart)
                records = stream.read(subsize)
                result = []
                for offset in range(0, subsize - 38, 38):
                    name, program, bank = struct.unpack_from("<20sHH", records, offset)
                    result.append({"name": name.split(b"\0")[0].decode("latin-1").rstrip(),
                                   "bank": bank, "program": program})
                return result
    raise ValueError("SoundFont has no preset table")


def midi_module():
    try:
        import mido
    except ImportError as exc:
        raise ValueError("Mido is missing. Install scripts/requirements.txt in a venv and use that environment's Python.") from exc
    return mido


def load_midi(path):
    midi = midi_module().MidiFile(path)
    if midi.type == 2 or midi.ticks_per_beat <= 0:
        raise ValueError("Convert type-2/SMPTE MIDI to type 0 or 1 with PPQN timing first")
    return midi


def midi_summary(midi):
    notes = [msg for track in midi.tracks for msg in track
             if msg.type == "note_on" and msg.velocity > 0]
    return {"type": midi.type, "tracks": len(midi.tracks),
            "seconds": round(midi.length, 4), "note_count": len(notes),
            "channels_zero_based": sorted({msg.channel for msg in notes}),
            "program_changes": sorted({(msg.channel, msg.program) for track in midi.tracks
                                       for msg in track if msg.type == "program_change"}),
            "sysex_count": sum(msg.type == "sysex" for track in midi.tracks for msg in track)}


def number(value, low, high, name, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if not low <= value <= high or (integer and int(value) != value):
        raise ValueError(f"{name} must be {'an integer ' if integer else ''}in {low}..{high}")
    return int(value) if integer else value


def pitch(value):
    if isinstance(value, str):
        match = re.fullmatch(r"([A-Ga-g])([#b]?)(-?\d+)", value)
        if not match:
            raise ValueError(f"Invalid pitch: {value}")
        note, accidental, octave = match.groups()
        value = 12 * (int(octave) + 1) + {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}[note.upper()] + {"": 0, "#": 1, "b": -1}[accidental]
    return number(value, 0, 127, "pitch", True)


def compose(args):
    mido = midi_module()
    sf2 = soundfont(args)
    available = {(p["bank"], p["program"]) for p in presets(sf2)}
    score_path = source(args.score)
    score = json.loads(score_path.read_text())
    bpm = number(score["bpm"], 20, 300, "bpm")
    beats = number(score["beats"], 1 / 480, 100000, "beats")
    end_tick = round(beats * 480)
    numerator, denominator = score.get("time_signature", [4, 4])
    numerator = number(numerator, 1, 255, "time signature numerator", True)
    if denominator not in (1, 2, 4, 8, 16, 32):
        raise ValueError("Time signature denominator must be a power of two up to 32")
    midi = mido.MidiFile(type=1, ticks_per_beat=480, charset="utf-8")
    tempo = TempoMap(score)
    conductor = mido.MidiTrack([
        mido.MetaMessage("track_name", name=str(score.get("title", "Theme")), time=0),
        mido.MetaMessage("time_signature", numerator=numerator, denominator=denominator, time=0)])
    previous = 0
    for beat, event_bpm in tempo.events:
        tick = round(beat*480)
        conductor.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(event_bpm), time=tick-previous))
        previous = tick
    conductor.append(mido.MetaMessage("end_of_track", time=end_tick-previous))
    midi.tracks.append(conductor)
    channels = set()
    for spec in score["tracks"]:
        ch = number(spec["channel"], 0, 15, "channel", True)
        if ch in channels:
            raise ValueError("Use a unique channel per score track")
        channels.add(ch)
        bank = number(spec.get("bank", 0), 0, 128, "GS bank", True)
        program = number(spec.get("program", 0), 0, 127, "program", True)
        if (bank, program) not in available:
            raise ValueError(f"SoundFont lacks bank {bank}, program {program}")
        if (ch == 9) != (bank == 128):
            raise ValueError("Use channel 9 with bank 128 for drums; melodic GS banks are 0..127")
        track = mido.MidiTrack([mido.MetaMessage("track_name", name=str(spec.get("name", "Instrument")), time=0)])
        for control, value in ((0, 0 if ch == 9 else bank), (32, 0),
                               (7, number(spec.get("volume", 100), 0, 127, "volume", True)),
                               (10, number(spec.get("pan", 64), 0, 127, "pan", True))):
            track.append(mido.Message("control_change", channel=ch, control=control, value=value, time=0))
        track.append(mido.Message("program_change", channel=ch, program=program, time=0))
        events, intervals = [], {}
        bends = spec.get('pitch_bends', [])
        if bends:
            bend_range = number(spec.get('pitch_bend_range', 2), 1, 24, 'pitch_bend_range', True)
            for control, val in ((101,0),(100,0),(6,bend_range),(38,0),(101,127),(100,127)):
                track.append(mido.Message('control_change',channel=ch,control=control,value=val,time=0))
        pedal_controls = set()
        for event in spec.get('controllers', []):
            tick = round(number(event['beat'],0,beats,'controller beat')*480)
            control = number(event['control'],0,119,'controller',True)
            if control in (0,32):
                raise ValueError('Use bank/program fields for preset selection, not CC0/CC32 automation')
            val = number(event['value'],0,127,'controller value',True)
            events.append((tick,1,mido.Message('control_change',channel=ch,control=control,value=val)))
            if control in (64,66):
                pedal_controls.add(control)
        for event in bends:
            tick = round(number(event['beat'],0,beats,'pitch bend beat')*480)
            bend = number(event['value'],-8192,8191,'pitch bend value',True)
            events.append((tick,1,mido.Message('pitchwheel',channel=ch,pitch=bend)))
        for control in sorted(pedal_controls):
            events.append((end_tick,3,mido.Message('control_change',channel=ch,control=control,value=0)))
        if bends:
            events.append((end_tick,3,mido.Message('pitchwheel',channel=ch,pitch=0)))
        notes = performed_notes(spec, tempo)
        validate_playability(spec, notes, pitch)
        for note in notes:
            start = number(note["beat"], 0, beats, "note beat")
            duration = number(note["duration"], 1 / 480, beats, "note duration")
            key = pitch(note["pitch"])
            velocity = number(note.get("velocity", 72), 1, 127, "velocity", True)
            begin, end = round(start * 480), round((start + duration) * 480)
            if end > end_tick or end <= begin:
                raise ValueError("A note exceeds score length or is shorter than one tick")
            intervals.setdefault(key, []).append((begin, end))
            release = number(note.get('release_velocity',0),0,127,'release_velocity',True)
            events.extend([(begin, 2, mido.Message("note_on", channel=ch, note=key, velocity=velocity)),
                           (end, 0, mido.Message("note_off", channel=ch, note=key, velocity=release))])
        for spans in intervals.values():
            ordered = sorted(spans)
            if any(a[1] > b[0] for a, b in zip(ordered, ordered[1:])):
                raise ValueError("Same pitch overlaps after performance shaping; shorten notes, group repeated attacks, or reduce timing variation")
        previous = 0
        for tick, _, msg in sorted(events, key=lambda item: (item[0], item[1])):
            track.append(msg.copy(time=tick - previous))
            previous = tick
        track.append(mido.MetaMessage("end_of_track", time=end_tick - previous))
        midi.tracks.append(track)
    if midi_summary(midi)["note_count"] == 0:
        raise ValueError("Score contains no notes")
    dest = output(args.midi, args.overwrite)
    if dest in (sf2, score_path):
        raise ValueError("Output must not replace an input")
    midi.save(dest)
    emit({"midi": str(dest), "soundfont": str(sf2), **midi_summary(midi)})


def piano_arrangement(midi):
    mido = midi_module()
    channels = midi_summary(midi)["channels_zero_based"]
    result = mido.MidiFile(type=1, ticks_per_beat=midi.ticks_per_beat)
    init = mido.MidiTrack()
    for ch in channels:
        if ch == 9:
            continue
        for cc in (0, 32):
            init.append(mido.Message("control_change", channel=ch, control=cc, value=0, time=0))
        init.append(mido.Message("program_change", channel=ch, program=0, time=0))
    result.tracks.append(init)
    for old in midi.tracks:
        track, pending = mido.MidiTrack(), 0
        for msg in old:
            pending += msg.time
            if (getattr(msg, "channel", None) == 9 or msg.type in ("program_change", "sysex")
                    or (msg.type == "control_change" and msg.control in (0, 32))):
                continue
            track.append(msg.copy(time=pending))
            pending = 0
        if pending:
            track.append(mido.MetaMessage("end_of_track", time=pending))
        result.tracks.append(track)
    if midi_summary(result)["note_count"] == 0:
        raise ValueError("No melodic notes remain after removing channel 10 percussion")
    return result


def audio_stats(path):
    with wave.open(str(path), "rb") as wav:
        if wav.getsampwidth() != 2 or wav.getcomptype() != "NONE":
            raise ValueError("Expected 16-bit PCM WAV")
        peak, squares, samples, clipped = 0, 0, 0, 0
        while True:
            raw = wav.readframes(65536)
            if not raw:
                break
            values = array("h", raw)
            if sys.byteorder != "little":
                values.byteswap()
            peak = max(peak, max(abs(v) for v in values))
            squares += sum(v * v for v in values)
            clipped += sum(v >= 32767 or v <= -32768 for v in values)
            samples += len(values)
        if not samples or peak <= 2:
            raise ValueError("Rendered audio is empty, silent, or only quantization noise")
        rms = math.sqrt(squares / samples) / 32768
        return {"seconds": round(wav.getnframes() / wav.getframerate(), 4),
                "sample_rate": wav.getframerate(), "channels": wav.getnchannels(),
                "peak_dbfs": round(20 * math.log10(peak / 32768), 2),
                "rms_dbfs": round(20 * math.log10(rms), 2), "clipped_samples": clipped}


def render(args):
    synth = shutil.which("fluidsynth")
    if not synth:
        raise ValueError("FluidSynth is missing; on macOS: brew install fluid-synth")
    sf2, original = soundfont(args), source(args.midi)
    available = presets(sf2)
    midi = load_midi(original)
    if not midi_summary(midi)["note_count"]:
        raise ValueError("MIDI contains no notes")
    dest = output(args.wav, args.overwrite)
    if dest.suffix.lower() != ".wav" or dest in (sf2, original):
        raise ValueError("Choose a separate .wav output")
    log_path = output(str(dest) + ".fluidsynth.log", args.overwrite)
    report_path = output(str(dest) + ".render.json", args.overwrite)
    derived = None
    if args.piano:
        if not any(p["bank"] == 0 and p["program"] == 0 for p in available):
            raise ValueError("--piano requires a piano preset at bank 0/program 0; inspect your SoundFont")
        derived = output(dest.with_suffix(".piano.mid"), args.overwrite)
        if derived in (original, sf2):
            raise ValueError("Piano arrangement must not replace an input")
        midi = piano_arrangement(midi)
        midi.save(derived)
    gain = number(args.gain, 0.001, 5, "gain")
    summary = midi_summary(midi)
    logs = []
    with tempfile.TemporaryDirectory(prefix="sf2-render-", dir=dest.parent) as temp:
        raw = Path(temp) / "render.wav"
        config = Path(temp) / "empty.cfg"
        interpolation = getattr(args, 'interpolation', None)
        config.write_text(f'interp {interpolation}\n' if interpolation is not None else '')
        # Only our explicit render configuration executes; never a user's global config.
        for attempt in range(4):
            command = [synth, "-ni", "-f", str(config), "-r", str(args.rate),
                       "-g", str(gain), "-T", "wav", "-O", "s16", "-F", str(raw),
                       "-o", f"synth.midi-bank-select={args.bank_mode}"]
            profile = getattr(args, 'profile', 'default')
            if profile == 'generaluser':
                for setting, val in {'synth.polyphony':512,'synth.reverb.damp':.3,
                                     'synth.reverb.level':.7,'synth.reverb.room-size':.5,
                                     'synth.reverb.width':.8,'synth.chorus.depth':3.6,
                                     'synth.chorus.level':.55,'synth.chorus.nr':4,
                                     'synth.chorus.speed':.36}.items():
                    command += ['-o',f'{setting}={val}']
            if args.dry:
                command += ["-R", "0", "-C", "0"]
            command += [str(sf2), str(derived or original)]
            process = subprocess.run(command, capture_output=True, text=True,
                                     timeout=max(120, summary["seconds"] * 2 + 60))
            logs.append(f"Attempt {attempt + 1}; gain={gain}\n{process.stdout}\n{process.stderr}")
            log_path.write_text("\n".join(logs))
            if process.returncode or not raw.exists():
                raise ValueError(f"FluidSynth failed; see {log_path}")
            stats = audio_stats(raw)
            if stats["peak_dbfs"] <= -1 and stats["clipped_samples"] == 0:
                break
            gain *= 0.5
        else:
            raise ValueError(f"Still approaching clipping after 4 attempts; lower --gain. See {log_path}")
        raw.replace(dest)
    warnings = [line for line in "\n".join(logs).splitlines()
                if any(word in line.lower() for word in ("warning", "error", "no preset", "unknown command", "invalid"))]
    report = {"wav": str(dest), "soundfont": str(sf2), "source_midi": str(original),
              "rendered_midi": str(derived or original), "piano_arrangement": args.piano,
              "arrangement_changes": ["Melodic channels set to bank 0/program 0", "Channel 10 percussion removed", "SysEx removed"] if args.piano else [],
              "bank_mode": args.bank_mode, "gain": gain, "midi": summary,
              "profile": profile, "interpolation": interpolation, "dry": args.dry,
              "audio": stats, "synth_warnings": warnings,
              "listening_review": "not performed by this helper", "log": str(log_path)}
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    emit(report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    sub.add_parser("fonts")
    preset = sub.add_parser("presets")
    font_options(preset)
    inspect = sub.add_parser("inspect-midi")
    inspect.add_argument("--midi", required=True)
    comp = sub.add_parser("compose")
    comp.add_argument("--score", required=True)
    comp.add_argument("--midi", required=True)
    font_options(comp)
    comp.add_argument("--overwrite", action="store_true")
    rend = sub.add_parser("render")
    font_options(rend)
    rend.add_argument("--midi", required=True)
    rend.add_argument("--wav", required=True)
    rend.add_argument("--piano", action="store_true")
    rend.add_argument("--bank-mode", choices=("gs", "gm", "xg", "mma"), default="gs")
    rend.add_argument("--gain", type=float, default=0.5)
    rend.add_argument("--rate", type=int, choices=(22050, 44100, 48000, 96000), default=44100)
    rend.add_argument("--dry", action="store_true")
    rend.add_argument('--profile', choices=('default','generaluser'), default='default')
    rend.add_argument('--interpolation', type=int, choices=(0,1,4,7))
    rend.add_argument("--overwrite", action="store_true")
    play = sub.add_parser("play")
    play.add_argument("--audio", required=True)
    args = parser.parse_args()
    if args.command == "doctor":
        import importlib.util
        sf = defaults().get("soundfont")
        sf = str(configured_path(sf).resolve()) if sf else None
        emit({"python": sys.executable, "mido": importlib.util.find_spec("mido") is not None,
              "fluidsynth": shutil.which("fluidsynth"), "ffmpeg": shutil.which("ffmpeg"),
              "sfizz_renderer": shutil.which('sfizz_render') or shutil.which('sfizz-render'),
              "speaker_player": shutil.which("afplay") or shutil.which("ffplay"),
              "default_soundfont": sf, "default_exists": bool(sf and Path(sf).is_file())})
    elif args.command == "fonts":
        emit({"default_soundfont": defaults().get("soundfont"), "fonts": {
            alias: {"name": entry["name"], "path": str(font_path(entry).resolve()),
                    "exists": font_path(entry).is_file()}
            for alias, entry in defaults().get("soundfonts", {}).items()}})
    elif args.command == "presets":
        sf = soundfont(args)
        emit({"soundfont": str(sf), "presets": presets(sf)})
    elif args.command == "inspect-midi":
        emit(midi_summary(load_midi(source(args.midi))))
    elif args.command == "compose":
        compose(args)
    elif args.command == "render":
        render(args)
    elif args.command == "play":
        path = source(args.audio)
        if shutil.which("afplay"):
            subprocess.run(["afplay", str(path)], check=True)
        elif shutil.which("ffplay"):
            subprocess.run(["ffplay", "-nodisp", "-autoexit", "-loglevel", "error", str(path)], check=True)
        else:
            raise ValueError("No speaker player found; provide the audio file in an inline player")
        emit({"played": str(path)})


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError, EOFError, struct.error, wave.Error,
            subprocess.SubprocessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
