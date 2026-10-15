"""Voix locale (Piper), plan par plan -> narration.wav + durées réelles dans storyboard.json.
Usage: tts_piper.py video_id [--force]   Corrige les prononciations dans prompts/prononciation.json"""
import sys, re, subprocess, wave
from config import *


def clean(t):
    t = re.sub(r"\[[^\]]*\]", "", t)
    t = re.sub(r"[*_#`>]+", "", t)
    pron = PROMPTS / "prononciation.json"
    if pron.exists():
        for k, v in read_json(pron).items():
            t = re.sub(rf"\b{re.escape(k)}\b", v, t)
    return re.sub(r"\s+", " ", t).strip()


def synth(text, out):
    r = subprocess.run([sys.executable, "-m", "piper", "-m", str(PIPER_VOICE), "-f", str(out)],
                       input=text.encode("utf-8"), capture_output=True)
    if r.returncode != 0 or not out.exists():
        raise RuntimeError("Piper a échoué : " + r.stderr.decode("utf-8", "replace")[-600:])


if __name__ == "__main__":
    vid, force = sys.argv[1], "--force" in sys.argv
    p = pdir(vid)
    (p / "audio").mkdir(exist_ok=True)
    sb = read_json(p / "storyboard.json")
    plans = sb["plans"]
    if not PIPER_VOICE.exists():
        raise SystemExit(f"Voix introuvable : {PIPER_VOICE} (voir README, étape voix)")
    frames_all, params = [], None
    for i, pl in enumerate(plans, 1):
        wav = p / "audio" / f"plan_{pl['id']:03d}.wav"
        if force or not wav.exists():
            log(f"Voix {i}/{len(plans)}")
            synth(clean(pl["narration"]), wav)
        with wave.open(str(wav), "rb") as w:
            if params is None:
                params = w.getparams()
            data, rate = w.readframes(w.getnframes()), w.getframerate()
        pause = GAP + (TAIL if i == len(plans) else 0)
        silence = b"\x00" * (int(pause * rate) * params.sampwidth * params.nchannels)
        pl["duration"] = round(len(data) / (rate * params.sampwidth * params.nchannels) + pause, 3)
        frames_all.append(data + silence)
    with wave.open(str(p / "audio" / "narration.wav"), "wb") as w:
        w.setnchannels(params.nchannels); w.setsampwidth(params.sampwidth); w.setframerate(params.framerate)
        w.writeframes(b"".join(frames_all))
    write_json(p / "storyboard.json", sb)
    log(f"narration.wav : {sum(pl['duration'] for pl in plans):.1f} s")
