"""Opt-in experimental Azure + one Groq Whisper transcription for the SAME take.

Never grade syllables: colours are categorised transcript-derived differences.
Never save or return the transcript, voice, phonemes, provider details, or keys.
The arithmetic blend is deliberately uncalibrated and cannot award XP.
"""
from __future__ import annotations

import json
import math
import re
import secrets
import urllib.request

GROQ_ENDPOINT = "https://api.groq.com/openai/v1/audio/transcriptions"
WHISPER_MODEL = "whisper-large-v3-turbo"
HINT_CLASSES = ("close", "review", "focus", "uncertain")
VOWELS = set("aąeęioóuy")
DIGRAPHS = ("dź", "dż", "dzi", "dz", "cz", "sz", "rz", "ch", "ci", "si", "zi", "ni")
NORMALIZE = {"w":"v","v":"v","rz":"ż","ż":"ż","ó":"u",
             "ch":"h","ci":"ć","si":"ś","zi":"ź","ni":"ń","dzi":"dź"}
CLOSE_CONTRASTS = {
    frozenset(("ś","s")):.55,
    frozenset(("ć","cz")):.55,
    frozenset(("ź","ż")):.55,
    frozenset(("ż","sz")):.5,
    frozenset(("ę","e")):.45,
    frozenset(("ą","o")):.45,
    frozenset(("i","y")):.6,
    frozenset(("j","i")):.4,
    frozenset(("cz","sz")):.55,
}


def sound_units(value: str) -> list[str]:
    """Lightweight orthographic sound proxy, NOT a phoneme transcript."""
    if not isinstance(value, str) or not 1 <= len(value) <= 300:
        raise ValueError("Invalid short Polish text")
    # Spacing and punctuation are not sounds, but NEVER alter authored text.
    cleaned = re.sub(r"[\s.,!?;:()\-’'„”“\"…]", "", value.casefold())
    if not cleaned or not re.fullmatch(r"[a-ząćęłńóśźż]+", cleaned):
        raise ValueError("Text cannot be scored as simple Polish sound units")
    units = []
    pos = 0
    while pos < len(cleaned):
        group = next((g for g in DIGRAPHS if cleaned.startswith(g, pos)), cleaned[pos])
        sound = NORMALIZE.get(group, group)
        if group == "rz" and units and units[-1] in ("k", "p", "t", "f", "h"):
            sound = "sz"
        units.append(sound)
        pos += len(group)
    return units


def _edit_cost(expected: str, heard: str) -> float:
    return 0 if expected == heard else CLOSE_CONTRASTS.get(frozenset((expected, heard)), 1.0)


def transcript_hints(reference: str, segments: list[str], transcript: str) -> dict:
    """Weighted edit alignment with an internal score and colour-only public hints."""
    if not isinstance(segments, list) or not 1 <= len(segments) <= 32 or (
        not all(isinstance(s, str) and s for s in segments) or
        "".join(segments) != reference
    ):
        raise ValueError("Invalid exact reference segmentation")
    grouped = [sound_units(s) for s in segments]
    expected = [(sound, i) for i, group in enumerate(grouped) for sound in group]
    observed = sound_units(transcript)
    if not expected or not observed or len(expected) > 300 or len(observed) > 300:
        raise ValueError("Empty/unbounded provider evidence")
    n, m = len(expected), len(observed)
    dp = [[0.0]*(m+1) for _ in range(n+1)]
    actions = [[""]*(m+1) for _ in range(n+1)]
    for i in range(1,n+1):
        dp[i][0], actions[i][0] = float(i), "delete"
    for j in range(1,m+1):
        dp[0][j], actions[0][j] = float(j), "insert"
    for i in range(1,n+1):
        for j in range(1,m+1):
            cost = _edit_cost(expected[i-1][0], observed[j-1])
            choice = min(
                (dp[i-1][j-1]+cost, 0, "match" if cost==0 else "substitute"),
                (dp[i-1][j]+1, 1, "delete"),
                (dp[i][j-1]+1, 2, "insert"),
            )
            dp[i][j], actions[i][j] = choice[0], choice[2]
    costs = [0.0]*len(segments)
    i,j=n,m
    while i or j:
        op = actions[i][j]
        if op in ("match","substitute"):
            costs[expected[i-1][1]] += _edit_cost(expected[i-1][0],observed[j-1])
            i-=1
            j-=1
        elif op == "delete":
            costs[expected[i-1][1]] += 1
            i-=1
        elif op == "insert":
            costs[expected[i-1][1] if i else expected[0][1]] += 1
            j-=1
        else:
            raise ValueError("Incomplete provider alignment")
    hints = []
    for segment, units, cost in zip(segments, grouped, costs):
        similarity = max(0, 100*(1-cost/len(units)))
        hint = "close" if similarity>=80 else "review" if similarity>=50 else "focus"
        hints.append({"polish":segment,"hint":hint})
    return {
        "transcription_similarity":round(max(0,100*(1-sum(costs)/n))),
        "segments":hints
    }


def blend_assessment(azure: dict, reference: str, segments: list[str], transcript: str) -> dict:
    """A result exists only when BOTH providers return usable evidence."""
    if azure.get("status") != "ok" or not isinstance(azure.get("scores"), dict):
        return {"status":"inconclusive","reason":"provider_inconclusive"}
    accuracy=azure["scores"].get("accuracy")
    if type(accuracy) not in (int,float) or not math.isfinite(accuracy) or not 0<=accuracy<=100:
        return {"status":"inconclusive","reason":"provider_inconclusive"}
    try:
        proxy=transcript_hints(reference,segments,transcript)
    except (TypeError,ValueError,OverflowError):
        return {"status":"inconclusive","reason":"provider_inconclusive"}
    return {
        "status":"ok",
        "engine":"azure-whisper-blend-v1",
        "calibration":"experimental-uncalibrated",
        "combined":round((accuracy+proxy["transcription_similarity"])/2),
        "colourHints":{"reference":reference,"method":"whisper-transcript-proxy-v1",
                       "segments":proxy["segments"]},
    }


def groq_whisper_transcribe(wav: bytes, key: str) -> str:
    """One bounded HTTPS request, no retries or private provider error exposure."""
    if (not isinstance(wav, bytes) or not 44<=len(wav)<=360000 or
        not isinstance(key,str) or not key or not key.isascii() or not key.isprintable()):
        raise ValueError("Speech provider is not configured")
    boundary = ("ptpspeech"+secrets.token_hex(16)).encode("ascii")
    pieces = []
    for field, value in (("model",WHISPER_MODEL),("language","pl"),
                         ("response_format","json"),("temperature","0")):
        pieces.append(b"--"+boundary+b'\r\nContent-Disposition: form-data; name="'+
                      field.encode("ascii")+b'"\r\n\r\n'+value.encode("ascii")+b"\r\n")
    pieces.append(b"--"+boundary+b'\r\nContent-Disposition: form-data; name="file"; filename="take.wav"\r\nContent-Type: audio/wav\r\n\r\n'+wav+b"\r\n")
    pieces.append(b"--"+boundary+b"--\r\n")
    request=urllib.request.Request(
        GROQ_ENDPOINT,method="POST",data=b"".join(pieces),
        headers={"Authorization":"Bearer "+key,"Content-Type":
                 "multipart/form-data; boundary="+boundary.decode("ascii")}
    )
    # The caller contains all exceptions and MUST NOT log model/provider text.
    with urllib.request.urlopen(request,timeout=18) as reply:
        payload=json.loads(reply.read(16384))
    transcript=payload.get("text") if isinstance(payload,dict) else None
    if not isinstance(transcript,str) or not transcript.strip() or len(transcript)>300:
        raise ValueError("Whisper did not return one bounded transcript")
    return transcript.strip()
