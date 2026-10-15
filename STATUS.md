# Contexte : chaîne YouTube faceless 100 % IA locale (ingénierie automobile)

Dernière mise à jour : 2026-10-15

## Objectif
Chaîne YouTube en français, vidéos longues (~8 min), production automatisée, 0 € de logiciel, IA locale.
Première vidéo : « Pourquoi le poids d'une voiture change son comportement » (projet video_001).
PC : Windows 11, Ryzen 5 3600, RTX 3080 10 Go, 16 Go RAM (jamais Ollama et ComfyUI en même temps : géré par gestion_gpu.py).
Priorité : qualité avant vitesse. Je parle français, je suis débutant en ligne de commande : commandes PowerShell prêtes à copier-coller, correctifs courts.
Dépôt : https://github.com/kronyxx/ytbia (branche main, pas de --force). Mise à jour : git add . ; git commit -m "..." ; git push.
Repo local : C:\YouTubeIA. Python des scripts ASR : C:\YouTubeIA\venv-asr\Scripts\python.exe.

## Fait
- Installation complète : Ollama (qwen3:8b), Python 3.11, FFmpeg, Piper (fr_FR-tom-medium, variable PIPER_VOICE), faster-whisper GPU, ComfyUI portable (SDXL base 1.0).
- video_001 produite de bout en bout : sources, script, storyboard (19 plans), images, voix (audio.wav, timings.json), sous_titres.srt (122 lignes), assemblage.py (mp4 1080p, zoom/pan selon motion, sous-titres brûlés, option --test), metadata.json.
- gestion_gpu.py (modes ollama / comfy / libre), branché dans run_pipeline.py, fetch_sources.py, storyboard.py, images.py, sous_titres.py. Testé : fonctionne.
- fetch_sources.py modifié : 20 candidates / 8 gardées, titre exact tenté avant la recherche plein texte, prompt de requêtes orienté dynamique du véhicule.

## En cours : qualité de la collecte de sources
- Test avec requêtes générées par qwen3:8b : mauvais (Masse critique, Ceinture de sécurité, Fabrication de pneumatiques gardées). Le 8b est faible pour générer les requêtes et filtrer.
- Test manuel avec requêtes imposées dans brief.json (Dynamique du véhicule, Transfert de charge, Centre de gravité, Suspension de véhicule, Pneumatique (véhicule), Sous-virage, Survirage, Distance de freinage, Rapport poids/puissance, Moment d'inertie, Adhérence (mécanique), Aérodynamique automobile) : meilleur. Résultat du dernier essai à confirmer.
- Patch proposé : filtre mécanique par mots-clés (ancres modifiables dans brief.json, clé "ancres", au moins 3 occurrences). À confirmer qu'il est appliqué.

## Reste à faire
1. Script : l'IA l'écrit à partir d'une idée en une phrase (déclencheur futur de n8n).
   - Fiabiliser la collecte (filtre mots-clés, requêtes imposées ou qwen3:14b Q4 pour cette étape, repli Wikipédia EN si FR pauvre).
   - Viser d'abord 5-6 min de qualité avant 8 min (le script actuel fait 760 mots pour une cible de 1100).
2. Images : tester un checkpoint plus réaliste (RealVisXL, Juggernaut) ou FLUX GGUF, en gardant les noms plan_NNN.png.
3. Voix : tester Chatterbox Multilingual (licence MIT).
4. Miniature et métadonnées finales.
5. Vidéo pilote complète : mesurer la durée et les interventions manuelles.
6. n8n : collecte de sources + orchestration (run_pipeline.py video_NNN "idée" --phase a).
7. Tri des scripts en doublon dans scripts\.

## Points ouverts
- Origine du mot « copyright » : Whisper sur les silences (vad_filter), logos/© dans les images SDXL, ou symbole lu par Piper. Ligne exacte à relever.
- Vérifier les licences des modèles et des voix avant monétisation.
- Dépôt GitHub public ou privé à vérifier.
- La commande ollama n'est pas dans le PATH (Ollama marche quand même).

## Pour reprendre
Donne le lien du dépôt, la dernière sortie de terminal, et dis à quelle étape tu en es.
