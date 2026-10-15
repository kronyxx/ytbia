"""Configuration commune à tous les scripts. Tout se règle ici ou par variables d'environnement."""
import os, sys, json, time, urllib.request
from pathlib import Path

ROOT = Path(os.environ.get("YT_ROOT", r"C:\YouTubeIA"))
PROJECTS = ROOT / "projects"
PROMPTS = Path(os.environ.get("YT_PROMPTS", str(ROOT / "prompts")))
VOICES = ROOT / "voices"

# --- Ollama (texte) ---
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:8b")
OLLAMA_CTX = 10240

# --- ComfyUI (images) : 8188 = version portable, 8000 = application Desktop ---
COMFY_URL = os.environ.get("COMFY_URL", "http://127.0.0.1:8188")
COMFY_CKPT = os.environ.get("COMFY_CKPT", "sd_xl_base_1.0.safetensors")
IMG_W, IMG_H = 1344, 768          # SDXL, ~16:9, redimensionné en 1920x1080 au montage
STEPS, CFG = 28, 6.5
STYLE = ("cinematic documentary still, dramatic lighting, shallow depth of field, "
         "muted film color grading, highly detailed, photorealistic, 35mm")
NEGATIVE = ("text, letters, watermark, logo, signature, caption, lowres, blurry, "
            "deformed, distorted car, extra wheels, bad anatomy, oversaturated, cartoon")

# --- Voix (Piper) ---
PIPER_VOICE = Path(os.environ.get("PIPER_VOICE", str(VOICES / "fr_FR-siwis-medium.onnx")))
GAP, TAIL = 0.35, 0.8             # pause entre plans / silence final (secondes)

# --- Montage ---
W, H, FPS = 1920, 1080, 25
CRF, PRESET = 19, os.environ.get("YT_PRESET", "medium")
MUSIC_VOL = 0.25                  # avant compression sidechain
WORDS_PER_PLAN = 35               # ~12-14 s par image

MOTIONS = ["zoom_in", "zoom_out", "pan_left", "pan_right"]


def pdir(video_id):
    return PROJECTS / video_id


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def log(msg):
    print(time.strftime("[%H:%M:%S] ") + str(msg), flush=True)


def http_json(url, payload=None, timeout=600):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json", "User-Agent": "YouTubeIA-kit/1.0 (usage personnel)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def http_bytes(url, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": "YouTubeIA-kit/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()
