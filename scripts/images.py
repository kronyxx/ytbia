import gestion_gpu; gestion_gpu.mode('comfy')
"""
Images : storyboard.json -> images\\plan_001.png ... via l'API ComfyUI (SDXL, 16:9).

Usage (PowerShell) - ComfyUI doit tourner (run_nvidia_gpu.bat) :
  C:\\YouTubeIA\\venv-tts\\Scripts\\python.exe C:\\YouTubeIA\\scripts\\images.py video_001

- Reprend là où il s'est arrêté (saute les images déjà faites).
- Même style ajouté à tous les prompts, seed fixe par plan (reproductible).
Stdlib uniquement.
"""
import sys, os, json, time, urllib.request, urllib.parse

ROOT = os.environ.get("YT_ROOT", r"C:\YouTubeIA")
COMFY = os.environ.get("COMFY_URL", "http://127.0.0.1:8188")
CKPT = "sd_xl_base_1.0.safetensors"
LARGEUR, HAUTEUR = 1344, 768
STYLE = ("realistic digital illustration, cinematic lighting, high detail, sharp focus, "
         "no text, no logo, no people")
NEGATIF = ("text, letters, words, caption, label, signature, copyright, watermark, logo, brand, badge, emblem, license plate, people, face, hands, blurry, deformed, "
           "low quality, cartoon, anime, oversaturated")
SEED_BASE = 1000
STEPS, CFG = 28, 7


def court(prompt, n=60):
    return " ".join(prompt.split()[:n])


def workflow(prompt, seed, prefixe):
    return {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": LARGEUR, "height": HAUTEUR, "batch_size": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": f"{court(prompt)}, {STYLE}", "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": NEGATIF, "clip": ["4", 1]}},
        "3": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": STEPS, "cfg": CFG,
              "sampler_name": "euler", "scheduler": "normal", "denoise": 1,
              "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": prefixe, "images": ["8", 0]}},
    }


def http_json(url, data=None):
    req = urllib.request.Request(url, json.dumps(data).encode() if data is not None else None,
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def generer(prompt, seed, prefixe, timeout=420):
    pid = http_json(COMFY + "/prompt", {"prompt": workflow(prompt, seed, prefixe)})["prompt_id"]
    t0 = time.time()
    while time.time() - t0 < timeout:
        h = http_json(f"{COMFY}/history/{pid}")
        if pid in h:
            sorties = h[pid].get("outputs", {})
            for o in sorties.values():
                for im in o.get("images", []):
                    q = urllib.parse.urlencode({"filename": im["filename"],
                                                "subfolder": im.get("subfolder", ""), "type": im["type"]})
                    with urllib.request.urlopen(f"{COMFY}/view?{q}", timeout=60) as r:
                        return r.read()
            raise RuntimeError("ComfyUI n'a renvoyé aucune image : " + json.dumps(h[pid].get("status", {}))[:300])
        time.sleep(1.5)
    raise TimeoutError("génération trop longue")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    dossier = os.path.join(ROOT, "projects", sys.argv[1])
    plans = json.load(open(os.path.join(dossier, "storyboard.json"), encoding="utf-8"))
    sortie = os.path.join(dossier, "images")
    os.makedirs(sortie, exist_ok=True)
    try:
        urllib.request.urlopen(COMFY + "/system_stats", timeout=5)
    except Exception:
        sys.exit("ComfyUI ne répond pas sur " + COMFY + " : lance run_nvidia_gpu.bat d'abord.")
    for p in plans:
        chemin = os.path.join(sortie, f"plan_{p['id']:03d}.png")
        if os.path.exists(chemin):
            print(f"Plan {p['id']}/{len(plans)} : déjà fait")
            continue
        t0 = time.time()
        for essai in (1, 2):
            try:
                png = generer(p["image_prompt"], SEED_BASE + p["id"], f"{os.path.basename(dossier)}_{p['id']:03d}")
                open(chemin, "wb").write(png)
                print(f"Plan {p['id']}/{len(plans)} : ok ({time.time()-t0:.0f} s)")
                break
            except Exception as e:
                print(f"Plan {p['id']} essai {essai} échoué : {str(e)[:200]}")
        else:
            print(f"Plan {p['id']} : ABANDONNÉ (relance le script pour réessayer)")
    print("Terminé. Images dans", sortie)


