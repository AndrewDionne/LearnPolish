"""Repository-local ignored research space and tracked-file safety guards."""
import pathlib
import tempfile
import unittest

from research_paths import check_research_location


class ResearchPathTests(unittest.TestCase):
    def test_research_files_permitted_under_ignored_repo_temp(self):
        with tempfile.TemporaryDirectory() as base:
            root = pathlib.Path(base) / "path-to-polish"
            root.mkdir()
            for path in (root / "temp" / "commons-native-01",
                         root / "temp" / "commons-native-01" / "manifest.json",
                         root / "temp" / "groq-research.jsonl"):
                check_research_location(path, repository=root)

    def test_owner_fixed_folder_is_allowed_without_moving_files(self):
        with tempfile.TemporaryDirectory() as base:
            root = pathlib.Path(base) / "path-to-polish"
            root.mkdir()
            original = root / "PathToPolish-Private-AI"
            original.mkdir()
            (original / "Pl-czapka.ogg").write_bytes(b"OggS local file")
            for path in (original / "Pl-czapka.ogg",
                         original / "Pl-ciasto.ogg",
                         original / "commons-native-01" / "manifest.json",
                         original / "commons-native-01" / "groq-transcripts.jsonl"):
                check_research_location(path, repository=root)
            self.assertTrue((original / "Pl-czapka.ogg").exists())

    def test_rejects_symlink_escape_from_owner_folder(self):
        with tempfile.TemporaryDirectory() as base:
            root = pathlib.Path(base) / "path-to-polish"
            root.mkdir()
            (root / "assets").mkdir()
            owner = root / "PathToPolish-Private-AI"
            owner.mkdir()
            (owner / "elsewhere").symlink_to(root / "assets", target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "PathToPolish-Private-AI"):
                check_research_location(owner / "elsewhere" / "private.wav", repository=root)

    def test_rejects_tracked_app_assets_and_git_root(self):
        with tempfile.TemporaryDirectory() as base:
            root = pathlib.Path(base) / "path-to-polish"
            root.mkdir()
            for path in (root, root / "assets" / "recording.wav",
                         root / "v2" / "benchmarks" / "results.jsonl",
                         root / "docs" / "public" / "audio.ogg"):
                with self.assertRaisesRegex(ValueError, "PathToPolish-Private-AI"):
                    check_research_location(path, repository=root)

    def test_rejects_symlinked_temp_to_external_directory(self):
        with tempfile.TemporaryDirectory() as base:
            root = pathlib.Path(base) / "path-to-polish"
            root.mkdir()
            external = pathlib.Path(base) / "elsewhere"
            external.mkdir()
            (root / "temp").symlink_to(external, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "PathToPolish-Private-AI"):
                check_research_location(root / "temp" / "manifest.json",
                                        repository=root)

    def test_external_private_folders_remain_supported(self):
        with tempfile.TemporaryDirectory() as base:
            root = pathlib.Path(base) / "path-to-polish"
            root.mkdir()
            outside = pathlib.Path(base) / "private" / "manifest.json"
            check_research_location(outside, repository=root)


if __name__ == "__main__":
    unittest.main()
