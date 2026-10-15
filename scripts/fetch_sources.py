"""Collecte de VRAIES sources -> sources.json (Wikipédia FR + fichiers que tu déposes dans sources/).
Le modèle ne reçoit que ces extraits : il ne doit rien inventer en dehors.

Améliorations :
 - si brief.json -> "queries" n'a pas été personnalisé (== le sujet brut), le modèle propose
   lui-même des termes de recherche précis (ex: « énergie cinétique », « distance de freinage ») ;
 - chaque page candidate est jugée par le modèle : les pages trop générales ou hors sujet
   (ex: « Automobile », un film) sont écartées et listées dans le journal ;
 - tes fichiers .txt/.md déposés dans sources/ passent TOUJOURS en premier et ne sont jamais filtrés.
Pour forcer tes propres requêtes : édite brief.json -> "queries".
Pour désactiver le filtre : brief.json -> "filter": false."""
import sys, datetime
from urllib.parse import urlencode
from config import *
from ollama_gen import chat, parse_json, unload

MAX_CANDIDATES, MAX_KEEP = 14, 5
vid = sys.argv[1]
p = pdir(vid)
brief_path = p / "brief.json"
brief = read_json(brief_path)
topic = brief["topic"]
API = "https://fr.wikipedia.org/w/api.php?"
today = datetime.date.today().isoformat()

# 1) Requêtes -------------------------------------------------------------------------------
queries = [q for q in (brief.get("queries") or []) if q.strip()]
if not queries or queries == [topic]:
    log("Requêtes non personnalisées : le modèle propose des termes de recherche précis...")
    try:
        d = parse_json(chat(
            f"Sujet d'une vidéo documentaire : « {topic} ».\n"
            "Propose 6 requêtes de recherche pour Wikipédia FR qui trouvent des articles de FOND "
            "(lois physiques, grandeurs, mécanismes, données chiffrées) utiles pour traiter ce sujet. "
            "Chaque requête = 1 à 4 mots, un concept précis (ex: « énergie cinétique »). "
            "Pas de phrase, pas de sujet trop général comme « automobile ».\n"
            'Réponds UNIQUEMENT par un JSON : {"queries":["...","..."]}', fmt="json", temperature=0.3))
        queries = [q.strip() for q in d.get("queries", []) if isinstance(q, str) and q.strip()][:6]
    except Exception as e:
        log(f"Génération des requêtes impossible : {e}")
    if not queries:
        queries = [topic]
    brief["queries"] = queries
    write_json(brief_path, brief)          # visible et modifiable par toi
log("Requêtes : " + " | ".join(queries))

# 2) Candidats Wikipédia ----------------------------------------------------------------------
cands, seen = [], set()
for q in queries:
    try:
        r = http_json(API + urlencode({"action": "query", "list": "search", "srsearch": q,
                                       "srlimit": 4, "format": "json"}), timeout=30)
    except Exception as e:
        log(f"Recherche impossible pour « {q} » : {e}")
        continue
    for hit in r.get("query", {}).get("search", []):
        title = hit["title"]
        if title in seen or len(cands) >= MAX_CANDIDATES:
            continue
        seen.add(title)
        try:
            dd = http_json(API + urlencode({"action": "query", "prop": "extracts|info", "titles": title,
                                            "explaintext": 1, "exchars": 5000, "inprop": "url",
                                            "format": "json", "redirects": 1}), timeout=30)
            page = next(iter(dd["query"]["pages"].values()))
            text = (page.get("extract") or "").strip()
            if len(text) > 300 and "peut désigner" not in text[:250]:
                cands.append({"type": "wikipedia", "title": page["title"], "url": page.get("fullurl", ""),
                              "retrieved": today, "extract": text, "query": q})
        except Exception as e:
            log(f"Page ignorée ({title}) : {e}")
log(f"{len(cands)} pages candidates")

# 3) Filtre de pertinence ---------------------------------------------------------------------
kept = cands
if cands and brief.get("filter", True):
    listing = "\n".join(f"{i}. {c['title']} — {c['extract'][:350].replace(chr(10), ' ')}" for i, c in enumerate(cands, 1))
    try:
        d = parse_json(chat(
            f"Sujet de la vidéo : « {topic} ».\n\nPages candidates :\n{listing}\n\n"
            f"Garde au maximum {MAX_KEEP} pages dont le contenu apporte des FAITS utiles pour expliquer ce sujet "
            "(lois physiques, grandeurs, mécanismes, données). Rejette : pages trop générales (ex: « Automobile »), "
            "pages hors sujet (films, personnes, lieux, politique), pages qui ne parlent du sujet qu'en passant.\n"
            'Réponds UNIQUEMENT par un JSON : {"keep":[numéros]}', fmt="json", temperature=0.1))
        ids = [int(x) for x in d.get("keep", []) if str(x).isdigit() and 1 <= int(x) <= len(cands)]
        if ids:
            kept = [cands[i - 1] for i in dict.fromkeys(ids)][:MAX_KEEP]
        else:
            log("Filtre : aucune page jugée pertinente.")
            kept = []
    except Exception as e:
        log(f"Filtre indisponible ({e}) : toutes les pages sont gardées.")
    for c in cands:
        log(("  + gardée   : " if c in kept else "  - écartée  : ") + c["title"])
unload()

# 4) Assemblage : fichiers manuels d'abord ------------------------------------------------------
sources = []
for f in sorted((p / "sources").glob("*")):
    if f.suffix.lower() in (".txt", ".md"):
        sources.append({"type": "manuel", "title": f.name, "url": "", "retrieved": today,
                        "extract": f.read_text(encoding="utf-8", errors="replace")[:6000]})
sources += [{k: v for k, v in c.items() if k != "query"} for c in kept]
for i, s in enumerate(sources, 1):
    s["id"] = f"S{i}"
write_json(p / "sources.json", sources)
log(f"{len(sources)} sources enregistrées dans sources.json : " + "; ".join(f"{s['id']}={s['title']}" for s in sources))
if not sources:
    log("ERREUR : aucune source pertinente. Précise brief.json -> queries ou dépose des fichiers dans sources/.")
    sys.exit(1)
if len(sources) < 2:
    log("ATTENTION : une seule source. Le script risque d'être court ; ajoute des fichiers dans sources/.")
