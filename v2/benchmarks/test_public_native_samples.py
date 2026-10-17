"""Offline-only validation for Wikimedia Commons native-control importer."""
import json
import pathlib
import tempfile
import unittest
import urllib.error
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

    def test_429_respects_retry_after_without_any_automatic_retry(self):
        calls=[]
        def throttled(request, timeout):
            calls.append(request)
            self.assertIn("github.com/AndrewDionne/LearnPolish",
                          request.get_header("User-agent"))
            self.assertEqual(timeout,20)
            raise urllib.error.HTTPError(request.full_url,429,"Too Many Requests",
                                         {"Retry-After":"180"},None)
        with self.assertRaisesRegex(ValueError,"Retry-After: 180"):
            get_audio(SAMPLES[0][3],opener=throttled)
        self.assertEqual(len(calls),1)

    def test_429_and_failed_conversion_leave_no_partial_folder(self):
        target=self.root/"throttled"
        def denied(_):
            raise ValueError("Wikimedia Commons returned HTTP 429")
        with self.assertRaisesRegex(ValueError,"HTTP 429"):
            collect(target,fetcher=denied,converter=self.converter)
        self.assertFalse(target.exists())
        self.assertEqual(list(self.root.glob(".ptp-commons-staging-*")),[])
        seen=[0]
        def fail_second(source,destination):
            seen[0]+=1
            if seen[0]==2:
                raise OSError("ffmpeg failed")
            self.converter(source,destination)
        with self.assertRaisesRegex(OSError,"ffmpeg failed"):
            collect(target,fetcher=self.fetcher,converter=fail_second)
        self.assertFalse(target.exists())
        self.assertEqual(list(self.root.glob(".ptp-commons-staging-*")),[])

    def test_local_commons_originals_skip_network_entirely(self):
        manual=self.root/"manual"
        manual.mkdir()
        (manual/"Pl-czapka.ogg").write_bytes(b"OggS fake first")
        (manual/"Pl-ciasto.ogg").write_bytes(b"OggS fake second")
        def unexpected(_):
            raise AssertionError("Local originals MUST NOT make network requests")
        target=self.root/"converted-locally"
        rows=collect(target,count=2,fetcher=unexpected,
                     converter=self.converter,source_dir=manual)
        self.assertEqual([x["reference"] for x in rows],["czapka","ciasto"])
        self.assertTrue((target/"manifest.json").is_file())
        self.assertFalse((target/"originals").exists())
        # User-supplied originals remain untouched.
        self.assertTrue((manual/"Pl-czapka.ogg").exists())

    def test_manual_folder_rejects_missing_symlinked_and_invalid_audio(self):
        manual=self.root/"manual"
        manual.mkdir()
        with self.assertRaisesRegex(ValueError,"missing"):
            collect(self.root/"out",count=1,converter=self.converter,source_dir=manual)
        self.assertFalse((self.root/"out").exists())
        (manual/"Pl-czapka.ogg").write_bytes(b"not an ogg")
        with self.assertRaisesRegex(ValueError,"valid-header Ogg"):
            collect(self.root/"out",count=1,converter=self.converter,source_dir=manual)
        self.assertFalse((self.root/"out").exists())
        (manual/"Pl-czapka.ogg").unlink()
        (manual/"Pl-czapka.ogg").symlink_to(self.root/"elsewhere")
        with self.assertRaisesRegex(ValueError,"missing or symlinked"):
            collect(self.root/"out",count=1,converter=self.converter,source_dir=manual)
        self.assertFalse((self.root/"out").exists())

    def test_fixed_source_list_rejects_arbitrary_urls(self):
        with self.assertRaisesRegex(ValueError,"pre-reviewed"):
            get_audio("https://malicious.example/audio.ogg")


if __name__=="__main__":
    unittest.main()
