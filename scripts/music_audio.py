#!/usr/bin/env python3
"""Aligned stems, conservative mixing, loudness-matched comparisons, optional SFZ rendering."""
import argparse
import contextlib
import io
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import sf2_music as core


def run(command, timeout=300):
    p = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise ValueError(f'{Path(command[0]).name} failed: {p.stderr[-4000:]} {p.stdout[-1000:]}')
    return p


def ffmpeg():
    exe = shutil.which('ffmpeg')
    if not exe:
        raise ValueError('FFmpeg is required for mixing and comparisons')
    return [exe, '-hide_banner', '-nostdin', '-v', 'info', '-n']


def writable(path, protected=()):
    dest = Path(path).expanduser().resolve()
    if dest in {Path(p).resolve() for p in protected}:
        raise ValueError('Output must not replace an input')
    return core.output(dest)


def fresh_directory(path):
    result = Path(path).expanduser().resolve()
    if result.exists() and (not result.is_dir() or any(result.iterdir())):
        raise ValueError(f'Choose a new or empty output directory: {result}')
    result.mkdir(parents=True, exist_ok=True)
    return result


def selected_channel(midi, channel):
    """Retain every global meta event and selected-channel event at its original tick."""
    mido = core.midi_module()
    if any(m.type == 'sysex' or (m.type == 'midi_port' and m.port != 0)
           for t in midi.tracks for m in t):
        raise ValueError('Channel extraction needs plain single-port MIDI; inspect SysEx/port routing first')
    result = mido.MidiFile(type=1, ticks_per_beat=midi.ticks_per_beat, charset=midi.charset)
    for old in midi.tracks:
        track, pending = mido.MidiTrack(), 0
        for msg in old:
            pending += msg.time
            if getattr(msg, 'channel', channel) != channel:
                continue
            track.append(msg.copy(time=pending))
            pending = 0
        if pending:
            track.append(mido.MetaMessage('end_of_track', time=pending))
        result.tracks.append(track)
    return result


def stems(args):
    original = core.source(args.midi)
    midi = core.load_midi(original)
    channels = core.midi_summary(midi)['channels_zero_based']
    if not channels:
        raise ValueError('No notes to render')
    # Validate extraction before creating any output.
    selected_channel(midi, channels[0])
    sf2 = core.soundfont(args)
    dest = fresh_directory(args.out_dir)
    entries = []
    for channel in channels:
        name = f'channel-{channel+1:02d}'
        mid_path, wav_path = dest/f'{name}.mid', dest/f'{name}.wav'
        selected_channel(midi, channel).save(mid_path)
        render_args = argparse.Namespace(sf2=str(sf2), font=None, midi=str(mid_path),
            wav=str(wav_path), overwrite=False, piano=False, gain=args.gain, rate=args.rate,
            bank_mode=args.bank_mode, dry=True, profile=args.profile, interpolation=args.interpolation)
        with contextlib.redirect_stdout(io.StringIO()):
            core.render(render_args)
        report = json.loads(Path(str(wav_path)+'.render.json').read_text())
        if report['synth_warnings']:
            raise ValueError(f'Review synth warnings in {wav_path}.render.json before mixing')
        # Compensate any automatic safety gain reduction when reassembling the mix.
        correction = 20*math.log10(args.gain/report['gain'])
        entries.append(dict(channel=channel, midi=mid_path.name, path=wav_path.name,
                            gain_db=round(correction,6), audio=report['audio']))
    manifest = dict(source_midi=str(original), soundfont=str(sf2),
                    alignment='All stems start at source time zero; release tails may differ',
                    dry=True, tracks=entries, midi=core.midi_summary(midi))
    (dest/'stems.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (dest/'mix.json').write_text(json.dumps(dict(tracks=[dict(path=e['path'],gain_db=e['gain_db'])
                                                       for e in entries]),indent=2)+'\n')
    core.emit(manifest)


def loudness(path, filters='anull'):
    result = run(ffmpeg()+['-i',str(path),'-af',filters+',loudnorm=I=-20:TP=-1:LRA=11:print_format=json',
                          '-f','null','-'])
    start = result.stderr.rfind('{')
    try:
        info = json.loads(result.stderr[start:result.stderr.rfind('}')+1])
        measured = {key: float(info[key]) for key in ('input_i','input_tp','input_lra')}
    except (ValueError,KeyError) as exc:
        raise ValueError('Unable to measure audio loudness') from exc
    if not all(math.isfinite(x) for x in measured.values()):
        raise ValueError('Audio is silent or too short for a useful loudness comparison')
    return measured


def mix(args):
    config_path = core.source(args.config)
    config = json.loads(config_path.read_text())
    specs = config['tracks']
    if not 1 <= len(specs) <= 32:
        raise ValueError('Mix needs 1..32 tracks')
    paths = [core.source(config_path.parent/s['path']) for s in specs]
    ir = core.source(config_path.parent/config['room_ir']) if config.get('room_ir') else None
    dest = writable(args.wav, [config_path,*paths,*([ir] if ir else [])])
    if dest.suffix.lower() != '.wav':
        raise ValueError('Mix output must be .wav')
    writable(str(dest)+'.mix.json')
    ceiling = core.number(config.get('peak_dbfs',-1.5),-12,-.5,'peak_dbfs')
    tail = core.number(config.get('tail_seconds',2),0,30,'tail_seconds')
    duration = config.get('duration_seconds')
    if duration is not None:
        duration = core.number(duration,.1,3600,'duration_seconds')
    fade = core.number(config.get('fade_out_seconds',0),0,duration or 0,'fade_out_seconds')
    command, graph, dry, wet = ffmpeg(), [], [], []
    for i,(path,spec) in enumerate(zip(paths,specs)):
        command += ['-i',str(path)]
        gain = core.number(spec.get('gain_db',0),-60,24,'gain_db')
        balance = core.number(spec.get('balance',0),-1,1,'balance')
        filters = ['aresample=44100','aformat=sample_fmts=fltp:channel_layouts=stereo',
                   'asetpts=PTS-STARTPTS',f'volume={gain}dB']
        if balance:
            filters.append(f'pan=stereo|c0={min(1,1-balance)}*c0|c1={min(1,1+balance)}*c1')
        highpass = core.number(spec.get('highpass_hz',0),0,1000,'highpass_hz')
        if highpass:
            filters.append(f'highpass=f={highpass}')
        for eq in spec.get('eq',[]):
            f = core.number(eq['hz'],20,20000,'EQ frequency')
            g = core.number(eq['gain_db'],-18,18,'EQ gain')
            q = core.number(eq.get('q',1),.1,10,'EQ Q')
            filters.append(f'equalizer=f={f}:t=q:w={q}:g={g}')
        send = core.number(spec.get('room_send',0),0,1,'room_send')
        if send and not ir:
            raise ValueError('room_send needs a supplied room_ir file')
        graph.append(f'[{i}:a]'+','.join(filters)+f'[t{i}]')
        if send:
            graph += [f'[t{i}]asplit=2[d{i}][s{i}]',f'[s{i}]volume={send}[w{i}]']
            wet.append(f'[w{i}]')
        else:
            graph.append(f'[t{i}]anull[d{i}]')
        dry.append(f'[d{i}]')
    graph.append(''.join(dry)+f'amix=inputs={len(dry)}:normalize=0:duration=longest[dry]')
    if ir and wet:
        command += ['-i',str(ir)]
        graph.append(''.join(wet)+f'amix=inputs={len(wet)}:normalize=0:duration=longest,apad=pad_dur={tail}[send]')
        graph.append(f'[{len(paths)}:a]aresample=44100,aformat=channel_layouts=stereo[ir]')
        graph.append('[send][ir]afir=dry=1:wet=1:irfmt=input[room]')
        graph.append('[dry][room]amix=inputs=2:normalize=0:duration=longest[sum]')
    else:
        graph.append('[dry]anull[sum]')
    ending = []
    if duration is not None:
        ending += [f'apad=whole_dur={duration}',f'atrim=duration={duration}']
    if fade:
        ending += [f'afade=t=out:st={duration-fade}:d={fade}']
    graph.append('[sum]'+(','.join(ending) or 'anull')+'[out]')
    with tempfile.TemporaryDirectory(prefix='sf2-mix-',dir=dest.parent) as tmp:
        floating = Path(tmp)/'mix-float.wav'
        run(command+['-filter_complex',';'.join(graph),'-map','[out]','-c:a','pcm_f32le',str(floating)])
        measurement = loudness(floating)
        gain = min(0,ceiling-measurement['input_tp'])
        final = Path(tmp)/'mix.wav'
        run(ffmpeg()+['-i',str(floating),'-af',f'volume={gain}dB','-ar','44100','-c:a','pcm_s16le',str(final)])
        stats = core.audio_stats(final)
        if stats['clipped_samples']:
            raise ValueError('Mix clipped; inspect input files and gain settings')
        final_measurement = loudness(final)
        if final_measurement['input_tp'] > ceiling+.2:
            raise ValueError('Final true peak exceeds headroom target; lower peak_dbfs')
        final.replace(dest)
    report = dict(wav=str(dest),config=str(config_path),audio=stats,master_gain_db=gain,
                  pre_master_loudness=measurement,final_loudness=final_measurement,room_ir=str(ir) if ir else None,
                  listening_review='not performed by this helper')
    Path(str(dest)+'.mix.json').write_text(json.dumps(report,indent=2)+'\n')
    core.emit(report)


def compare(args):
    paths = [core.source(args.a),core.source(args.b)]
    start = core.number(args.start,0,3600,'start')
    duration = core.number(args.duration,3,120,'duration')
    target = core.number(args.lufs,-40,-10,'LUFS target')
    ceiling = core.number(args.peak,-12,-.5,'peak ceiling')
    filters = f'atrim=start={start}:duration={duration},asetpts=PTS-STARTPTS'
    measures = [loudness(p,filters) for p in paths]
    # A common lower level preserves both dynamics and equality without a limiter.
    target = min(target,*(m['input_i']+ceiling-m['input_tp'] for m in measures))
    dest = fresh_directory(args.out_dir)
    report = dict(target_lufs=target,start_seconds=start,duration_seconds=duration,versions=[])
    for name,path,measurement in zip(('A','B'),paths,measures):
        gain = target-measurement['input_i']
        output = dest/f'{name}.wav'
        run(ffmpeg()+['-i',str(path),'-af',filters+f',volume={gain}dB',
                      '-ar','44100','-ac','2','-c:a','pcm_s16le',str(output)])
        stats = core.audio_stats(output)
        if abs(stats['seconds']-duration) > 1/44100 or stats['clipped_samples']:
            raise ValueError('Comparison needs the requested passage in both files without clipping')
        actual = loudness(output)
        if abs(actual['input_i']-target) > .2:
            raise ValueError('Loudness match outside 0.2 LU; inspect the comparison files')
        if actual['input_tp'] > ceiling+.2:
            raise ValueError('Comparison true peak exceeds headroom target')
        report['versions'].append(dict(label=name,source=str(path),preview=str(output),
                                       gain_db=gain,audio=stats,loudness=actual))
    run(ffmpeg()+['-i',str(dest/'A.wav'),'-i',str(dest/'B.wav'),'-filter_complex',
        '[0:a]apad=pad_dur=0.6[a];[a][1:a]concat=n=2:v=0:a=1[out]',
        '-map','[out]','-c:a','pcm_s16le',str(dest/'A-then-B.wav')])
    report['listening_review'] = 'pending: listen to A and B; signal checks do not choose a winner'
    (dest/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    core.emit(report)


def render_sfz(args):
    exe = args.renderer or shutil.which('sfizz_render') or shutil.which('sfizz-render')
    if not exe:
        raise ValueError('Optional SFZ renderer unavailable. Install sfizz with its offline renderer or pass --renderer. SF2 rendering remains available.')
    sfz, original = core.source(args.sfz), core.source(args.midi)
    midi = core.load_midi(original)
    channels = core.midi_summary(midi)['channels_zero_based']
    if args.channel is not None:
        if args.channel not in channels:
            raise ValueError('Selected channel has no notes')
        midi = selected_channel(midi,args.channel)
    elif len(channels) != 1:
        raise ValueError('SFZ renders one instrument; select --channel for a multi-instrument MIDI')
    if any(m.type=='sysex' or (m.type=='midi_port' and m.port!=0) for t in midi.tracks for m in t):
        raise ValueError('Inspect SysEx/port routing before SFZ conversion')
    dest = writable(args.wav,[sfz,original])
    if dest.suffix.lower() != '.wav':
        raise ValueError('SFZ output must be .wav')
    log = writable(str(dest)+'.sfizz.log')
    report_path = writable(str(dest)+'.render.json')
    with tempfile.TemporaryDirectory(prefix='sfz-render-',dir=dest.parent) as tmp:
        selected, wav = Path(tmp)/'selected.mid', Path(tmp)/'render.wav'
        midi.save(selected)
        proc = subprocess.run([str(exe),'--sfz',str(sfz),'--midi',str(selected),
                               '--wav',str(wav),'--samplerate',str(args.rate)],
                              capture_output=True,text=True,timeout=max(120,midi.length*2+60))
        messages = proc.stdout+'\n'+proc.stderr
        log.write_text(messages)
        if proc.returncode or not wav.is_file():
            raise ValueError(f'SFZ render failed; see {log}')
        stats = core.audio_stats(wav)
        warnings = [line for line in messages.splitlines() if any(w in line.lower()
                    for w in ('warning','error','unsupported','not found'))]
        if stats['clipped_samples'] or warnings:
            raise ValueError(f'SFZ render needs review (clipping or sampler warnings); see {log}')
        wav.replace(dest)
    report=dict(wav=str(dest),sfz=str(sfz),midi=str(original),channel=args.channel,audio=stats,
                synth_warnings=warnings,listening_review='not performed by this helper')
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    core.emit(report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command',required=True)
    p = sub.add_parser('stems')
    p.add_argument('--midi',required=True)
    p.add_argument('--out-dir',required=True)
    core.font_options(p)
    p.add_argument('--gain',type=float,default=.5)
    p.add_argument('--rate',type=int,choices=(44100,48000),default=44100)
    p.add_argument('--bank-mode',choices=('gs','gm','xg','mma'),default='gs')
    p.add_argument('--profile',choices=('default','generaluser'),default='default')
    p.add_argument('--interpolation',type=int,choices=(0,1,4,7))
    p.set_defaults(func=stems)
    p = sub.add_parser('mix')
    p.add_argument('--config',required=True)
    p.add_argument('--wav',required=True)
    p.set_defaults(func=mix)
    p = sub.add_parser('compare')
    p.add_argument('--a',required=True)
    p.add_argument('--b',required=True)
    p.add_argument('--out-dir',required=True)
    p.add_argument('--start',type=float,default=0)
    p.add_argument('--duration',type=float,default=12)
    p.add_argument('--lufs',type=float,default=-20)
    p.add_argument('--peak',type=float,default=-1.5)
    p.set_defaults(func=compare)
    p = sub.add_parser('render-sfz')
    p.add_argument('--sfz',required=True)
    p.add_argument('--midi',required=True)
    p.add_argument('--wav',required=True)
    p.add_argument('--channel',type=int,choices=range(16))
    p.add_argument('--renderer')
    p.add_argument('--rate',type=int,choices=(44100,48000),default=44100)
    p.set_defaults(func=render_sfz)
    args = parser.parse_args()
    args.func(args)


if __name__=='__main__':
    try:
        main()
    except (ValueError,OSError,KeyError,TypeError,subprocess.SubprocessError) as error:
        print(f'Error: {error}',file=sys.stderr)
        sys.exit(1)
