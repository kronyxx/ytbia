# Contexte : chaîne YouTube faceless 100 % IA locale (ingénierie automobile)

## Objectif
Chaîne YouTube en français, vidéos longues (~8 min), production automatisée, 0 € de logiciel, IA locale.
Première vidéo : « Pourquoi le poids d'une voiture change son comportement » (projet `video_001`).
PC : Windows 11, Ryzen 5 3600, RTX 3080 10 Go, 16 Go RAM (jamais Ollama et ComfyUI en même temps).
Priorité : qualité avant vitesse. Je parle français, je suis débutant en ligne de commande : commandes PowerShell prêtes à copier-coller, correctifs courts, un seul bloc à la fois.

## Dépôt GitHub
https://github.com/kronyxx/ytbia (branche `main`). Identité git locale : `kronyxx` / `kronyxx@users.noreply.github.com`.
`.gitignore` exclut : venv-tts, venv-asr, voices, models, logs, *.onnx, *.safetensors, *.wav, *.mp4, *.png, projects/*/images, projects/*/audio.
Mise à jour : `git add . ; git commit -m "..." ; git push`. Jamais `--force`. Visibilité public/privé à vérifier.
Les avertissements « LF will be replaced by CRLF » sont normaux.

## Installation (faite)
- Racine `C:\YouTubeIA` (scripts, prompts, workflows, voices, projects, logs, models).
- Ollama + qwen3:8b (la commande `ollama` n'est pas dans le PATH du terminal, mais ça marche) ; Python ; FFmpeg ; Node.js ; 7-Zip.
- `venv-tts` (Piper) et `venv-asr` (faster-whisper + cublas/cudnn). Piper n'existe QUE dans venv-tts : toujours lancer `voix.py` avec `.\venv-tts\Scripts\python.exe`, sinon « No module named piper ».
- ComfyUI portable `C:\ComfyUI\ComfyUI_windows_portable` (SDXL base 1.0, API http://127.0.0.1:8188). Le .bat utilise des chemins relatifs : `cd C:\ComfyUI\ComfyUI_windows_portable ; .\run_nvidia_gpu.bat`, fenêtre à laisser ouverte.
- Voix `fr_FR-tom-medium` dans `C:\YouTubeIA\voices`, variable d'env `PIPER_VOICE` = chemin complet du .onnx. Piste : Chatterbox Multilingual (MIT), non testée.

## Pipeline (ordre d'exécution, depuis C:\YouTubeIA)
1. `python scripts\run_pipeline.py video_001 "<sujet>" --phase a` : sources Wikipédia, script.md, verification.md. Fait, qualité médiocre (5 sources hors sujet voiture, 760 mots pour 1100 visés, erreurs 429).
2. `python scripts\storyboard.py video_001` : storyboard.json (liste de 19 plans). Ollama doit tourner, ComfyUI fermé.
3. `python scripts\images.py video_001` : images\plan_NNN.png (ComfyUI ouvert, Ollama déchargé). Reprise possible : supprimer un png pour le régénérer. FAIT (19 images).
4. `.\venv-tts\Scripts\python.exe scripts\voix.py video_001` : un wav par plan, audio.wav, timings.json, texte_sous_titres.txt. FAIT, voix validée à l'écoute.
5. `.\venv-asr\Scripts\python.exe scripts\sous_titres.py projects\video_001\audio.wav projects\video_001\texte_sous_titres.txt projects\video_001\sous_titres.srt` (modèle medium). FAIT.
6. `python scripts\assemblage.py video_001` : clips zoom/pan selon `motion`, voix normalisée, sous-titres brûlés, `projects\video_001\output\final.mp4`. Script écrit ; résultat final.mp4 À VÉRIFIER (synchro images/voix, taille des sous-titres via FontSize dans assemblage.py, fluidité des zooms).

## Scripts de `scripts\`
Écrits par Claude (Python, stdlib sauf Whisper/Piper) : `storyboard.py`, `images.py` (1344x768, seed 1000+id, STYLE/NEGATIF communs, 60 mots max), `voix.py` (0,35 s de silence entre plans, prononciation.json appliqué à la voix seulement), `sous_titres.py` (texte exact du script + temps Whisper par alignement difflib), `assemblage.py`.
Anciens, probablement doublons à trier : `run_pipeline.py`, `config.py`, `fetch_sources.py`, `new_project.py`, `ollama_gen.py`, `comfy_gen.py`, `tts_piper.py`, `subtitles.py`, `qc.py`, `00_install_tout.ps1`, `01_setup.ps1`, `workflows/n8n_pipeline.json`.
`montage.py` : OBSOLÈTE (attend storyboard en dict, narration.wav, subtitles.srt). Ne plus l'utiliser.

## Prompts (`prompts\`)
systeme, plan, section, verification, storyboard, metadata, sujets, prononciation.json. Règles : aucun fait inventé, citations [S#] retirées avant la voix, écrire court plutôt qu'inventer. Limites : verification.txt sans verdict « RAISONNEMENT » et avec doublons ; qwen3:8b répétitif avec peu de sources.

## Problèmes résolus (ne pas rechercher à nouveau)
- « copyright » dans l'audio : Piper, lancé en sous-processus sous Windows, lisait le texte en cp1252 ; chaque accent devenait « Ã© », lu « A tilde copyright ». Corrigé dans voix.py avec `env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}`. Ce n'était ni le script, ni le storyboard, ni prononciation.json, ni les images.
- PowerShell affiche mal l'UTF-8 (« Ã§ ») : vérifier avec `Get-Content fichier -Encoding UTF8` avant de conclure qu'un fichier est abîmé.
- Négatif SDXL renforcé (text, letters, words, caption, signature, copyright, watermark, logo, badge, emblem, license plate...).

## Points ouverts
- Images SDXL « pas folles » : améliorer STYLE, checkpoint réaliste (RealVisXL/Juggernaut) ou FLUX GGUF ; remplaçable sans toucher au reste tant que les fichiers s'appellent plan_NNN.png. Certains image_prompt dépassent 60 mots (coupés) et SDXL tronque vers 77 tokens : demander des prompts plus courts dans storyboard.py.
- Script faible : sources hors sujet voiture, à refaire avec de meilleures sources.
- Vérifier les licences des modèles et voix avant monétisation.
- Trier les scripts en doublon.

## Prochaines étapes
1. Vérifier final.mp4 et ajuster (sous-titres, zooms, durée).
2. Métadonnées + miniature (prompts\metadata.txt).
3. Vidéo pilote complète : mesurer durée et interventions manuelles.
4. Améliorer script (sources pertinentes, rédaction plus solide), images, voix.
5. n8n : collecte de sources (gérer le 429, requêtes précises) et orchestration.

## Pour reprendre dans une nouvelle conversation
Donne le lien du dépôt, la dernière sortie de terminal et dis à quelle étape tu en es.