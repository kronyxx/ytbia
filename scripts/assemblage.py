import sys, json, subprocess
from pathlib import Path

FPS = 25
vid = sys.argv[1]
test = "--test" in sys.argv
p = Path(__file__).resolve().parent.parent / "projects" / vid

def rj(f):
    return json.loads((p / f).read_text(encoding="utf-8"))

def run(cmd):
    r = subprocess.run(cmd, cwd=p, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stderr[-2500:]); sys.exit(1)
    return r.stdout

plans = rj("storyboard.json")
if isinstance(plans, dict):
    plans = plans["plans"]
timings = {t["id"]: t for t in rj("timings.json")}
total = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                   "-of", "csv=p=0", "audio.wav"]).strip())

def zp(motion, n):
    z, x = f"1+0.15*on/{n}", "iw/2-(iw/zoom/2)"
    y = "ih/2-(ih/zoom/2)"
    if motion == "zoom_out":
        z = f"1.15-0.15*on/{n}"
    elif motion == "pan_left":
        z, x = "1.15", f"(iw-iw/zoom)*(1-on/{n})"
    elif motion == "pan_right":
        z, x = "1.15", f"(iw-iw/zoom)*on/{n}"
    return f"zoompan=z='{z}':x='{x}':y='{y}':d={n}:s=1920x1080:fps={FPS}"

(p / "clips").mkdir(exist_ok=True)
(p / "output").mkdir(exist_ok=True)
if test:
    plans = plans[:3]

liste = []
for i, pl in enumerate(plans):
    pid = pl["id"]
    debut = timings[pid]["debut"]
    nxt = plans[i + 1]["id"] if i + 1 < len(plans) else None
    fin = timings[nxt]["debut"] if nxt else total
    f0, f1 = round(debut * FPS), round(fin * FPS)
    n = max(2, f1 - f0)
    img = f"images/plan_{pid:03d}.png"
    clip = f"clips/clip_{pid:03d}.mp4"
    print(f"clip {i+1}/{len(plans)} ({n} images)")
    vf = f"scale=3840:2160:flags=lanczos,{zp(pl.get('motion', 'zoom_in'), n)},format=yuv420p"
    run(["ffmpeg", "-y", "-i", img, "-vf", vf, "-frames:v", str(n),
         "-c:v", "libx264", "-crf", "18", "-r", str(FPS), clip])
    liste.append(f"file '{clip}'")

(p / "liste.txt").write_text("\n".join(liste), encoding="utf-8")
print("concatenation...")
run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "liste.txt", "-c", "copy", "clips/video_sans_son.mp4"])

print("voix + sous-titres...")
style = "FontName=Arial,FontSize=16,Outline=2,Shadow=0,MarginV=45,Alignment=2"
sortie = f"output/{vid}{'_test' if test else ''}.mp4"
run(["ffmpeg", "-y", "-i", "clips/video_sans_son.mp4", "-i", "audio.wav",
     "-vf", f"subtitles=sous_titres.srt:force_style='{style}'",
     "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
     "-c:a", "aac", "-b:a", "192k", "-shortest", sortie])
print("termine :", p / sortie)
