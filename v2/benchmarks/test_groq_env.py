"""Private Groq API-key persistence: all tests offline and with dummy strings."""
from __future__ import annotations

import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from groq_env import FILENAME, groq_key, read_private_groq, save_private_groq, main
from speech_env import PRIVATE_FOLDER, REGION, read_private_config, save_private_config


class GroqEnvTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.folder=self.root / PRIVATE_FOLDER
        self.path=self.folder / FILENAME
        self.key="MOCK-GROQ-NO-REAL-SECRET"

    def tearDown(self):
        self.temp.cleanup()

    def test_no_file_uses_environment_without_modification(self):
        env={"GROQ_API_KEY":"STALE-SHELL"}
        self.assertEqual(groq_key(root=self.root,environ=env),"STALE-SHELL")
        self.assertIsNone(read_private_groq(self.root))
        self.assertFalse(self.folder.exists())

    def test_save_once_is_owner_only_and_wins_over_stale_shell(self):
        save_private_groq(self.key,root=self.root)
        self.assertEqual(self.folder.stat().st_mode & 0o777,0o700)
        self.assertEqual(self.path.stat().st_mode & 0o777,0o600)
        self.assertEqual(read_private_groq(self.root),self.key)
        self.assertEqual(groq_key(root=self.root,environ={"GROQ_API_KEY":"OLD"}),self.key)
        self.assertEqual(self.path.read_text(),f"GROQ_API_KEY={self.key}\n")

    def test_does_not_damage_existing_azure_configuration(self):
        save_private_config("MOCK-AZURE-KEY",REGION,root=self.root)
        before=(self.folder/".env.azure-speech").read_bytes()
        save_private_groq(self.key,root=self.root)
        self.assertEqual((self.folder/".env.azure-speech").read_bytes(),before)
        self.assertEqual(read_private_config(self.root),("MOCK-AZURE-KEY",REGION))
        self.assertEqual(read_private_groq(self.root),self.key)

    def test_existing_file_not_overwritten_and_rotation_only_when_explicit(self):
        save_private_groq(self.key,root=self.root)
        with self.assertRaisesRegex(ValueError,"already exists"):
            save_private_groq("NEW-KEY",root=self.root)
        self.assertEqual(read_private_groq(self.root),self.key)
        save_private_groq("NEW-KEY",root=self.root,replace=True)
        self.assertEqual(read_private_groq(self.root),"NEW-KEY")
        self.assertEqual(self.path.stat().st_mode & 0o777,0o600)
        self.assertEqual([p.name for p in self.folder.iterdir()],[FILENAME])
        with self.assertRaisesRegex(ValueError,"No installed"):
            save_private_groq("NEW",root=self.root/"elsewhere",replace=True)

    def test_insecure_directory_file_and_symlinks_fail_closed(self):
        save_private_groq(self.key,root=self.root)
        self.path.chmod(0o644)
        with self.assertRaises(ValueError):
            groq_key(root=self.root,environ={"GROQ_API_KEY":"FALLBACK"})
        self.path.chmod(0o600)
        self.folder.chmod(0o755)
        with self.assertRaises(ValueError):
            read_private_groq(self.root)
        self.folder.chmod(0o700)
        target=self.root/"target"
        target.write_text(f"GROQ_API_KEY={self.key}\n")
        self.path.unlink()
        self.path.symlink_to(target)
        with self.assertRaises(ValueError):
            read_private_groq(self.root)
        with self.assertRaises(ValueError):
            save_private_groq(self.key,root=self.root)

    def test_rejects_extra_keys_executable_like_file_and_bad_values(self):
        save_private_groq(self.key,root=self.root)
        bad=[
            "export GROQ_API_KEY=bad\n",
            "GROQ_API_KEY=good\nOTHER_KEY=evil\n",
            "GROQ_API_KEY=good\nGROQ_API_KEY=second\n",
            "GROQ_API_KEY=\n",
            "GROQ_API_KEY=\u2026\n",
        ]
        for value in bad:
            self.path.write_text(value)
            with self.assertRaises(ValueError):
                read_private_groq(self.root)
        for value in ("", "...", "…notvalid", " BAD", "BAD\nKEY", "[REDACTED]", "key'quoted"):
            with self.assertRaises(ValueError):
                save_private_groq(value,root=self.root,replace=True)

    def test_local_status_save_current_never_echoes_api_key(self):
        output=io.StringIO()
        with patch("groq_env._root",return_value=self.root):
            with patch.dict(os.environ,{"GROQ_API_KEY":self.key},clear=True):
                with patch.object(sys,"argv",["groq_env.py","--save-current"]):
                    with contextlib.redirect_stdout(output):
                        self.assertEqual(main(),0)
                with patch.object(sys,"argv",["groq_env.py","--status"]):
                    with contextlib.redirect_stdout(output):
                        self.assertEqual(main(),0)
        self.assertIn("private key saved successfully",output.getvalue())
        self.assertIn("private key installed",output.getvalue())
        self.assertNotIn(self.key,output.getvalue())

    def test_hidden_setup_and_duplicate_avoid_accidental_override(self):
        output=io.StringIO()
        with patch("groq_env._root",return_value=self.root):
            with patch("groq_env.getpass.getpass",return_value=self.key) as prompt:
                with patch.object(sys,"argv",["groq_env.py","--setup"]):
                    with contextlib.redirect_stdout(output):
                        self.assertEqual(main(),0)
            self.assertEqual(prompt.call_count,1)
            with patch.object(sys,"argv",["groq_env.py","--save-current"]):
                with patch.dict(os.environ,{"GROQ_API_KEY":"STALE"},clear=True):
                    with contextlib.redirect_stderr(io.StringIO()):
                        with self.assertRaises(SystemExit) as caught:
                            main()
            self.assertEqual(caught.exception.code,2)
        self.assertEqual(read_private_groq(self.root),self.key)
        self.assertNotIn(self.key,output.getvalue())


if __name__=="__main__":
    unittest.main()
