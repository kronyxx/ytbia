"""Crée le dossier d'une vidéo.  Usage: new_project.py video_001 "Sujet de la vidéo" """
import sys, datetime
from config import *

vid = sys.argv[1]
topic = " ".join(sys.argv[2:]).strip() or vid
p = pdir(vid)
for d in ("sources", "audio", "images", "clips", "output"):
    (p / d).mkdir(parents=True, exist_ok=True)
brief = p / "brief.json"
if not brief.exists():
    write_json(brief, {"video_id": vid, "topic": topic, "target_words": 1100,
                       "queries": [topic], "created": datetime.date.today().isoformat()})
log(f"Projet prêt : {p}")
log("Astuce : ajoute des fichiers .txt/.md dans sources/ (docs constructeur, articles) : ils seront ajoutés aux sources.")
