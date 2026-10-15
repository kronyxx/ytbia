"""Génération de texte locale (Ollama).  Usage: ollama_gen.py {script|storyboard|metadata} video_id"""
import sys, re, json
from config import *

DEFAULT_SECTIONS = [
    {"titre": "Accroche", "objectif": "Poser une question ou un paradoxe concret"},
    {"titre": "Contexte", "objectif": "Situer le sujet et promettre ce que la vidéo va expliquer"},
    {"titre": "Mise en place", "objectif": "Raconter le début de l'histoire"},
    {"titre": "Explications", "objectif": "Expliquer les choix techniques avec les preuves"},
    {"titre": "Rebondissement", "objectif": "Montrer la conséquence ou la surprise"},
    {"titre": "Conclusion", "objectif": "Répondre à la question centrale et ouvrir"},
]


def prompt(name, **kw):
    t = (PROMPTS / name).read_text(encoding="utf-8")
    for k, v in kw.items():
        t = t.replace(f"[[{k}]]", str(v))
    return t


def chat(user, fmt=None, temperature=0.6):
    system = (PROMPTS / "systeme.txt").read_text(encoding="utf-8")
    payload = {"model": OLLAMA_MODEL, "stream": False, "think": False, "keep_alive": "10m",
               "options": {"num_ctx": OLLAMA_CTX, "temperature": temperature},
               "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    if fmt:
        payload["format"] = fmt
    r = http_json(OLLAMA_URL + "/api/chat", payload, timeout=1800)
    return re.sub(r"<think>.*?</think>", "", r["message"]["content"], flags=re.S).strip()


def unload():
    """Libère la VRAM pour l'étape suivante (voix / images)."""
    try:
        http_json(OLLAMA_URL + "/api/generate", {"model": OLLAMA_MODEL, "keep_alive": 0}, timeout=60)
    except Exception:
        pass


def parse_json(txt):
    m = re.search(r"\{.*\}", txt, flags=re.S)
    return json.loads(m.group(0)) if m else {}


def clean_narration(t):
    lines = []
    for ln in t.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#") or re.fullmatch(r"[-*_=]{3,}", ln):
            continue
        ln = re.sub(r"[*_`]+", "", ln)
        ln = re.sub(r"^(section|partie)\s*\d+.*?:\s*", "", ln, flags=re.I)
        lines.append(ln)
    return "\n".join(lines).strip()


def sources_text(p, limit=11000):
    """Budget réparti équitablement : chaque source garde sa part (avant, les 2 premières mangeaient tout)."""
    srcs = read_json(p / "sources.json")
    per = max(800, limit // max(1, len(srcs)))
    out = []
    for s in srcs:
        block = f"[{s['id']}] {s['title']} — {s['url'] or 'source fournie manuellement'}\n{s['extract']}"
        out.append(block[:per])
    return "\n\n".join(out)


def auto_checks(script, src):
    """Contrôle déterministe : tout nombre du script absent des sources est signalé (sans passer par le modèle)."""
    norm = lambda x: x.replace(",", ".").replace("\u202f", "").replace("\xa0", "")
    src_nums = {norm(n) for n in re.findall(r"\d+(?:[.,]\d+)?", src)}
    flags = []
    for sent in re.split(r"(?<=[.!?…])\s+", script.replace("\n", " ")):
        bad = [n for n in re.findall(r"\d+(?:[.,]\d+)?", re.sub(r"\[[^\]]*\]", "", sent)) if norm(n) not in src_nums]
        if bad:
            flags.append(f"- Nombre(s) {', '.join(bad)} absent(s) des sources : « {sent.strip()} »")
        elif "[À VÉRIFIER]" in sent:
            flags.append(f"- Marqué par le modèle : « {sent.strip()} »")
    return flags


def verify(script, src):
    """Vérification en 2 temps : contrôle automatique des nombres + revue du modèle paragraphe par paragraphe."""
    out = ["# Vérification du script", "", "## 1. Contrôle automatique (nombres absents des sources)", ""]
    out += auto_checks(script, src) or ["Aucun nombre suspect."]
    out += ["", "## 2. Revue paragraphe par paragraphe (modèle local, à prendre comme aide, pas comme preuve)", ""]
    for i, para in enumerate([x for x in script.split("\n\n") if x.strip()], 1):
        res = chat(prompt("verification.txt", SOURCES=src, SCRIPT=para), temperature=0.1)
        out += [f"### Paragraphe {i}", res.strip(), ""]
    return "\n".join(out)


def mode_script(vid):
    p = pdir(vid)
    brief = read_json(p / "brief.json")
    topic, target = brief["topic"], int(brief.get("target_words", 1100))
    src = sources_text(p)
    try:
        sections = parse_json(chat(prompt("plan.txt", SUJET=topic, SOURCES=src), fmt="json", temperature=0.4))["sections"]
        assert 3 <= len(sections) <= 10 and all("titre" in s and "objectif" in s for s in sections)
    except Exception:
        log("Plan non exploitable : plan par défaut utilisé")
        sections = DEFAULT_SECTIONS
    outline = "\n".join(f"{i}. {s['titre']} — {s['objectif']}" for i, s in enumerate(sections, 1))
    per, done = target // len(sections), ""
    for i, s in enumerate(sections, 1):
        log(f"Section {i}/{len(sections)} : {s['titre']}")
        txt = chat(prompt("section.txt", SUJET=topic, SOURCES=src, PLAN=outline, TITRE=s["titre"],
                          OBJECTIF=s["objectif"], MOTS=per, NUM=i, TOTAL=len(sections),
                          PRECEDENT=done[-700:] or "(début de la vidéo)"))
        done += ("\n\n" if done else "") + clean_narration(txt)
    (p / "script.md").write_text(done, encoding="utf-8")
    log(f"script.md : {len(done.split())} mots (cible {target})")
    log("Vérification des affirmations...")
    (p / "verification.md").write_text(verify(done, src), encoding="utf-8")
    unload()
    log("TERMINÉ. À FAIRE : relire script.md + verification.md, corriger, retirer tous les [À VÉRIFIER].")


def split_plans(text):
    sentences = re.split(r"(?<=[.!?…])\s+", re.sub(r"\[[^\]]*\]", "", text).replace("\n", " "))
    plans, cur = [], []
    for s in sentences:
        if not s.strip():
            continue
        cur.append(s.strip())
        if sum(len(x.split()) for x in cur) >= WORDS_PER_PLAN:
            plans.append(" ".join(cur)); cur = []
    if cur:
        if plans and len(" ".join(cur).split()) < 12:
            plans[-1] += " " + " ".join(cur)
        else:
            plans.append(" ".join(cur))
    return plans


def mode_storyboard(vid):
    p = pdir(vid)
    narrations = split_plans((p / "script.md").read_text(encoding="utf-8"))
    plans, prev = [], "(aucun)"
    for i, n in enumerate(narrations, 1):
        log(f"Plan {i}/{len(narrations)}")
        try:
            d = parse_json(chat(prompt("storyboard.txt", NARRATION=n, PRECEDENT=prev), fmt="json", temperature=0.7))
            img = d["image_prompt"].strip()
            assert len(img) > 15
        except Exception:
            log("  réponse invalide -> image générique")
            d, img = {}, "detailed mechanical engineering workshop, car engine on a stand, moody light"
        motion = d.get("motion") if d.get("motion") in MOTIONS else MOTIONS[(i - 1) % 4]
        plans.append({"id": i, "narration": n, "image_prompt": img, "motion": motion,
                      "on_screen_text": d.get("on_screen_text", "") or "", "image": f"plan_{i:03d}.png"})
        prev = img
    write_json(p / "storyboard.json", {"plans": plans})
    unload()
    log(f"storyboard.json : {len(plans)} plans")


def mode_metadata(vid):
    p = pdir(vid)
    brief, script = read_json(p / "brief.json"), (p / "script.md").read_text(encoding="utf-8")
    d = parse_json(chat(prompt("metadata.txt", SUJET=brief["topic"], SCRIPT=script), fmt="json", temperature=0.5))
    titles = [t for t in d.get("titles", []) if isinstance(t, str)]
    if not titles:
        raise SystemExit("Métadonnées invalides, relance l'étape.")
    srcs = ""
    if (p / "sources.json").exists():
        srcs = "\n\nSources :\n" + "\n".join(f"- {s['title']} {s['url']}".strip() for s in read_json(p / "sources.json") if s["url"])
    d["title"] = titles[0]
    d["description"] = (d.get("description", "") + srcs +
                        "\n\nNarration et illustrations générées par IA ; les images ne sont pas des photographies d'archives.")
    write_json(p / "metadata.json", d)
    unload()
    log(f"metadata.json : {d['title']}")


if __name__ == "__main__":
    mode, vid = sys.argv[1], sys.argv[2]
    {"script": mode_script, "storyboard": mode_storyboard, "metadata": mode_metadata}[mode](vid)
