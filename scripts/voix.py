"""
Voix : storyboard.json -> audio\\plan_001.wav ... + audio.wav (complet) + timings.json + texte_sous_titres.txt

Usage (PowerShell) :
  C:\\YouTubeIA\\venv-tts\\Scripts\\python.exe C:\\YouTubeIA\\scripts\\voix.py video_001

- Une synthèse Piper par plan (durée exacte de chaque plan -> calage des images).
- Applique prononciation.json UNIQUEMENT à la voix (les sous-titres gardent l'orthographe normale).
- Voix : variable PIPER_VOICE (défaut fr_FR-tom-medium), fichiers dans C:\\YouTubeIA\\voices.
- Reprend là où il s'est arrêté. Stdlib uniquement (+ piper du venv).
"""
import sys, os, re, json, wave, subprocess

ROOT = os.environ.get("YT_ROOT", r"C:\YouTubeIA")
VOIX = os.environ.get("PIPER_VOICE", "fr_FR-tom-medium")
SILENCE_S = 0.35          # pause entre deux plans


def nettoyer(texte):
    texte = re.sub(r"\[S\d+\]", "", texte)
    texte = re.sub(r"\[À VÉRIFIER\]", "", texte, flags=re.I)
    texte = re.sub(r"[#*_`>]+", "", texte)
    texte = re.sub(r"\s+", " ", texte)
    return re.sub(r"\s+([.,;:!?…])", r"\1", texte).strip()


def prononciation(texte, table):
    for mot in sorted(table, key=len, reverse=True):
        texte = re.sub(r"(?<![\wÀ-ÿ])" + re.escape(mot) + r"(?![\wÀ-ÿ])", table[mot], texte)
    return texte


def piper(texte, sortie):
    # PIPER_VOICE peut être un nom ("fr_FR-tom-medium") ou un chemin complet (".../fr_FR-tom-medium.onnx")
    if VOIX.lower().endswith(".onnx"):
        modele = VOIX if os.path.isabs(VOIX) else os.path.join(ROOT, "voices", VOIX)
    else:
        modele = os.path.join(ROOT, "voices", VOIX + ".onnx")
    if not os.path.exists(modele):
        sys.exit(f"Voix introuvable : {modele}\nTélécharge-la : python -m piper.download_voices {VOIX} --data-dir {ROOT}\\voices")
    r = subprocess.run([sys.executable, "-m", "piper", "-m", modele, "-f", sortie],
                       input=texte.encode("utf-8"), capture_output=True, env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
    if r.returncode != 0 or not os.path.exists(sortie):
        raise RuntimeError(r.stderr.decode("utf-8", "replace")[-300:])


def duree(chemin):
    with wave.open(chemin) as w:
        return w.getnframes() / w.getframerate()


def assembler(fichiers, sortie, silence=SILENCE_S):
    """Concatène des wav de même format en insérant du silence ; retourne les débuts de chaque fichier."""
    debuts, t = [], 0.0
    with wave.open(fichiers[0]) as w0:
        params = w0.getparams()
    sil = b"\x00" * (int(params.framerate * silence) * params.sampwidth * params.nchannels)
    with wave.open(sortie, "wb") as out:
        out.setparams(params)
        for i, f in enumerate(fichiers):
            with wave.open(f) as w:
                if w.getparams()[:3] != params[:3] or w.getframerate() != params.framerate:
                    raise ValueError("formats audio différents : " + f)
                debuts.append(round(t, 3))
                out.writeframes(w.readframes(w.getnframes()))
                t += w.getnframes() / w.getframerate()
            if i < len(fichiers) - 1:
                out.writeframes(sil)
                t += silence
    return debuts


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    dossier = os.path.join(ROOT, "projects", sys.argv[1])
    plans = json.load(open(os.path.join(dossier, "storyboard.json"), encoding="utf-8"))
    table = {}
    chemin_pron = os.path.join(ROOT, "prompts", "prononciation.json")
    if os.path.exists(chemin_pron):
        table = json.load(open(chemin_pron, encoding="utf-8"))
    audio_dir = os.path.join(dossier, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    fichiers = []
    for p in plans:
        f = os.path.join(audio_dir, f"plan_{p['id']:03d}.wav")
        if not os.path.exists(f):
            texte = prononciation(nettoyer(p["narration"]), table)
            print(f"Plan {p['id']}/{len(plans)} : synthèse ({len(texte.split())} mots)")
            piper(texte, f)
        else:
            print(f"Plan {p['id']}/{len(plans)} : déjà fait")
        fichiers.append(f)
    complet = os.path.join(dossier, "audio.wav")
    debuts = assembler(fichiers, complet)
    timings = [{"id": p["id"], "debut": d, "duree": round(duree(f), 3)}
               for p, d, f in zip(plans, debuts, fichiers)]
    json.dump(timings, open(os.path.join(dossier, "timings.json"), "w"), indent=2)
    texte_sub = " ".join(nettoyer(p["narration"]) for p in plans)
    open(os.path.join(dossier, "texte_sous_titres.txt"), "w", encoding="utf-8").write(texte_sub)
    total = duree(complet)
    print(f"Terminé : audio.wav = {int(total//60)} min {int(total%60)} s, {len(plans)} plans.")



