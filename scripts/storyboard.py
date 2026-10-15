"""
Storyboard : script.md -> storyboard.json (un plan = narration + prompt d'image SDXL + mouvement).

Usage (PowerShell) :
  C:\\YouTubeIA\\venv-tts\\Scripts\\python.exe C:\\YouTubeIA\\scripts\\storyboard.py video_001 [modele]

Lit  : C:\\YouTubeIA\\projects\\<video>\\script.md
Écrit: C:\\YouTubeIA\\projects\\<video>\\storyboard.json
Utilise le prompt C:\\YouTubeIA\\prompts\\storyboard.txt. Décharge le modèle Ollama à la fin (libère la RAM).
Stdlib uniquement.
"""
import sys, re, json, os, urllib.request

ROOT = os.environ.get("YT_ROOT", r"C:\YouTubeIA")
OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MOUVEMENTS = ["zoom_in", "zoom_out", "pan_left", "pan_right"]
MOTS_PAR_PLAN = 38          # ~15 s de narration par image


def nettoyer(texte):
    texte = re.sub(r"\[S\d+\]", "", texte)
    texte = re.sub(r"\[À VÉRIFIER\]", "", texte, flags=re.I)
    texte = re.sub(r"[#*_`>]+", "", texte)
    texte = re.sub(r"\s+", " ", texte)
    return re.sub(r"\s+([.,;:!?…])", r"\1", texte).strip()


def phrases(texte):
    return [p.strip() for p in re.split(r"(?<=[.!?…])\s+", texte) if p.strip()]


def regrouper(ph, cible=MOTS_PAR_PLAN):
    """Regroupe les phrases en plans de ~cible mots, sans couper une phrase."""
    plans, cur, n = [], [], 0
    for p in ph:
        w = len(p.split())
        if cur and n + w > cible * 1.3:
            plans.append(" ".join(cur)); cur, n = [], 0
        cur.append(p); n += w
        if n >= cible:
            plans.append(" ".join(cur)); cur, n = [], 0
    if cur:
        if plans and n < cible * 0.4:
            plans[-1] += " " + " ".join(cur)
        else:
            plans.append(" ".join(cur))
    return plans


def ollama(prompt, modele, keep_alive="5m", temperature=0.6):
    corps = {"model": modele, "prompt": prompt, "stream": False, "format": "json",
             "think": False, "keep_alive": keep_alive,
             "options": {"temperature": temperature, "num_ctx": 4096}}
    req = urllib.request.Request(OLLAMA + "/api/generate", json.dumps(corps).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)["response"]


def extraire_json(txt):
    txt = re.sub(r"<think>.*?</think>", "", txt, flags=re.S)
    m = re.search(r"\{.*\}", txt, flags=re.S)
    return json.loads(m.group(0)) if m else None


def valider(d, defaut_motion):
    if not isinstance(d, dict) or not str(d.get("image_prompt", "")).strip():
        return None
    mv = d.get("motion") if d.get("motion") in MOUVEMENTS else defaut_motion
    return {"image_prompt": str(d["image_prompt"]).strip(),
            "motion": mv,
            "on_screen_text": str(d.get("on_screen_text", "") or "")}


CADRAGES = ["wide establishing shot", "close-up of a mechanical detail", "top-down view",
            "low-angle front three-quarter view", "side profile on a road", "cockpit / interior detail",
            "macro shot of tire and asphalt", "clean studio shot on a plain background"]


def trop_proche(prompt, deja, seuil=0.55):
    import difflib
    return any(difflib.SequenceMatcher(None, prompt.lower(), d.lower()).ratio() > seuil for d in deja)


def faire_plan(modele_prompt, narration, deja, modele, i, appel=ollama):
    """deja : liste des image_prompt déjà utilisés (on évite de les recopier)."""
    cadrage = CADRAGES[i % len(CADRAGES)]
    evite = " | ".join(d[:90] for d in deja[-3:]) or "aucun"
    prompt = (modele_prompt.replace("[[NARRATION]]", narration)
              .replace("Image du plan précédent (pour la cohérence) : [[PRECEDENT]]",
                       "Images déjà utilisées (NE PAS les reprendre) : " + evite)
              .replace("[[PRECEDENT]]", evite))
    prompt += ("\nConsigne supplémentaire : cadrage imposé = " + cadrage + ". "
               "Le sujet doit être DIFFÉRENT des images déjà utilisées et illustrer concrètement cette narration "
               "(voiture, pneu, suspension, virage, route, balance, mécanisme, etc.). "
               "N'invente pas d'époque ni de décennie ; pas de personnes ; pas de texte dans l'image.")
    defaut = MOUVEMENTS[i % 4]
    for essai in range(4):
        try:
            r = valider(extraire_json(appel(prompt, modele, temperature=0.6 + 0.15 * essai)), defaut)
            if r and not trop_proche(r["image_prompt"], deja):
                return r
        except Exception as e:
            print("   essai raté :", str(e)[:80])
    return {"image_prompt": cadrage + " of a modern car, soft natural light, no text, no people",
            "motion": defaut, "on_screen_text": ""}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    video = sys.argv[1]
    modele = sys.argv[2] if len(sys.argv) > 2 else "qwen3:8b"
    dossier = os.path.join(ROOT, "projects", video)
    texte = nettoyer(open(os.path.join(dossier, "script.md"), encoding="utf-8").read())
    plans = regrouper(phrases(texte))
    modele_prompt = open(os.path.join(ROOT, "prompts", "storyboard.txt"), encoding="utf-8").read()
    sortie, deja = [], []
    for i, narr in enumerate(plans):
        print(f"Plan {i+1}/{len(plans)} ({len(narr.split())} mots)")
        p = faire_plan(modele_prompt, narr, deja, modele, i)
        p.update({"id": i + 1, "narration": narr})
        deja.append(p["image_prompt"])
        sortie.append(p)
    json.dump(sortie, open(os.path.join(dossier, "storyboard.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    try:
        ollama("ok", modele, keep_alive=0)   # décharge le modèle de la RAM
    except Exception:
        pass
    print(f"{len(sortie)} plans écrits dans {dossier}\\storyboard.json")
