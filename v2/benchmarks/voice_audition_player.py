"""Static, verified audio player for owner-private Polish TTS auditions.

Audio stays in the ignored private research directory. No HTTP/TTS/family API calls.
Never render a Play control for an absent, changed, symlinked, or unreviewed file.
"""
from __future__ import annotations

import argparse
import base64
from collections import OrderedDict
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
import subprocess
import webbrowser
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "PathToPolish-Private-AI" / "voice-audition-01"
FILENAME = re.compile(r"^pl-PL-[A-Za-z]+Neural/[A-Za-z0-9_-]+\.mp3$")
VOICE_ID = re.compile(r"^pl-PL-[A-Za-z]+Neural$")
HASH = re.compile(r"^[a-f0-9]{64}$")
PLAYER = "listen.html"

# Static, no-network, hash-pinned local rate control. Browser native playback
# menus may vary, so ratechange also enforces the bounded app learning range.
RATE_SCRIPT = """(() => {
  const allowed = [0.75, 0.85, 1];
  const audios = Array.from(document.querySelectorAll('audio[data-audition]'));
  const buttons = Array.from(document.querySelectorAll('button[data-rate]'));
  let selected = 1;
  function select(speed) {
    if (!allowed.includes(speed)) return;
    selected = speed;
    for (const audio of audios) {
      audio.defaultPlaybackRate = speed;
      audio.playbackRate = speed;
    }
    for (const button of buttons) {
      const pressed = Number(button.dataset.rate) === speed;
      button.setAttribute('aria-pressed', String(pressed));
    }
  }
  for (const audio of audios) {
    audio.addEventListener('ratechange', () => {
      if (!allowed.includes(audio.playbackRate)) {
        audio.playbackRate = selected;
      }
    });
  }
  for (const button of buttons) {
    button.addEventListener('click', () => select(Number(button.dataset.rate)));
  }
  select(1);
})();"""



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


def local_audio_probe(file: Path) -> dict:
    """No provider calls. Ask an installed native decoder for MP3 duration."""
    if shutil.which("afinfo"):
        try:
            proc = subprocess.run(["afinfo", str(file)], capture_output=True,
                                  text=True, timeout=15, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return {"tool": "afinfo", "result": "probe_failed", "duration_seconds": None}
        if proc.returncode != 0:
            return {"tool": "afinfo", "result": "not_decodable", "duration_seconds": None}
        found = re.search(r"(?:estimated\s+)?duration:\s*([0-9]+(?:\.[0-9]+)?)\s*sec",
                          proc.stdout, flags=re.IGNORECASE)
        if found:
            duration = float(found.group(1))
            return {"tool": "afinfo", "result": "unusually_short" if duration < 0.3 else "duration_detected",
                    "duration_seconds": duration}
        return {"tool": "afinfo", "result": "duration_unconfirmed", "duration_seconds": None}
    if shutil.which("ffprobe"):
        try:
            proc = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_name",
                 "-of", "json", str(file)],
                capture_output=True, text=True, timeout=15, check=False)
            if proc.returncode:
                return {"tool": "ffprobe", "result": "not_decodable", "duration_seconds": None}
            details = json.loads(proc.stdout)
            codecs = {stream.get("codec_name") for stream in details.get("streams", [])}
            if "mp3" not in codecs:
                return {"tool": "ffprobe", "result": "not_mp3_codec", "duration_seconds": None}
            duration = float(details.get("format", {}).get("duration", 0))
            return {"tool": "ffprobe",
                    "result": "unusually_short" if duration < 0.3 else "duration_detected",
                    "duration_seconds": duration}
        except (OSError, subprocess.TimeoutExpired, ValueError, TypeError, KeyError):
            return {"tool": "ffprobe", "result": "probe_failed", "duration_seconds": None}
    return {"tool": None, "result": "no_local_decoder_available", "duration_seconds": None}


def playback_diagnostics(clips: list[dict], output: Path) -> dict:
    return {
        "status": "LOCAL_AUDIO_INSPECTION_ONLY",
        "provider_requests_made": 0,
        "clips": [
            {"voice": clip["voiceId"], "polish": clip["polish"],
             "bytes": clip["audioBytes"], **local_audio_probe(output / clip["audioPath"])}
            for clip in clips
        ],
        "interpretation": "Checks decoder metadata, not human listening. If decoding fails the MP3 is not verified playable; if it succeeds but HTML playback stops, compare with afplay to isolate browser behavior.",
    }


def render_player(clips: list[dict], plans: list[dict], voices: list[dict]) -> str:
    script_hash = base64.b64encode(hashlib.sha256(RATE_SCRIPT.encode("utf-8")).digest()).decode("ascii")
    by_identity = {(clip["itemId"], clip["voiceId"]): clip for clip in clips}
    # An ungenerated third-choice voice should not occupy every pilot row.
    # In partial auditions, show only voices with at least one real verified clip.
    active_voices = [voice for voice in voices
                     if any(clip["voiceId"] == voice["id"] for clip in clips)]
    samples = OrderedDict()
    for plan in plans:
        if plan["itemId"] in {x["itemId"] for x in clips}:
            samples.setdefault(plan["itemId"], plan["polish"])
    headings = []
    for item_id, polish in samples.items():
        buttons = []
        for voice in active_voices:
            voice_id = voice["id"]
            name = html.escape(voice["label"])
            clip = by_identity.get((item_id, voice_id))
            if clip:
                href = quote(clip["audioPath"], safe="/-_.")
                buttons.append(
                    '<section class="voice"><h3>' + name + '</h3>'
                    '<audio controls controlslist="noplaybackrate" data-audition="true" preload="metadata" aria-label="' + name + " — " +
                    html.escape(polish, quote=True) + '" src="' + href +
                    '">Your browser does not support audio playback.</audio>' +
                    '<a class="direct-audio" href="' + href + '">Open MP3 directly</a></section>')
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
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; media-src 'self' file:; style-src 'unsafe-inline'; script-src 'sha256-""" + script_hash + """'; base-uri 'none'; form-action 'none'">
<title>Path to Polish — Voice audition</title>
<style>
:root { color-scheme: light; font: 16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; color:#202538; background:#f7f8fa; }
body { max-width:1050px; padding:32px 22px 72px; margin:auto; }
header { margin-bottom:28px; } .brand { color:#506080; letter-spacing:.08em; font-weight:750; text-transform:uppercase; font-size:.77rem; }
h1 { font-size:clamp(2rem,4vw,3rem); margin:.2em 0; letter-spacing:-.04em; } .intro { max-width:760px; color:#4f5668; }
.sample { padding:22px; border:1px solid #e1e4ed; border-radius:18px; background:white; margin:16px 0; }
.sample h2 { margin:0 0 14px; font-size:1.48rem; font-weight:680; }
.voices { display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,260px),1fr)); gap:14px; }
.voice { padding:12px; border-radius:13px; background:#f5f6fb; }
.voice h3 { font-size:1rem; margin:0 0 9px; font-weight:680; }
audio { display:block; width:100%; min-width:0; height:42px; }
.voice.missing { color:#7e8796; border:1px dashed #c7cdd9; background:#fafbfc; }
.voice p { font-size:.87rem; margin:12px 0; }
.speed-picker { display:flex; flex-wrap:wrap; align-items:center; gap:9px; margin:17px 0; padding:0; border:0; }
.speed-picker legend { color:#4f5668; font-size:.89rem; font-weight:650; margin-bottom:8px; }
.speed-picker button { font:inherit; cursor:pointer; min-width:63px; padding:8px 13px; background:#f5f6fb; color:#202538; border:1px solid #d8deeb; border-radius:9px; }
.speed-picker button[aria-pressed="true"] { background:#202538; border-color:#202538; color:white; }
.speed-picker button:focus-visible { outline:3px solid #739bdd; outline-offset:3px; }
.direct-audio { display:inline-block; margin-top:10px; font-size:.82rem; color:#344e85; }
footer { color:#525a68; font-size:.88rem; margin-top:24px; }
@media(max-width:680px){ .voices{grid-template-columns:1fr;} body{padding:18px;} }
</style></head><body><header><div class="brand">Path to Polish / Content Lab</div>
<h1>Compare Polish voices</h1>
<p class="intro">Compare the same Polish phrase spoken by Marek and Agnieszka (and other voices only if recordings exist). Pay particular attention to <strong>natural word endings, final consonants and cadence</strong>. These are <strong>unreviewed synthetic recordings</strong>, not approved lesson audio.</p>
</header>
<fieldset class="speed-picker"><legend>Playback speed</legend>
<button type="button" data-rate="0.75" aria-pressed="false">0.75×</button>
<button type="button" data-rate="0.85" aria-pressed="false">0.85×</button>
<button type="button" data-rate="1" aria-pressed="true">1×</button>
</fieldset><main>""" + "".join(headings) + """</main>
<footer>Audio files are source/hash verified, but may still be unplayable due to encoding or browser restrictions. Use the Open MP3 directly link or the offline --diagnose CLI to distinguish these cases. No audio is uploaded and no provider is called when listening.</footer>
<script>""" + RATE_SCRIPT + """</script>
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


def refresh_player(output: Path, clips: list[dict], plans: list[dict], voices: list[dict]) -> Path:
    """Update only HTML, never private MP3s or their manifest."""
    page = output / PLAYER
    if page.is_symlink():
        raise ValueError("Refusing symlinked private listening page")
    temporary = output / (PLAYER + ".tmp")
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write(render_player(clips, plans, voices))
    temporary.replace(page)
    return page


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--open", action="store_true", help="Open local listening HTML in default browser")
    parser.add_argument("--diagnose", action="store_true",
                        help="Verify saved MP3s and inspect local decoder duration; no provider calls")
    args = parser.parse_args(argv)
    # Import only when running; tests can supply trusted fixture rows without API use.
    from azure_voice_audition import plan_from_generated_catalog, select_audition_rows
    plan = plan_from_generated_catalog()
    rows = select_audition_rows(plan, 24)
    manifest_path = OUTPUT / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("Missing private source-audition manifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    clips = verified_clips(manifest, rows, OUTPUT)
    if args.diagnose:
        print(json.dumps(playback_diagnostics(clips, OUTPUT), ensure_ascii=False, indent=2))
        return 0
    page = refresh_player(OUTPUT, clips, rows, plan["voices"])
    print("Private voice audition listening page: " + str(page))
    if args.open:
        webbrowser.open(page.as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
