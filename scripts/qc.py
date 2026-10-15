"""Contrôle qualité technique -> quality_report.json. Code retour 1 si un contrôle échoue.
Ne prouve PAS que les faits sont exacts : relecture humaine obligatoire."""
import sys, re, json, wave, subprocess
from config import *

vid = sys.argv[1]
p = pdir(vid)
res = []


def chk(name, ok, detail=""):
    res.append({"controle": name, "ok": bool(ok), "detail": detail})
    print(("[OK]   " if ok else "[FAIL] ") + name + (f" — {detail}" if detail else ""))


script = (p / "script.md").read_text(encoding="utf-8") if (p / "script.md").exists() else ""
chk("script présent (≥ 600 mots)", len(script.split()) >= 600, f"{len(script.split())} mots")
chk("aucun [À VÉRIFIER] restant", "[À VÉRIFIER]" not in script and "[A VERIFIER]" not in script.upper())
try:
    src = read_json(p / "sources.json")
    chk("sources.json (≥ 2 sources)", len(src) >= 2, f"{len(src)} sources")
except Exception:
    chk("sources.json (≥ 2 sources)", False, "absent")

srt = p / "subtitles.srt"
blocks = re.findall(r"\d+\n\d\d:\d\d:\d\d,\d{3} --> \d\d:\d\d:\d\d,\d{3}\n\S", srt.read_text(encoding="utf-8")) if srt.exists() else []
chk("sous-titres valides", len(blocks) > 0, f"{len(blocks)} blocs")

final = p / "output" / "final.mp4"
if final.exists():
    pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height",
                                    "-show_entries", "format=duration", "-of", "json", str(final)],
                                   capture_output=True, text=True).stdout)
    st = pr["streams"]; vd = float(pr["format"]["duration"])
    v = [s for s in st if s["codec_type"] == "video"]
    chk("piste vidéo", bool(v)); chk("piste audio", any(s["codec_type"] == "audio" for s in st))
    chk("résolution 1920x1080", bool(v) and (v[0]["width"], v[0]["height"]) == (1920, 1080))
    try:
        with wave.open(str(p / "audio" / "narration.wav")) as w:
            nd = w.getnframes() / w.getframerate()
        chk("durée cohérente avec la narration", abs(vd - nd) <= 2.0, f"vidéo {vd:.1f}s / voix {nd:.1f}s")
    except Exception:
        chk("durée cohérente avec la narration", False, "narration.wav illisible")
    sil = subprocess.run(["ffmpeg", "-i", str(final), "-af", "silencedetect=noise=-45dB:d=3", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    chk("pas de silence > 3 s", "silence_start" not in sil)
    vol = subprocess.run(["ffmpeg", "-i", str(final), "-af", "volumedetect", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    m = re.search(r"max_volume: (-?[\d.]+) dB", vol)
    chk("pas d'écrêtage", bool(m) and float(m.group(1)) < 0, f"max {m.group(1)} dB" if m else "mesure impossible")
else:
    chk("final.mp4 présent", False)

chk("metadata.json présent", (p / "metadata.json").exists())
chk("miniature présente", (p / "thumbnail.png").exists())
ok = all(r["ok"] for r in res)
write_json(p / "quality_report.json", {"ok": ok, "controles": res})
print("\nRÉSULTAT :", "SUCCÈS techniques (relecture humaine encore requise)" if ok else "ÉCHEC — corriger avant publication")
sys.exit(0 if ok else 1)
