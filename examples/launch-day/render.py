#!/usr/bin/env python3
"""Reproduce the example from its editable score, without personal settings."""
import argparse
import contextlib
import io
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import sf2_music as core
import music_audio as audio


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', required=True, help='New or empty output directory')
    args = parser.parse_args()
    dest = audio.fresh_directory(args.out_dir)
    example = Path(__file__).resolve().parent
    sf2 = ROOT / 'assets/soundfonts/generaluser-gs/GeneralUser-GS.sf2'
    midi_path = dest / 'launch-day.mid'
    core.compose(argparse.Namespace(sf2=str(sf2), font=None, score=str(example/'score.json'),
                                    midi=str(midi_path), overwrite=False))
    midi = core.load_midi(midi_path)
    stem_dir = dest / 'wet-stems'
    stem_dir.mkdir()
    config = json.loads((example/'mix.json').read_text())
    for entry, channel in zip(config['tracks'], [0, 1, 2, 3, 9]):
        path = dest / entry['path']
        stem_midi = path.with_suffix('.mid')
        audio.selected_channel(midi, channel).save(stem_midi)
        render = argparse.Namespace(sf2=str(sf2), font=None, midi=str(stem_midi),
            wav=str(path), overwrite=False, piano=False, gain=.5, rate=44100,
            bank_mode='gs', dry=False, profile='generaluser', interpolation=7)
        with contextlib.redirect_stdout(io.StringIO()):
            core.render(render)
        report = json.loads(Path(str(path)+'.render.json').read_text())
        if report['synth_warnings']:
            raise ValueError(f'Review synthesizer warnings: {path}.render.json')
        entry['gain_db'] += 20 * math.log10(.5 / report['gain'])
    config_path = dest / 'mix.json'
    config_path.write_text(json.dumps(config, indent=2)+'\n')
    audio.mix(argparse.Namespace(config=str(config_path), wav=str(dest/'launch-day.wav')))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError) as error:
        sys.exit(f'Error: {error}')
