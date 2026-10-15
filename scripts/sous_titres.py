import gestion_gpu; gestion_gpu.mode('libre')
"""
Sous-titres : texte EXACT du script + temps fournis par Whisper.

Usage (PowerShell) :
  C:\\YouTubeIA\\venv-asr\\Scripts\\python.exe sous_titres.py audio.wav script.md sortie.srt [modele]

- Retire [S1], [À VÉRIFIER], markdown du texte.
- Whisper ne sert qu'à dater les mots ; le texte affiché est toujours celui du script.
- GPU d'abord (DLL CUDA du venv), CPU en secours.
"""
import os, sys, re, glob, difflib, unicodedata

# --- DLL CUDA installées par pip (nvidia-cublas-cu12, nvidia-cudnn-cu12) ---
_sp = os.path.join(sys.prefix, "Lib", "site-packages", "nvidia")
for _d in glob.glob(os.path.join(_sp, "*", "bin")):
    try:
        os.add_dll_directory(_d)
    except (AttributeError, OSError):
        pass
    os.environ["PATH"] = _d + os.pathsep + os.environ.get("PATH", "")


def nettoyer(texte):
    texte = re.sub(r"\[S\d+\]", "", texte)
    texte = re.sub(r"\[À VÉRIFIER\]", "", texte, flags=re.I)
    texte = re.sub(r"[#*_`>]+", "", texte)
    texte = re.sub(r"\s+", " ", texte)
    texte = re.sub(r"\s+([.,;:!?…])", r"\1", texte)
    return texte.strip()


def norm(mot):
    mot = unicodedata.normalize("NFD", mot.lower())
    mot = "".join(c for c in mot if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", mot)


def aligner(mots_script, mots_whisper, duree):
    """mots_script: list[str]; mots_whisper: list[(mot,debut,fin)].
    Retourne list[(debut,fin)] pour chaque mot du script."""
    n = len(mots_script)
    t = [None] * n
    a = [norm(m) for m in mots_script]
    b = [norm(w[0]) for w in mots_whisper]
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                t[i1 + k] = (mots_whisper[j1 + k][1], mots_whisper[j1 + k][2])
    # mots non appariés : répartition linéaire entre voisins connus
    debut_audio = mots_whisper[0][1] if mots_whisper else 0.0
    fin_audio = mots_whisper[-1][2] if mots_whisper else duree
    i = 0
    while i < n:
        if t[i] is not None:
            i += 1
            continue
        j = i
        while j < n and t[j] is None:
            j += 1
        t0 = t[i - 1][1] if i > 0 else debut_audio
        t1 = t[j][0] if j < n else fin_audio
        t1 = max(t1, t0)
        pas = (t1 - t0) / (j - i)
        for k in range(i, j):
            t[k] = (t0 + (k - i) * pas, t0 + (k - i + 1) * pas)
        i = j
    return t


def decouper(mots, temps, max_mots=8, max_car=42):
    cues, cur = [], []
    for m, tm in zip(mots, temps):
        cur.append((m, tm))
        txt = " ".join(x[0] for x in cur)
        fin_phrase = re.search(r"[.!?…]$", m) is not None
        pause = re.search(r"[,;:]$", m) is not None
        if fin_phrase or len(cur) >= max_mots or len(txt) >= max_car or (pause and len(txt) > 25):
            cues.append(cur)
            cur = []
    if cur:
        cues.append(cur)
    out = []
    for c in cues:
        out.append((c[0][1][0], c[-1][1][1], " ".join(x[0] for x in c)))
    # évite les trous courts entre deux sous-titres
    for k in range(len(out) - 1):
        d, f, tx = out[k]
        if 0 < out[k + 1][0] - f < 0.35:
            out[k] = (d, out[k + 1][0], tx)
    return out


def fmt(s):
    s = max(s, 0)
    h, r = divmod(s, 3600)
    m, r = divmod(r, 60)
    sec, ms = divmod(r, 1)
    return f"{int(h):02d}:{int(m):02d}:{int(sec):02d},{int(ms*1000):03d}"


def ecrire_srt(cues, chemin):
    with open(chemin, "w", encoding="utf-8") as f:
        for i, (d, fi, tx) in enumerate(cues, 1):
            f.write(f"{i}\n{fmt(d)} --> {fmt(fi)}\n{tx}\n\n")


def charger_whisper(taille):
    from faster_whisper import WhisperModel
    try:
        import numpy as np
        m = WhisperModel(taille, device="cuda", compute_type="float16")
        list(m.transcribe(np.zeros(16000, dtype="float32"), language="fr")[0])
        return m
    except Exception as e:
        print(f"GPU indisponible ({str(e)[:80]}), passage au CPU.")
        return WhisperModel(taille, device="cpu", compute_type="int8")


def mots_whisper(audio, taille):
    m = charger_whisper(taille)
    segs, info = m.transcribe(audio, language="fr", word_timestamps=True)
    mots = []
    for s in segs:
        for w in (s.words or []):
            mots.append((w.word.strip(), w.start, w.end))
    return mots, info.duration


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    audio, fichier_texte, sortie = sys.argv[1:4]
    taille = sys.argv[4] if len(sys.argv) > 4 else "medium"
    texte = nettoyer(open(fichier_texte, encoding="utf-8").read())
    mots_s = texte.split()
    mw, duree = mots_whisper(audio, taille)
    temps = aligner(mots_s, mw, duree)
    cues = decouper(mots_s, temps)
    ecrire_srt(cues, sortie)
    print(f"{len(cues)} sous-titres écrits dans {sortie} ({len(mots_s)} mots du script, {len(mw)} mots Whisper).")

