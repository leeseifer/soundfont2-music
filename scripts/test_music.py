"""Behavioral checks for expressive MIDI, timing preservation, and real audio workflows.

Run: python -m unittest discover -s scripts -p test_music.py -v
Audio tests require the installed band font, FluidSynth, and FFmpeg.
"""
import argparse
import contextlib
import copy
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import wave
from array import array
from unittest.mock import patch

import sf2_music as core
import music_audio as audio
import midi_references as references
from performance import TempoMap, performed_notes


def absolute_events(midi, channel=None):
    result=[]
    for t in midi.tracks:
        tick=0
        for m in t:
            tick+=m.time
            if not m.is_meta and (channel is None or getattr(m,'channel',None)==channel):
                result.append((tick,str(m.copy(time=0))))
    return sorted(result)


def example():
    return dict(title='Performance validation phrase',bpm=120,beats=16,time_signature=[4,4],tracks=[
        dict(name='Piano',channel=0,bank=0,program=0,volume=90,pan=66,
             notes=[dict(beat=b,duration=.7,pitch=p,velocity=82+i%4*3)
                    for i,(b,p) in enumerate([(0,62),(1,66),(2,69),(3,66),(4,61),(5,64),(6,69),(7,64),
                                              (8,59),(9,62),(10,66),(11,62),(12,62),(13,66),(14,74)])]),
        dict(name='Guitar',channel=1,bank=0,program=25,volume=85,pan=40,
             notes=[dict(beat=bar*4+j*.02,duration=1.3,pitch=p,velocity=72+j,
                         group=f'strum-{bar}') for bar,ps in enumerate(
                         [[50,57,62,66],[45,52,57,61],[47,54,59,62],[50,57,62,66]]) for j,p in enumerate(ps)]),
        dict(name='Drums',channel=9,bank=128,program=0,volume=84,pan=64,
             notes=[dict(beat=b,duration=.12,pitch=36 if b%2==0 else 38,velocity=90 if b%2==0 else 82)
                    for b in range(15)])])


class MidiTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.out=Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def compile(self,score,name='theme'):
        path=self.out/f'{name}.json'
        path.write_text(json.dumps(score))
        args=argparse.Namespace(sf2=None,font='band',score=str(path),midi=str(self.out/f'{name}.mid'),overwrite=False)
        with contextlib.redirect_stdout(io.StringIO()): core.compose(args)
        return core.load_midi(args.midi)

    def test_portable_configuration_and_reference_without_local_file(self):
        (self.out/'defaults.json').write_text(json.dumps({
            'soundfont':'bank.sf2', 'midi_references':{'catalog':'catalog.json'}}))
        (self.out/'bank.sf2').write_bytes(b'configuration path fixture')
        (self.out/'catalog.json').write_text(json.dumps({'entries':[]}))
        with patch.object(core,'ROOT',self.out), patch.object(references,'ROOT',self.out):
            args=argparse.Namespace(sf2=None,font=None)
            self.assertEqual(core.soundfont(args),(self.out/'bank.sf2').resolve())
            self.assertEqual(references.catalog()['entries'],[])

    def test_local_overrides_preserve_other_font_aliases(self):
        (self.out/'defaults.json').write_text(json.dumps({'soundfonts':{
            'piano':{'name':'Bundled','path':'bank.sf2'},
            'band':{'name':'Bundled','path':'bank.sf2'}}}))
        (self.out/'local-defaults.json').write_text(json.dumps({'soundfonts':{
            'piano':{'path':'personal.sf2'}}}))
        with patch.object(core,'ROOT',self.out):
            settings=core.defaults()
            self.assertEqual(settings['soundfonts']['piano']['path'],'personal.sf2')
            self.assertEqual(settings['soundfonts']['band']['path'],'bank.sf2')
            self.assertEqual(settings['soundfonts']['piano']['name'],'Bundled')

    def test_old_score_has_exact_notes_and_duration(self):
        score=example(); midi=self.compile(score)
        self.assertEqual(midi.length,8)
        expected=sum(len(t['notes']) for t in score['tracks'])
        self.assertEqual(core.midi_summary(midi)['note_count'],expected)
        self.assertFalse(any(m.type=='pitchwheel' or (m.type=='control_change' and m.control==64)
                             for t in midi.tracks for m in t))

    def test_tempo_map_integrates_and_extracts(self):
        score=example(); score['tempo_changes']=[dict(beat=8,bpm=60)]
        midi=self.compile(score)
        self.assertEqual(midi.length,12)
        separated=audio.selected_channel(midi,1)
        self.assertEqual(separated.length,12)
        self.assertEqual(absolute_events(midi,1),absolute_events(separated,1))
        self.assertEqual(core.midi_summary(separated)['channels_zero_based'],[1])

    def test_controller_order_and_end_resets(self):
        score=example(); t=score['tracks'][0]
        t['controllers']=[dict(beat=0,control=64,value=127),dict(beat=4,control=11,value=85)]
        t['pitch_bends']=[dict(beat=1,value=4096)]
        t['pitch_bend_range']=2
        midi=self.compile(score); messages=midi.tracks[1]
        pedal_idx=next(i for i,m in enumerate(messages) if m.type=='control_change' and m.control==64)
        note_idx=next(i for i,m in enumerate(messages) if m.type=='note_on')
        self.assertLess(pedal_idx,note_idx)
        self.assertEqual([m.value for m in messages if m.type=='control_change' and m.control==64], [127,0])
        self.assertEqual([m.pitch for m in messages if m.type=='pitchwheel'],[4096,0])
        extracted=audio.selected_channel(midi,0)
        self.assertEqual(absolute_events(midi,0),absolute_events(extracted,0))

    def test_grouped_variation_is_reproducible_and_preserves_strum(self):
        score=example(); t=score['tracks'][1]
        t['humanize']=dict(timing_ms=5,velocity=3,duration_percent=2,seed=9)
        a=performed_notes(t,TempoMap(score)); b=performed_notes(t,TempoMap(score))
        self.assertEqual(a,b)
        self.assertAlmostEqual(a[5]['beat']-a[4]['beat'],.02)
        self.assertNotEqual(a[4]['beat'],t['notes'][4]['beat'])

    def test_fixed_notes_bypass_shaping(self):
        score=example(); t=score['tracks'][0]; t['humanize']=dict(timing_ms=20,velocity=10)
        t['notes'][0]['fixed']=True
        self.assertEqual(performed_notes(t,TempoMap(score))[0],t['notes'][0])

    def test_strum_spacing_preserved_at_score_boundary(self):
        score=example(); t=score['tracks'][1]
        t['groove']=dict(timing_ms=[-20])
        notes=performed_notes(t,TempoMap(score))
        self.assertEqual(notes[0]['beat'],0)
        for i in (1,2,3):
            self.assertAlmostEqual(notes[i]['beat']-notes[0]['beat'],i*.02)

    def test_millisecond_groove_across_tempo_change(self):
        score=example(); score['tempo_changes']=[dict(beat=8,bpm=60)]
        t=score['tracks'][0]; t['groove']=dict(timing_ms=[10])
        tempo=TempoMap(score); notes=performed_notes(t,tempo)
        for old,new in zip(t['notes'],notes):
            self.assertAlmostEqual(tempo.seconds(new['beat'])-tempo.seconds(old['beat']),.010)

    def test_authored_overlap_rejected(self):
        score=example(); score['tracks'][0]['notes'].append(dict(beat=.2,pitch=62,duration=.5))
        with self.assertRaisesRegex(ValueError,'overlap'): self.compile(score)

    def test_guitar_string_collision_rejected(self):
        score=example(); t=score['tracks'][1]
        t['guitar']={}
        t['notes']=[dict(beat=0,pitch=40,duration=1,string=0,fret=0),
                    dict(beat=.5,pitch=42,duration=.5,string=0,fret=2)]
        with self.assertRaisesRegex(ValueError,'same guitar string'): self.compile(score)

    def test_valid_guitar_annotation(self):
        score=example(); t=score['tracks'][1]; t['guitar']={}
        t['notes']=[dict(beat=0,pitch=40,duration=.7,string=0,fret=0,group='a'),
                    dict(beat=.02,pitch=47,duration=.7,string=1,fret=2,group='a')]
        self.compile(score)

    def test_invalid_expression_and_preset_rejected(self):
        for changes,match in [({'controllers':[dict(beat=0,control=64,value=128)]},'controller value'),
                              ({'pitch_bends':[dict(beat=0,value=8192)]},'pitch bend'),
                              ({'program':999},'program'),
                              ({'humanize':dict(timing_mss=5)},'Unknown humanize')]:
            score=example(); score['tracks'][0].update(changes)
            with self.subTest(changes=changes):
                with self.assertRaisesRegex(ValueError,match): self.compile(score)

    def test_sysex_extraction_rejected(self):
        mido=core.midi_module(); midi=self.compile(example())
        midi.tracks[0].insert(0,mido.Message('sysex',data=(1,2)))
        with self.assertRaisesRegex(ValueError,'SysEx'): audio.selected_channel(midi,0)

    def test_missing_sfz_dependency_is_explicit(self):
        with patch('music_audio.shutil.which',return_value=None):
            with self.assertRaisesRegex(ValueError,'Optional SFZ renderer unavailable'):
                audio.render_sfz(argparse.Namespace(renderer=None))


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('fluidsynth'),'audio dependencies unavailable')
class AudioTests(unittest.TestCase):
    setUp = MidiTests.setUp
    tearDown = MidiTests.tearDown
    compile = MidiTests.compile

    def test_render_stems_mix_and_match_loudness(self):
        score=example()
        score['tracks'][0]['controllers']=[dict(beat=.1,control=64,value=127),dict(beat=3.8,control=64,value=0)]
        self.compile(score)
        stem_args=argparse.Namespace(midi=str(self.out/'theme.mid'),sf2=None,font='band',
          out_dir=str(self.out/'stems'),gain=.5,rate=44100,bank_mode='gs',profile='generaluser',interpolation=7)
        with contextlib.redirect_stdout(io.StringIO()): audio.stems(stem_args)
        manifest=json.loads((self.out/'stems/stems.json').read_text())
        self.assertEqual(len(manifest['tracks']),3)
        for entry in manifest['tracks']:
            self.assertEqual(entry['audio']['clipped_samples'],0)
            report=json.loads((self.out/'stems'/str(entry['path']+'.render.json')).read_text())
            self.assertFalse(report['synth_warnings'])
            self.assertEqual(report['interpolation'],7)
        config=self.out/'stems/mix.json'
        data=json.loads(config.read_text()); data.update(duration_seconds=8,fade_out_seconds=.4)
        data['tracks'][1].update(highpass_hz=70,balance=-.1,eq=[dict(hz=300,gain_db=-1,q=.8)])
        config.write_text(json.dumps(data))
        output=self.out/'mixed.wav'
        with contextlib.redirect_stdout(io.StringIO()): audio.mix(argparse.Namespace(config=str(config),wav=str(output)))
        stats=core.audio_stats(output)
        self.assertEqual(stats['seconds'],8)
        self.assertEqual(stats['clipped_samples'],0)
        louder=self.out/'louder.wav'
        audio.run(audio.ffmpeg()+['-i',str(output),'-af','volume=-6dB','-c:a','pcm_s16le',str(louder)])
        compare=argparse.Namespace(a=str(output),b=str(louder),start=0,duration=6,lufs=-20,peak=-1.5,out_dir=str(self.out/'compare'))
        with contextlib.redirect_stdout(io.StringIO()): audio.compare(compare)
        report=json.loads((self.out/'compare/comparison.json').read_text())
        self.assertLess(abs(report['versions'][0]['loudness']['input_i']-report['versions'][1]['loudness']['input_i']),.2)
        self.assertTrue(report['listening_review'].startswith('pending'))
        self.assertEqual(core.audio_stats(self.out/'compare/A-then-B.wav')['seconds'],12.6)

    def test_shared_room_is_rendered_and_input_preserved(self):
        self.compile(example())
        dest=self.out/'source.wav'
        args=argparse.Namespace(sf2=None,font='band',midi=str(self.out/'theme.mid'),wav=str(dest),
          overwrite=False,piano=False,gain=.3,rate=44100,bank_mode='gs',dry=True,profile='default',interpolation=None)
        with contextlib.redirect_stdout(io.StringIO()): core.render(args)
        original=dest.read_bytes()
        # Synthetic test impulse; never presented as a sampled room library.
        impulse=array('h',[0]*22050)
        impulse[0]=16000; impulse[4410]=8000; impulse[8820]=4000
        ir=self.out/'test-ir.wav'
        with wave.open(str(ir),'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(44100); w.writeframes(impulse.tobytes())
        config=self.out/'room.json'
        config.write_text(json.dumps(dict(tracks=[dict(path='source.wav',room_send=.2)],
                                         room_ir='test-ir.wav',tail_seconds=1,duration_seconds=8,fade_out_seconds=.4)))
        output=self.out/'room.wav'
        with contextlib.redirect_stdout(io.StringIO()): audio.mix(argparse.Namespace(config=str(config),wav=str(output)))
        self.assertEqual(core.audio_stats(output)['clipped_samples'],0)
        self.assertEqual(dest.read_bytes(),original)
        with self.assertRaisesRegex(ValueError,'replace an input'):
            audio.mix(argparse.Namespace(config=str(config),wav=str(dest)))


if __name__=='__main__': unittest.main()
