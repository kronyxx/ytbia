# Contexte : chaîne YouTube faceless 100 % IA locale (ingénierie automobile)

## Objectif
Chaîne YouTube en français, vidéos longues (~8 min), production automatisée, 0 € de logiciel, IA locale.
Première vidéo : « Pourquoi le poids d'une voiture change son comportement » (projet `video_001`).
PC : Windows 11, Ryzen 5 3600, RTX 3080 10 Go, 16 Go RAM (RAM serrée : jamais Ollama et ComfyUI en même temps).
Priorité : qualité avant vitesse. Je parle français, je suis débutant en ligne de commande : donne des commandes PowerShell prêtes à copier-coller et des correctifs courts.

## Dépôt GitHub
https://github.com/kronyxx/ytbia (branche `main`).
Git configuré dans C:\YouTubeIA avec l'identité `kronyxx` / `kronyxx@users.noreply.github.com` (locale au dépôt).
`.gitignore` exclut : venv-tts, venv-asr, voices, models, logs, *.onnx, *.safetensors, *.wav, *.mp4, *.png, projects/*/images, projects/*/audio.
Mise à jour : `git add . ; git commit -m "..." ; git push`. Pas de `--force`. Visibilité public/privé à vérifier.

## Installation (faite)
Racine `C:\YouTubeIA` (scripts, prompts, workflows, voices, projects, logs, models).
- Ollama + qwen3:8b ; Python ; FFmpeg ; Node.js ; 7-Zip.
- `venv-tts` (Piper), `venv-asr` (faster-whisper + nvidia-cublas-cu12 + nvidia-cudnn-cu12). Piper n'est installé que dans venv-tts : lancer voix.py avec `.\venv-tts\Scripts\python.exe`, sinon « No module named piper ».
- ComfyUI portable : `C:\ComfyUI\ComfyUI_windows_portable` (SDXL base 1.0, API http://127.0.0.1:8188). Le .bat utilise des chemins relatifs : `cd C:\ComfyUI\ComfyUI_windows_portable ; .\run_nvidia_gpu.bat`.
- Voix : `fr_FR-tom-medium` dans `C:\YouTubeIA\voices` ; la variable d'env `PIPER_VOICE` contient le chemin complet du .onnx (voix.py accepte nom ou chemin). Piste : voix plus naturelle (Chatterbox Multilingual, licence MIT), pas testée.
- La commande `ollama` n'est pas dans le PATH de mon terminal (Ollama marche quand même).

## Pipeline (ordre d'exécution)
1. `run_pipeline.py video_001 "<sujet>" --phase a` : sources Wikipédia, script.md, verification.md. Faite : 5 sources hors sujet voiture, script de 760 mots (cible 1100), qualité médiocre, acceptée pour l'instant. Erreurs HTTP 429 sur 2 requêtes.
2. `storyboard.py video_001` : storyboard.json (liste de 19 plans).
3. `images.py video_001` : images\plan_NNN.png via ComfyUI (ComfyUI lancé, Ollama déchargé). 19 images générées.
4. `.\venv-tts\Scripts\python.exe scripts\voix.py video_001` : un wav Piper par plan, audio.wav, timings.json, texte_sous_titres.txt. Voix validée à l'écoute.
5. `.\venv-asr\Scripts\python.exe scripts\sous_titres.py projects\video_001\audio.wav projects\video_001\texte_sous_titres.txt projects\video_001\sous_titres.srt` : .srt généré (modèle medium).
6. `python scripts\assemblage.py video_001` : clips avec zoom/pan selon `motion`, voix normalisée, sous-titres brûlés, output\final.mp4. Lancé, résultat à vérifier.

## Scripts de `C:\YouTubeIA\scripts\`
Écrits par Claude (Python, stdlib sauf Whisper/Piper) :
- `storyboard.py` : script.md → storyboard.json (plans ~38 mots ; image_prompt EN, motion zoom_in/zoom_out/pan_left/pan_right, on_screen_text), Ollama think:false, anti-doublons, décharge le modèle à la fin.
- `images.py` : storyboard.json → plan_NNN.png (1344x768, seed 1000+id, STYLE et NEGATIF communs, 60 mots max, reprise possible : supprimer un png pour le régénérer).
- `voix.py` : un wav Piper par plan, audio.wav (0,35 s de silence entre plans), timings.json, texte_sous_titres.txt ; prononciation.json appliqué à la voix seulement.
- `sous_titres.py` : texte exact du script + temps Whisper (alignement difflib), repli CPU.
- `assemblage.py` : remplace montage.py (lit storyboard liste, timings.json, audio.wav, sous_titres.srt).
Anciens, probablement doublons à trier : `run_pipeline.py`, `config.py`, `fetch_sources.py`, `new_project.py`, `ollama_gen.py`, `comfy_gen.py`, `tts_piper.py`, `subtitles.py`, `qc.py`, `00_install_tout.ps1`, `01_setup.ps1`, `workflows/n8n_pipeline.json`.
`montage.py` : OBSOLÈTE, incompatible avec le format actuel (attend storyboard en dict, narration.wav, subtitles.srt). Ne plus l'utiliser.

## Prompts (`C:\YouTubeIA\prompts`)
systeme, plan, section, verification, storyboard, metadata, sujets, prononciation.json. Règles : aucun fait inventé, citations [S#] à retirer avant la voix, écrire court plutôt qu'inventer.
Limites : verification.txt manque d'un verdict « RAISONNEMENT » et produit des doublons ; qwen3:8b est répétitif avec peu de sources.

## Problèmes résolus (ne pas rechercher à nouveau)
- Le mot « copyright » dans l'audio/transcription : Piper, lancé en sous-processus sous Windows, lisait le texte en cp1252 ; chaque accent devenait « Ã© », lu « A tilde copyright ». Corrigé dans voix.py avec `env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}`. Ce n'était ni le script, ni le storyboard, ni prononciation.json, ni les images.
- PowerShell affiche mal l'UTF-8 (« Ã§ ») : toujours vérifier avec `Get-Content fichier -Encoding UTF8` avant de conclure qu'un fichier est abîmé.
- Négatif SDXL renforcé (text, letters, words, caption, signature, copyright, watermark, logo, badge, emblem, license plate...).

## Points ouverts
- Images SDXL « pas folles » : améliorer STYLE, checkpoint réaliste (RealVisXL/Juggernaut) ou FLUX GGUF. Remplaçable sans toucher au reste tant que les fichiers s'appellent plan_NNN.png. Les image_prompt dépassent parfois 60 mots (coupés) et SDXL tronque à ~77 tokens : prévoir des prompts plus courts dans storyboard.py.
- Vérifier les licences des modèles et voix avant monétisation.
- Tri des scripts en doublon dans `scripts\`.

## Prochaines étapes
1. Vérifier final.mp4 : synchro images/voix, taille des sous-titres (FontSize dans assemblage.py), zooms fluides.
2. Métadonnées + miniature (metadata.txt).
3. Vidéo pilote complète : mesurer durée et interventions manuelles.
4. Améliorer script (sources sur le sujet, éventuellement rédaction par un modèle plus fort), images, voix.
5. n8n : collecte de sources (gérer le 429, requêtes précises) et orchestration.

Pour reprendre : donne le lien du dépôt (ou joins les scripts), la dernière sortie de terminal et dis-moi à quelle étape tu en es.