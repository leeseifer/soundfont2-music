"""Asset restoration must preserve good files and reject unsafe/corrupt inputs."""
import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

import fetch_assets as fetch


class AssetRestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.data=b'verified publisher sample'
        self.spec=dict(path='sample.wav',target=self.root/'sample.wav',bytes=len(self.data),
                       sha256=hashlib.sha256(self.data).hexdigest(),url='https://raw.githubusercontent.com/test/pinned/sample.wav')

    def test_rejects_traversal_and_symlink_escape(self):
        for path in ('../outside.wav','/outside.wav','folder/../../outside.wav','folder\\outside.wav'):
            with self.subTest(path=path),self.assertRaises(ValueError):fetch.safe_target(self.root,path)
        (self.root/'escape').symlink_to(self.root.parent,target_is_directory=True)
        with self.assertRaises(ValueError):fetch.safe_target(self.root,'escape/outside.wav')

    def test_read_only_check_never_downloads(self):
        opener=Mock(side_effect=AssertionError('unexpected network'))
        with self.assertRaisesRegex(ValueError,'Missing or invalid'):
            fetch.ensure_asset(self.spec,check=True,opener=opener)
        opener.assert_not_called()
        self.assertFalse(self.spec['target'].exists())

    def test_download_is_verified_and_existing_valid_file_avoids_network(self):
        opener=Mock(return_value=io.BytesIO(self.data))
        self.assertEqual(fetch.ensure_asset(self.spec,opener=opener),'downloaded')
        self.assertEqual(self.spec['target'].read_bytes(),self.data)
        self.assertEqual(fetch.ensure_asset(self.spec,opener=Mock(side_effect=AssertionError('unexpected network'))),'verified')

    def test_corrupt_download_cannot_replace_existing_file(self):
        original=b'local custom instrument';self.spec['target'].write_bytes(original)
        opener=Mock(return_value=io.BytesIO(b'x'*len(self.data)))
        with self.assertRaisesRegex(ValueError,'Existing asset differs'):
            fetch.ensure_asset(self.spec,opener=opener)
        opener.assert_not_called()
        with self.assertRaisesRegex(ValueError,'checksum mismatch'):
            fetch.ensure_asset(self.spec,repair=True,opener=opener)
        self.assertEqual(self.spec['target'].read_bytes(),original)
        self.assertFalse(list(self.root.glob('*.partial')))


if __name__=='__main__':unittest.main()
