"""Offline-only validation for Wikimedia Commons native-control importer."""
import json
import pathlib
import tempfile
import unittest
import wave
from array import array

from public_native_samples import SAMPLES, collect, get_audio


class NativeAudioTests(unittest.TestCase):
    def setUp(self):
        self.private=tempfile.TemporaryDirectory()
        self.root=pathlib.Path(self.private.name)
        self.root.chmod(0o700)
        self.calls=[]

    def tearDown(self):
        self.private.cleanup()

    def fetcher(self,url):
        self.assertIn(url,[item[3] for item in SAMPLES])
        self.calls.append(url)
        return b"OggS synthetic data; converter mocked"

    def converter(self,source,destination):
        self.assertEqual(source.read_bytes()[:4],b"OggS")
        with wave.open(str(destination),"wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(16000)
            out.writeframes(array("h",[500]*16000).tobytes())

    def test_private_two_sample_manifest_and_attribution(self):
        target=self.root/"native-controls"
        rows=collect(target,fetcher=self.fetcher,converter=self.converter)
        self.assertEqual(len(rows),2)
        self.assertEqual(len(self.calls),2)
        self.assertEqual([x["reference"] for x in rows],["czapka","ciasto"])
        self.assertEqual(len(rows[0]["audio_sha256"]),64)
        self.assertEqual(rows[0]["study_role"],"native_speaker_asr_control")
        self.assertTrue(rows[0]["source_page"].startswith("https://commons.wikimedia.org/wiki/File:"))
        self.assertEqual(json.loads((target/"manifest.json").read_text()),rows)
        self.assertIn("Rogra",(target/"ATTRIBUTION.txt").read_text())
        self.assertIn("Frizabela",(target/"ATTRIBUTION.txt").read_text())
        self.assertEqual(target.stat().st_mode&0o777,0o700)
        self.assertEqual((target/"manifest.json").stat().st_mode&0o777,0o600)
        self.assertEqual((target/"ATTRIBUTION.txt").stat().st_mode&0o777,0o600)
        with self.assertRaisesRegex(ValueError,"not-yet-existing"):
            collect(target,fetcher=self.fetcher,converter=self.converter)

    def test_rejects_large_batch(self):
        with self.assertRaisesRegex(ValueError,"between one and six"):
            collect(self.root/"fail",count=7,fetcher=self.fetcher,converter=self.converter)
        self.assertFalse((self.root/"fail").exists())

    def test_rejects_insecure_parent(self):
        self.root.chmod(0o755)
        with self.assertRaisesRegex(ValueError,"0700"):
            collect(self.root/"bad",fetcher=self.fetcher,converter=self.converter)
        self.assertFalse((self.root/"bad").exists())

    def test_invalid_recordings_do_not_produce_manifest(self):
        def silent_converter(source,destination):
            with wave.open(str(destination),"wb") as out:
                out.setnchannels(1)
                out.setsampwidth(2)
                out.setframerate(16000)
                out.writeframes(array("h",[0]*16000).tobytes())
        target=self.root/"quiet"
        with self.assertRaisesRegex(ValueError,"Unusable"):
            collect(target,fetcher=self.fetcher,converter=silent_converter)
        self.assertFalse((target/"manifest.json").exists())

    def test_fixed_source_list_rejects_arbitrary_urls(self):
        with self.assertRaisesRegex(ValueError,"pre-reviewed"):
            get_audio("https://malicious.example/audio.ogg")


if __name__=="__main__":
    unittest.main()
