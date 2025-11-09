# app/tts.py
import os, requests
from pathlib import Path
from gtts import gTTS  # fallback

AZ_VOICE_DEFAULT = os.getenv("TTS_VOICE", "pl-PL-MarekNeural")
AZ_FORMAT = os.getenv("TTS_FORMAT", "audio-16khz-128kbitrate-mono-mp3")

def _azure_env():
    key = (
        os.getenv("AZURE_SPEECH_KEY")
        or os.getenv("AZURE_TTS_KEY")
        or os.getenv("SPEECH_KEY")
        or os.getenv("AZURE_COG_KEY")
        or os.getenv("COGNITIVE_SERVICES_KEY")
    )
    region = (
        os.getenv("AZURE_SPEECH_REGION")
        or os.getenv("SPEECH_REGION")
        or os.getenv("AZURE_REGION")
        or os.getenv("REGION")
    )
    endpoint = os.getenv("AZURE_SPEECH_ENDPOINT")  # optional
    return key, region, endpoint

def _azure_tts(text: str, out_path: Path, voice: str) -> None:
    key, region, endpoint = _azure_env()
    if not (key and region):
        raise RuntimeError("azure_tts_misconfigured")

    url = (endpoint.rstrip("/") + "/cognitiveservices/v1") if endpoint else f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
    ssml = f"""<speak version='1.0' xml:lang='pl-PL'>
  <voice name='{voice}'>{text}</voice>
</speak>"""
    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": AZ_FORMAT,
        "User-Agent": "PathToPolish/1.0",
    }
    r = requests.post(url, headers=headers, data=ssml.encode("utf-8"), timeout=20)
    r.raise_for_status()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(r.content)

def synthesize_tts(text: str, out_path: str | Path, lang: str = "pl", voice: str | None = None) -> None:
    """
    If TTS_PROVIDER=azure, use Azure neural voice; else use gTTS.
    """
    provider = os.getenv("TTS_PROVIDER", "gtts").lower()
    p = Path(out_path)
    if provider == "azure":
        _azure_tts(text, p, voice or AZ_VOICE_DEFAULT)
    else:
        # gTTS fallback
        tts = gTTS(text=text, lang=lang, slow=False)
        p.parent.mkdir(parents=True, exist_ok=True)
        tts.save(str(p))
