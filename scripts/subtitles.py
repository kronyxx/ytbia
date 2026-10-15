"""Sous-titres (faster-whisper, CPU pour laisser la VRAM libre) + contrôle de la voix.  Python du venv-asr."""
import sys, os, textwrap, difflib, re
from config import *
from faster_whisper import WhisperModel


def t(s):
    ms = round(s * 1000); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); sec, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{sec:02},{ms:03}"


if __name__ == "__main__":
    vid = sys.argv[1]
    p = pdir(vid)
    model = WhisperModel(os.environ.get("WHISPER_MODEL", "small"), device="cpu", compute_type="int8")
    segs, _ = model.transcribe(str(p / "audio" / "narration.wav"), language="fr", vad_filter=True, word_timestamps=True)
    cues, cur, heard = [], [], []
    for seg in segs:
        heard.append(seg.text)
        for w in seg.words or []:
            cur.append(w)
            end = w.word.strip()[-1:] in ".?!,;:"
            if len(cur) >= 9 or (end and len(cur) >= 4):
                cues.append(cur); cur = []
        if cur:
            cues.append(cur); cur = []
    with open(p / "subtitles.srt", "w", encoding="utf-8") as f:
        for i, c in enumerate(cues, 1):
            txt = "".join(w.word for w in c).strip()
            f.write(f"{i}\n{t(c[0].start)} --> {t(c[-1].end)}\n{chr(10).join(textwrap.wrap(txt, 42))}\n\n")
    norm = lambda s: re.sub(r"[^a-zàâçéèêëîïôûùüÿœ0-9 ]", "", s.lower())
    ref = norm(" ".join(pl["narration"] for pl in read_json(p / "storyboard.json")["plans"]))
    ratio = difflib.SequenceMatcher(None, ref.split(), norm(" ".join(heard)).split()).ratio()
    log(f"subtitles.srt : {len(cues)} sous-titres ; fidélité voix/script ≈ {ratio:.0%} (sous 85 % : réécouter la voix)")
