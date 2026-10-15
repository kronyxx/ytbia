"""Orchestrateur sans n8n (ou en secours).
  run_pipeline.py video_001 "Sujet" --phase a     -> projet, sources, script  (puis TU relis script.md)
  run_pipeline.py video_001 --phase b             -> storyboard, métadonnées, voix, images, sous-titres, montage, QC"""
import sys, os, subprocess, time
from pathlib import Path
from config import *
import gestion_gpu
MODES = {'fetch_sources.py':'ollama','ollama_gen.py':'ollama','comfy_gen.py':'comfy','subtitles.py':'libre'}

HERE = Path(__file__).parent
ASR = os.environ.get("YT_PY_ASR", str(ROOT / "venv-asr" / "Scripts" / "python.exe"))
args = [a for a in sys.argv[1:] if not a.startswith("--")]
phase = sys.argv[sys.argv.index("--phase") + 1] if "--phase" in sys.argv else "a"
args = [a for a in args if a not in ("a", "b", "all")]
vid, topic = args[0], " ".join(args[1:])


def step(name, script, *a, py=None, retries=0):
    for attempt in range(retries + 1):
        log(f"=== {name}" + (f" (essai {attempt + 1})" if attempt else ""))
        t0 = time.time()
        if script in MODES: gestion_gpu.mode(MODES[script])
        r = subprocess.run([py or sys.executable, str(HERE / script), *a])
        with open(pdir(vid).parent / f"{vid}.log", "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%F %T')} {name} code={r.returncode} {time.time() - t0:.0f}s\n")
        if r.returncode == 0:
            return
    sys.exit(f"ÉCHEC à l'étape « {name} » — corrige puis relance la même commande (les étapes terminées sont reprises).")


if phase in ("a", "all"):
    step("Créer le projet", "new_project.py", vid, topic or vid)
    step("Collecter les sources", "fetch_sources.py", vid)
    step("Script (Ollama)", "ollama_gen.py", "script", vid, retries=1)
    if phase == "a":
        print("\nPAUSE VALIDATION : relis script.md et verification.md, retire les [À VÉRIFIER], puis --phase b")
if phase in ("b", "all"):
    sc = pdir(vid) / "script.md"
    if not sc.exists() or "[À VÉRIFIER]" in sc.read_text(encoding="utf-8"):
        sys.exit("Script absent ou contenant encore des [À VÉRIFIER] : validation humaine requise.")
    step("Storyboard", "ollama_gen.py", "storyboard", vid, retries=1)
    step("Métadonnées", "ollama_gen.py", "metadata", vid, retries=1)
    step("Voix (Piper)", "tts_piper.py", vid)
    step("Images (ComfyUI)", "comfy_gen.py", vid, retries=1)
    step("Sous-titres (Whisper)", "subtitles.py", vid, py=ASR)
    step("Montage (FFmpeg)", "montage.py", vid)
    step("Contrôle qualité", "qc.py", vid)

