"""Images via l'API ComfyUI (SDXL). Reprend là où ça s'est arrêté.  Usage: comfy_gen.py video_id [--force]"""
import sys, time, random, urllib.parse
from config import *


def workflow(prompt, seed, w, h, prefix):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": COMFY_CKPT}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": f"{STYLE}, {prompt}", "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": NEGATIVE, "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": STEPS, "cfg": CFG,
              "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0,
              "model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": prefix}},
    }


def generate(prompt, seed, w, h, out):
    pid = http_json(COMFY_URL + "/prompt", {"prompt": workflow(prompt, seed, w, h, "yt")})["prompt_id"]
    t0 = time.time()
    while time.time() - t0 < 900:
        hist = http_json(f"{COMFY_URL}/history/{pid}", timeout=30)
        if pid in hist and hist[pid].get("outputs"):
            for node in hist[pid]["outputs"].values():
                for im in node.get("images", []):
                    q = urllib.parse.urlencode({"filename": im["filename"], "subfolder": im["subfolder"], "type": im["type"]})
                    out.write_bytes(http_bytes(f"{COMFY_URL}/view?{q}"))
                    return
            raise RuntimeError("Aucune image dans la sortie ComfyUI")
        time.sleep(1.5)
    raise TimeoutError("ComfyUI : délai dépassé")


if __name__ == "__main__":
    vid, force = sys.argv[1], "--force" in sys.argv
    p = pdir(vid)
    (p / "images").mkdir(exist_ok=True)
    seed0 = random.Random(vid).randint(1, 10**9)   # graine stable par vidéo
    plans = read_json(p / "storyboard.json")["plans"]
    for i, pl in enumerate(plans, 1):
        out = p / "images" / pl.get("image", f"plan_{pl['id']:03d}.png")
        if out.exists() and not force:
            continue
        log(f"Image {i}/{len(plans)}")
        generate(pl["image_prompt"], seed0 + i, IMG_W, IMG_H, out)
    meta = p / "metadata.json"
    if meta.exists() and (force or not (p / "thumbnail.png").exists()):
        log("Miniature")
        generate(read_json(meta).get("thumbnail_prompt", "dramatic close-up of a car engine, high contrast"),
                 seed0, 1344, 768, p / "thumbnail.png")
    try:  # libère la VRAM
        http_json(COMFY_URL + "/free", {"unload_models": True, "free_memory": True}, timeout=30)
    except Exception:
        pass
    log("Images terminées")
