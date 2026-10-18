"""Strict no-provider public Polish audio fixtures: metadata and downloader safeguards."""
import unittest
from unittest.mock import patch
from public_polish_audio import SOURCES, MAX_SOURCE_BYTES, validate_ogg, fetch_original


class PublicPolishAudioTests(unittest.TestCase):
    def test_public_sources_are_real_attributed_greetings_not_child_voices(self):
        self.assertEqual([r["text"] for r in SOURCES],["Dzień dobry","Dobry wieczór"])
        self.assertEqual([r["author"] for r in SOURCES],["Julo","SirPL0"])
        self.assertTrue(all(r["license"]=="Public domain" for r in SOURCES))
        self.assertTrue(all(r["url"].startswith("https://upload.wikimedia.org/wikipedia/commons/")
                            for r in SOURCES))

    def test_rejects_html_silence_wrong_format_and_oversize_without_any_inference(self):
        for value in [b"",b"<html>" * 1000, b"RIFF" + b"x" * 4096,
                      b"OggS" + b"a" * (MAX_SOURCE_BYTES + 1)]:
            with self.assertRaises(ValueError):
                validate_ogg(value)
        self.assertEqual(len(validate_ogg(b"OggS" + b"a" * 2048)),64)

    def test_no_other_domain_can_supply_original_sound(self):
        for host in ["http://upload.wikimedia.org/evil.ogg",
                     "https://not-wikimedia.example/test.ogg",
                     "https://upload.wikimedia.org.evil.example/a.ogg"]:
            with self.assertRaises(ValueError):
                fetch_original(host)

    def test_no_remote_request_in_validation(self):
        with patch("public_polish_audio.urlopen") as calls:
            validate_ogg(b"OggS"+b"p"*2048)
            calls.assert_not_called()


if __name__ == "__main__":
    unittest.main()
