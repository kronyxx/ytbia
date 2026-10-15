"""Montage FFmpeg piloté par storyboard.json : zooms/panoramiques, voix normalisée, musique avec ducking, sous-titres.
Usage: montage.py video_id   (musique optionnelle : audio/musique.wav|mp3)"""
import sys, subprocess, json
from config import *


def run(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stderr[-2000:]); sys.exit(1)


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def zoompan(motion, n):
    cx, cy = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    z, x, y = f"1+0.15*on/{n}", cx, cy
    if motion == "zoom_out":
        z = f"1.15-0.15*on/{n}"
    elif motion == "pan_left":
        z, x = "1.15", f"(iw-iw/zoom)*(1-on/{n})"
    elif motion == "pan_right":
        z, x = "1.15", f"(iw-iw/zoom)*on/{n}"
    return f"zoompan=z='{z}':x='{x}':y='{y}':d={n}:s={W}x{H}:fps={FPS}"


if __name__ == "__main__":
    vid = sys.argv[1]
    p = pdir(vid)
    plans = read_json(p / "storyboard.json")["plans"]
    (p / "clips").mkdir(exist_ok=True); (p / "output").mkdir(exist_ok=True)
    lst = []
    for i, pl in enumerate(plans, 1):
        log(f"clip {i}/{len(plans)}")
        n = max(2, round(pl["duration"] * FPS))
        img = f"images/{pl.get('image', 'plan_%03d.png' % pl.get('id', i))}"
        vf = (f"scale=3840:2160:force_original_aspect_ratio=increase:flags=lanczos,crop=3840:2160,"
              f"{zoompan(pl.get('motion', 'zoom_in'), n)},format=yuv420p")
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", img, "-vf", vf, "-c:v", "libx264", "-preset", PRESET,
             "-crf", "18", "-r", str(FPS), f"clips/clip_{i:03d}.mp4"], p)
        lst.append(f"file 'clip_{i:03d}.mp4'")
    (p / "clips" / "list.txt").write_text("\n".join(lst), encoding="utf-8")
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", "all.mp4"], p / "clips")
    total = duration(p / "clips" / "all.mp4")

    music = next((m for m in ("audio/musique.wav", "audio/musique.mp3") if (p / m).exists()), None)
    vchain = f"[0:v]fade=t=in:st=0:d=0.6,fade=t=out:st={max(0, total - 1.2):.2f}:d=1.2"
    if (p / "subtitles.srt").exists():
        vchain += (",subtitles=subtitles.srt:force_style='FontName=Arial,FontSize=12,PrimaryColour=&H00FFFFFF,"
                   "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,MarginV=40'")
    vchain += "[v]"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", "clips/all.mp4", "-i", "audio/narration.wav"]
    if music:
        cmd += ["-stream_loop", "-1", "-i", music]
        af = ("[1:a]aresample=48000,loudnorm=I=-16:TP=-1.5,apad,asplit=2[n1][n2];"
              f"[2:a]aresample=48000,volume={MUSIC_VOL}[m0];"
              "[m0][n2]sidechaincompress=threshold=0.02:ratio=10:attack=20:release=500[md];"
              "[n1][md]amix=inputs=2:duration=first:normalize=0[a]")
    else:
        af = "[1:a]aresample=48000,loudnorm=I=-16:TP=-1.5,apad[a]"
    cmd += ["-filter_complex", f"{vchain};{af}", "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", PRESET,
            "-crf", str(CRF), "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.3f}",
            "-movflags", "+faststart", "output/final.mp4"]
    log("Assemblage final")
    run(cmd, p)
    log(f"OK : {p / 'output' / 'final.mp4'} ({total:.1f} s)")
