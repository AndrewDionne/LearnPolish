"""Original-audio syllable audition: synthetic PCM, no network or scores."""
import hashlib
import io
import json
import math
import pathlib
import stat
import tempfile
import unittest
import wave
from array import array

from syllable_audio_clips import _manual_intervals, prepare_clips


def wav_bytes(seconds=1.6):
    out=io.BytesIO()
    with wave.open(out,"wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(array("h",[round(4500*math.sin(i*.11)) for i in range(round(seconds*16000))]).tobytes())
    return out.getvalue()


def time_record(raw, boundaries=None):
    cuts=boundaries or [0,.4,.8,1.2,1.6]
    words=["Świę","to","krzy","ska"]
    return {"schemaVersion":1,"method":"manual-syllable-audition-v1",
       "polish":"Świętokrzyska","syllables":words,"sourceSha256":hashlib.sha256(raw).hexdigest(),
       "sourceBytes":len(raw),"sourceDurationSeconds":1.6,
       "intervals":[{"polish":words[i],"startSeconds":cuts[i],
                    "endSeconds":cuts[i+1]} for i in range(4)],
       "assessmentStatus":"timing_only_unverified","scores":None}


class SoundClipTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=pathlib.Path(self.temp.name)
        self.raw=wav_bytes()
        self.wav=self.root/"adult-01.wav"
        self.wav.write_bytes(self.raw)
        self.wav.chmod(0o600)
        self.timing=self.root/"timing.json"
        self.write_timings(time_record(self.raw))

    def tearDown(self):
        self.temp.cleanup()

    def write_timings(self,record):
        self.timing.write_text(json.dumps(record,ensure_ascii=False),encoding="utf-8")
        self.timing.chmod(0o600)

    def test_extract_source_frames_without_resampling_or_fabrication(self):
        report=prepare_clips(self.wav,self.timing,self.root/"clips",_test_private_root=self.root)
        self.assertEqual(report,{"status":"created_local_syllable_clips","count":4,
             "sample_rate":16000,"phonetic_grades_computed":False,"network_requests":0})
        folder=self.root/"clips"
        self.assertEqual(stat.S_IMODE(folder.stat().st_mode),0o700)
        output=json.loads((folder/"listening-clips.json").read_text(encoding="utf-8"))
        self.assertEqual(output["purpose"],"listening_only_no_scores")
        self.assertNotIn("scores",output)
        self.assertNotIn("syllableFeedback",output)
        self.assertEqual([p["polish"] for p in output["segments"]],["Świę","to","krzy","ska"])
        with wave.open(str(self.wav),"rb") as source:
            frames=source.readframes(source.getnframes())
        for i,item in enumerate(output["segments"]):
            clip=folder/item["filename"]
            self.assertEqual(stat.S_IMODE(clip.stat().st_mode),0o600)
            with wave.open(str(clip),"rb") as wav:
                self.assertEqual(wav.getframerate(),16000)
                self.assertEqual(wav.getnframes(),6400)
                self.assertEqual(wav.readframes(6400),frames[i*6400:(i+1)*6400])
        with self.assertRaisesRegex(ValueError,"NEW output directory"):
            prepare_clips(self.wav,self.timing,folder,_test_private_root=self.root)

    def test_wrong_recording_hash_or_forged_score_fail_without_writes(self):
        target=self.root/"no-write"
        cases=[
            {**time_record(self.raw),"sourceSha256":"a"*64},
            {**time_record(self.raw),"scores":[50,50,0,100]},
            {**time_record(self.raw),"method":"whisper-transcript-v1"},
            {**time_record(self.raw),"sourceDurationSeconds":3.0},
            time_record(self.raw,[0,.4,.8,.81,1.6]),
            time_record(self.raw,[0,.4,.8,.65,1.6]),
        ]
        for record in cases:
            with self.subTest(record=record):
                self.write_timings(record)
                with self.assertRaises(ValueError):
                    prepare_clips(self.wav,self.timing,target,_test_private_root=self.root)
                self.assertFalse(target.exists())

    def test_no_symlinks_and_no_public_repo_output(self):
        target=self.root/"out"
        symlink=self.root/"alias.wav"
        symlink.symlink_to(self.wav)
        with self.assertRaisesRegex(ValueError,"non-symlink"):
            prepare_clips(symlink,self.timing,target,_test_private_root=self.root)
        outside=self.root.parent/"not-private"
        with self.assertRaisesRegex(ValueError,"[Pp]rivate"):
            prepare_clips(self.wav,self.timing,outside,_test_private_root=self.root)
        self.assertFalse(target.exists())

    def test_empty_segment_or_misaligned_word_cannot_be_scored(self):
        tampered=time_record(self.raw)
        tampered["intervals"][2]["polish"]="cz"
        with self.assertRaises(ValueError):
            _manual_intervals(tampered,self.raw,1.6)
        self.assertFalse((self.root/"clips").exists())


if __name__=="__main__":
    unittest.main()
