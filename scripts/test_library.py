"""Rights-filter and installed-library routing behavior."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import midi_references as refs
import music_audio as audio
import sf2_music as core


class ReferenceRightsTests(unittest.TestCase):
    def setUp(self):
        self.data = {'entries': [dict(id=ident, title='Calm theme', themes=['calm'],
            reference_use='Lyrical movement', path='example.mid', analysis={}, rights_status=status)
            for ident,status in [('legacy','public_domain_user_declared'),
                                 ('documented','public_domain_source_documented'),
                                 ('cc0','CC0-1.0'),('by','CC-BY-4.0'),('unknown','unknown')]]}

    def test_default_public_domain_filter_rejects_unknown_and_attribution(self):
        found=refs.select_references(self.data,'calm',10)
        self.assertEqual({x['id'] for x in found['matches']},{'legacy','documented','cc0'})

    def test_source_documented_filter_excludes_user_declaration(self):
        found=refs.select_references(self.data,'calm',10,'source-documented')
        self.assertEqual({x['id'] for x in found['matches']},{'documented','cc0'})
        self.assertTrue(all(x['rights_status']!='public_domain_user_declared' for x in found['matches']))

    def test_name_match_cannot_bypass_rights_filter(self):
        self.assertEqual(refs.select_references(self.data,'unknown',10)['returned'],0)


class InstrumentRoutingTests(unittest.TestCase):
    def test_qualified_alias_resolves_to_file(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'instrument.sfz';p.write_text('<region> sample=a.wav')
            cat={'entries':[{'id':'test','path':str(p),'qualification':{'status':'technical_pass'}}]}
            with patch.object(audio,'instrument_catalog',return_value=cat):
                self.assertEqual(audio.installed_instrument('test'),p.resolve())
                with self.assertRaisesRegex(ValueError,'Unknown instrument'):
                    audio.installed_instrument('missing')

    def test_unqualified_mapping_is_rejected(self):
        cat={'entries':[{'id':'test','path':'not-used.sfz','qualification':{'status':'failed'}}]}
        with patch.object(audio,'instrument_catalog',return_value=cat):
            with self.assertRaisesRegex(ValueError,'not passed'):
                audio.installed_instrument('test')

    def test_missing_configured_renderer_does_not_silently_substitute(self):
        with patch.object(core,'defaults',return_value={'sfz_renderer':'/missing/renderer'}), \
             patch.object(core.shutil,'which',return_value='/another/renderer'):
            self.assertIsNone(core.sfz_renderer())


if __name__=='__main__':
    unittest.main()
