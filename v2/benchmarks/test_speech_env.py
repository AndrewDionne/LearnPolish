"""Fully offline durable Speech config tests: no cloud calls or real credentials."""
from __future__ import annotations

import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from speech_env import (
    REGION, FILENAME, PRIVATE_FOLDER, read_private_config,
    save_private_config, speech_credentials, main,
)


class DurableSpeechConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.folder=self.root / PRIVATE_FOLDER
        self.path=self.folder / FILENAME
        self.fake_key="PRIVATE-TEST-F0-KEY-NEVER-EXPOSE"
        self.stale={"AZURE_SPEECH_KEY":"OLD-SHELL-WRONG-KEY",
                    "AZURE_SPEECH_REGION":"westeurope"}

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_file_fallback_preserves_legacy_shell_behavior(self):
        self.assertIsNone(read_private_config(self.root))
        self.assertEqual(speech_credentials(root=self.root,environ=self.stale),
                         ("OLD-SHELL-WRONG-KEY","westeurope"))
        self.assertFalse(self.folder.exists())

    def test_install_is_owner_only_and_has_precedence_over_stale_shell(self):
        save_private_config(self.fake_key,REGION,root=self.root)
        self.assertEqual(self.folder.stat().st_mode & 0o777,0o700)
        self.assertEqual(self.path.stat().st_mode & 0o777,0o600)
        self.assertEqual(read_private_config(self.root),(self.fake_key,REGION))
        self.assertEqual(speech_credentials(root=self.root,environ=self.stale),
                         (self.fake_key,REGION))
        self.assertNotIn("OLD-SHELL",self.path.read_text())
        self.assertEqual(set(line.split("=",1)[0] for line in self.path.read_text().splitlines()),
                         {"AZURE_SPEECH_KEY","AZURE_SPEECH_REGION"})

    def test_no_silent_overwrite_and_explicit_atomic_rotation(self):
        save_private_config(self.fake_key,REGION,root=self.root)
        original=self.path.read_bytes()
        with self.assertRaisesRegex(ValueError,"already exists"):
            save_private_config("NEW-SECRET",REGION,root=self.root)
        self.assertEqual(self.path.read_bytes(),original)
        save_private_config("NEW-SECRET",REGION,root=self.root,replace=True)
        self.assertEqual(read_private_config(self.root),("NEW-SECRET",REGION))
        self.assertEqual(self.path.stat().st_mode & 0o777,0o600)
        self.assertEqual(sorted(x.name for x in self.folder.iterdir()),[FILENAME])

    def test_invalid_values_do_not_create_file(self):
        for key,region in (("",REGION),("…placeholder",REGION),
                           (" PRIVATE ",REGION),("key\nEVIL=COMMAND",REGION),
                           ("[REDACTED]",REGION),("VALID","westeurope")):
            with self.subTest(kind="invalid"):
                with self.assertRaises(ValueError):
                    save_private_config(key,region,root=self.root)
        self.assertFalse(self.path.exists())

    def test_reject_insecure_directory_and_file_permissions_without_shell_fallback(self):
        save_private_config(self.fake_key,REGION,root=self.root)
        self.path.chmod(0o644)
        with self.assertRaisesRegex(ValueError,"chmod-600"):
            speech_credentials(root=self.root,environ=self.stale)
        self.path.chmod(0o600)
        self.folder.chmod(0o755)
        with self.assertRaisesRegex(ValueError,"chmod 700"):
            speech_credentials(root=self.root,environ=self.stale)
        self.folder.chmod(0o700)
        self.assertEqual(read_private_config(self.root),(self.fake_key,REGION))

    def test_refuses_symlink_file_and_parent_including_outside_repo(self):
        other=self.root/"target"
        other.write_text("AZURE_SPEECH_KEY=SOMETHING\nAZURE_SPEECH_REGION=germanywestcentral\n")
        self.folder.mkdir(mode=0o700)
        self.path.symlink_to(other)
        with self.assertRaisesRegex(ValueError,"symbolic link"):
            read_private_config(self.root)
        with self.assertRaises(ValueError):
            save_private_config(self.fake_key,REGION,root=self.root)
        self.path.unlink()
        self.folder.rmdir()
        self.folder.symlink_to(self.root)
        with self.assertRaises(ValueError):
            read_private_config(self.root) if self.path.is_symlink() else save_private_config(
                self.fake_key,REGION,root=self.root)

    def test_not_a_shell_script_or_general_dotenv_interpreter(self):
        save_private_config(self.fake_key,REGION,root=self.root)
        for content in (
            "AZURE_SPEECH_KEY=good\nAZURE_SPEECH_REGION=germanywestcentral\nEVIL=$(touch /tmp/invalid)\n",
            "export AZURE_SPEECH_KEY=good\nAZURE_SPEECH_REGION=germanywestcentral\n",
            "AZURE_SPEECH_KEY=good\nAZURE_SPEECH_KEY=another\nAZURE_SPEECH_REGION=germanywestcentral\n",
            "AZURE_SPEECH_KEY=good\nAZURE_SPEECH_REGION=westeurope\n",
        ):
            self.path.write_text(content)
            with self.assertRaises(ValueError):
                read_private_config(self.root)
        # Values are data; no sourcing/evaluation/variable expansion occurs.
        self.path.write_text("AZURE_SPEECH_KEY=literal-$(false)\nAZURE_SPEECH_REGION=germanywestcentral\n")
        self.assertEqual(read_private_config(self.root)[0],"literal-$(false)")

    def test_setup_from_existing_current_shell_is_nonnetwork_and_key_never_logged(self):
        out=io.StringIO()
        with patch("speech_env._root",return_value=self.root):
            with patch.dict(os.environ,{"AZURE_SPEECH_KEY":self.fake_key,
                                        "AZURE_SPEECH_REGION":REGION},clear=True):
                with patch.object(sys,"argv",["speech_env.py","--save-current"]):
                    with contextlib.redirect_stdout(out):
                        self.assertEqual(main(),0)
                with patch.object(sys,"argv",["speech_env.py","--status"]):
                    with contextlib.redirect_stdout(out):
                        self.assertEqual(main(),0)
        self.assertNotIn(self.fake_key,out.getvalue())
        self.assertIn("owner-only",out.getvalue())
        self.assertIn("private file installed and valid",out.getvalue())

    def test_prompt_setup_does_not_echo_and_requires_explicit_replace(self):
        out=io.StringIO()
        with patch("speech_env._root",return_value=self.root):
            with patch("speech_env.getpass.getpass",return_value=self.fake_key) as prompt:
                with patch.object(sys,"argv",["speech_env.py","--setup"]):
                    with contextlib.redirect_stdout(out):
                        self.assertEqual(main(),0)
            self.assertEqual(prompt.call_count,1)
            with patch.object(sys,"argv",["speech_env.py","--save-current"]):
                with patch.dict(os.environ,{"AZURE_SPEECH_KEY":"OLD",
                                           "AZURE_SPEECH_REGION":REGION},clear=True):
                    with contextlib.redirect_stderr(io.StringIO()):
                        with self.assertRaises(SystemExit) as cm:
                            main()
            self.assertEqual(cm.exception.code,2)
        self.assertEqual(read_private_config(self.root)[0],self.fake_key)
        self.assertNotIn(self.fake_key,out.getvalue())


if __name__=="__main__":
    unittest.main()
