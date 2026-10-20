"""Static, verified audio player for owner-private Polish TTS auditions.

Audio stays in the ignored private research directory. No HTTP/TTS/family API calls.
Never render a Play control for an absent, changed, symlinked, or unreviewed file.
"""
from __future__ import annotations

import argparse
from collections import OrderedDict
import hashlib
import html
import json
from pathlib import Path
import re
import webbrowser
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "PathToPolish-Private-AI" / "voice-audition-01"
FILENAME = re.compile(r"^pl-PL-[A-Za-z]+Neural/[A-Za-z0-9_-]+\.mp3$")
VOICE_ID = re.compile(r"^pl-PL-[A-Za-z]+Neural$")
HASH = re.compile(r"^[a-f0-9]{64}$")
PLAYER = "listen.html"


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verified_clips(manifest: dict, planned_rows: list[dict], output: Path) -> list[dict]:
    """Fail closed: compare against canonical source rows and actual audio bytes."""
    if (manifest.get("schemaVersion") != 1 or
            manifest.get("status") != "synthetic_audio_unreviewed" or
            not isinstance(manifest.get("clips"), list)):
        raise ValueError("Missing or invalid locally generated private-audio manifest")
    expected = {(row["itemId"], row["voiceId"]): row for row in planned_rows}
    if len(expected) != len(planned_rows):
        raise ValueError("Duplicate planned item/voice identities")
    rows = []
    seen = set()
    for clip in manifest["clips"]:
        if not isinstance(clip, dict):
            raise ValueError("Invalid audio clip record")
        identity = (clip.get("itemId"), clip.get("voiceId"))
        expected_row = expected.get(identity)
        if identity in seen or expected_row is None:
            raise ValueError("Duplicate or unplanned voice recording")
        seen.add(identity)
        relpath = clip.get("audioPath")
        if (not isinstance(relpath, str) or not FILENAME.fullmatch(relpath) or
                clip.get("voiceId") != relpath.split("/")[0] or
                not VOICE_ID.fullmatch(clip.get("voiceId", "")) or
                relpath != expected_row["suggestedLocalFilename"] or
                clip.get("polish") != expected_row["polish"] or
                clip.get("textSha256") != expected_row["textSha256"] or
                clip.get("reviewStatus") != "needs_native_speaker_listening_review" or
                not isinstance(clip.get("audioSha256"), str) or
                not HASH.fullmatch(clip["audioSha256"])):
            raise ValueError("Unsafe, stale or mismatched voice recording")
        source = output / relpath
        if source.is_symlink() or source.parent.is_symlink() or not source.is_file():
            raise ValueError("Missing or symlinked local audio file")
        data = source.read_bytes()
        if _digest(data) != clip["audioSha256"] or len(data) != clip.get("audioBytes"):
            raise ValueError("Recorded audio checksum/size mismatch")
        if len(data) < 100 or not (data.startswith(b"ID3") or
                (data[0] == 0xFF and data[1] & 0xE0 == 0xE0)):
            raise ValueError("Audition file is not a recognizable MP3")
        rows.append(dict(clip))
    if not rows:
        raise ValueError("No generated clips to listen to")
    return rows


def render_player(clips: list[dict], plans: list[dict], voices: list[dict]) -> str:
    by_identity = {(clip["itemId"], clip["voiceId"]): clip for clip in clips}
    samples = OrderedDict()
    for plan in plans:
        if plan["itemId"] in {x["itemId"] for x in clips}:
            samples.setdefault(plan["itemId"], plan["polish"])
    headings = []
    for item_id, polish in samples.items():
        buttons = []
        for voice in voices:
            voice_id = voice["id"]
            name = html.escape(voice["label"])
            clip = by_identity.get((item_id, voice_id))
            if clip:
                href = quote(clip["audioPath"], safe="/-_.")
                buttons.append(
                    '<section class="voice"><h3>' + name + '</h3>'
                    '<audio controls preload="none" aria-label="' + name + " — " +
                    html.escape(polish, quote=True) + '" src="' + href +
                    '">Your browser does not support audio playback.</audio></section>')
            else:
                buttons.append(
                    '<section class="voice missing"><h3>' + name + '</h3>'
                    '<p>Not generated</p></section>')
        headings.append('<article class="sample"><h2 lang="pl">' +
            html.escape(polish) + '</h2><div class="voices">' +
            "".join(buttons) + '</div></article>')
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; media-src 'self' file:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Path to Polish — Voice audition</title>
<style>
:root { color-scheme: light; font: 16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; color:#202538; background:#f7f8fa; }
body { max-width:1050px; padding:32px 22px 72px; margin:auto; }
header { margin-bottom:28px; } .brand { color:#506080; letter-spacing:.08em; font-weight:750; text-transform:uppercase; font-size:.77rem; }
h1 { font-size:clamp(2rem,4vw,3rem); margin:.2em 0; letter-spacing:-.04em; } .intro { max-width:760px; color:#4f5668; }
.sample { padding:22px; border:1px solid #e1e4ed; border-radius:18px; background:white; margin:16px 0; }
.sample h2 { margin:0 0 14px; font-size:1.48rem; font-weight:680; }
.voices { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px; }
.voice { padding:12px; border-radius:13px; background:#f5f6fb; }
.voice h3 { font-size:1rem; margin:0 0 9px; font-weight:680; }
audio { display:block; width:100%; min-width:0; height:42px; }
.voice.missing { color:#7e8796; border:1px dashed #c7cdd9; background:#fafbfc; }
.voice p { font-size:.87rem; margin:12px 0; }
footer { color:#525a68; font-size:.88rem; margin-top:24px; }
@media(max-width:680px){ .voices{grid-template-columns:1fr;} body{padding:18px;} }
</style></head><body><header><div class="brand">Path to Polish / Content Lab</div>
<h1>Compare Polish voices</h1>
<p class="intro">Play the same phrase across voices, then compare clarity, rhythm and difficult Polish sounds. These are <strong>unreviewed synthetic recordings</strong>, not approved lesson audio. Missing voices are deliberately disabled.</p>
</header><main>""" + "".join(headings) + """</main>
<footer>All playable clips are local, checksum-verified files. Listening here does not call Azure or upload any voice data. Do not use these test recordings as phonetic ground truth.</footer>
</body></html>
"""


def write_player(output: Path, plans: list[dict], voices: list[dict]) -> Path:
    manifest_path = output / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("No private voice-audition manifest found. Only a preview exists.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    clips = verified_clips(manifest, plans, output)
    page = output / PLAYER
    if page.exists() or page.is_symlink():
        raise FileExistsError("Existing listening page will not be overwritten")
    page.write_text(render_player(clips, plans, voices), encoding="utf-8")
    return page


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--open", action="store_true", help="Open local listening HTML in default browser")
    args = parser.parse_args(argv)
    # Import only when running; tests can supply trusted fixture rows without API use.
    from azure_voice_audition import plan_from_generated_catalog, select_audition_rows
    plan = plan_from_generated_catalog()
    rows = select_audition_rows(plan, 24)
    page = OUTPUT / PLAYER
    if page.exists() and not page.is_symlink():
        # Always verify against the source hashes, not just the old HTML.
        manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
        verified_clips(manifest, rows, OUTPUT)
    else:
        page = write_player(OUTPUT, rows, plan["voices"])
    print("Private voice audition listening page: " + str(page))
    if args.open:
        webbrowser.open(page.as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
