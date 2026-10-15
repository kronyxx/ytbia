import sys, os, json, subprocess
ROOT = os.environ.get("YT_ROOT", r"C:\YouTubeIA")
W, H, FPS = 1920, 1080, 25
QUEUE_FIN = 0.8   # secondes ajoutees apres la derniere phrase

def run(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stderr[-2000:]); sys.exit(1)

def zoompan(motion, n):
    cx, cy = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    z, x, y = f"1+0.12*on/{n}", cx, cy
    if motion == "zoom_out":
        z = f"1.12-0.12*on/{n}"
    elif motion == "pan_left":
        z, x = "1.12", f"(iw-iw/zoom)*(1-on/{n})"
    elif motion == "pan_right":
        z, x = "1.12", f"(iw-iw/zoom)*on/{n}"
    return f"zoompan=z='{z}':x='{x}':y='{y}':d={n}:s={W}x{H}:fps={FPS}"

vid = sys.argv[1]
d = os.path.join(ROOT, "projects", vid)
plans = json.load(open(os.path.join(d, "storyboard.json"), encoding="utf-8"))
if isinstance(plans, dict):
    plans = plans["plans"]
tim = json.load(open(os.path.join(d, "timings.json"), encoding="utf-8"))
os.makedirs(os.path.join(d, "clips"), exist_ok=True)
os.makedirs(os.path.join(d, "output"), exist_ok=True)

durs = {}
for k, t in enumerate(tim):
    if k + 1 < len(tim):
        durs[t["id"]] = tim[k + 1]["debut"] - t["debut"]
    else:
        durs[t["id"]] = t["duree"] + QUEUE_FIN

liste, total = [], 0.0
for i, pl in enumerate(plans, 1):
    pid = pl.get("id", i)
    dur = durs[pid]
    n = max(2, round(dur * FPS))
    total += n / FPS
    print(f"clip {i}/{len(plans)}", flush=True)
    vf = (f"scale=3840:2160:force_original_aspect_ratio=increase:flags=lanczos,crop=3840:2160,"
          f"{zoompan(pl.get('motion', 'zoom_in'), n)},format=yuv420p")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"images/plan_{pid:03d}.png", "-vf", vf,
         "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-r", str(FPS), f"clips/clip_{i:03d}.mp4"], d)
    liste.append(f"file 'clip_{i:03d}.mp4'")

open(os.path.join(d, "clips", "list.txt"), "w", encoding="utf-8").write("\n".join(liste))
run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", "all.mp4"],
    os.path.join(d, "clips"))

style = ("FontName=Arial,FontSize=16,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
         "BorderStyle=1,Outline=2,Shadow=0,MarginV=30")
fc = (f"[0:v]fade=t=in:st=0:d=0.6,fade=t=out:st={max(0, total - 1.2):.2f}:d=1.2,"
      f"subtitles=sous_titres.srt:force_style='{style}'[v];"
      "[1:a]aresample=48000,loudnorm=I=-16:TP=-1.5,apad[a]")
print("Assemblage final", flush=True)
run(["ffmpeg", "-y", "-loglevel", "error", "-i", "clips/all.mp4", "-i", "audio.wav", "-filter_complex", fc,
     "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
     "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.3f}", "-movflags", "+faststart", "output/final.mp4"], d)
print(f"OK : {os.path.join(d, 'output', 'final.mp4')} ({total:.1f} s)")