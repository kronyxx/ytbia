# État du projet : chaîne YouTube faceless IA locale

Dernière mise à jour : 2026-10-15

## Fait

- Installation complète : Ollama (qwen3:8b), Python 3.11, FFmpeg, Piper (voix fr_FR-tom-medium), faster-whisper (GPU), ComfyUI portable + SDXL base 1.0.
- Pipeline de production de video_001, de bout en bout :
  - Phase A : sources Wikipédia, script.md, verification.md.
  - storyboard.py : 19 plans, prompts d'images variés.
  - images.py : images générées (plan_NNN.png).
  - voix.py : audio.wav, timings.json, texte_sous_titres.txt.
  - sous_titres.py : sous_titres.srt (122 sous-titres, texte exact du script, temps Whisper).
  - assemblage.py : vidéo mp4 1080p (zoom/pan selon motion, voix, sous-titres brûlés), option --test pour 3 plans.
  - metadata.json produit.
- Collecte de sources améliorée : requêtes imposables dans brief.json, filtre de pertinence, retry sur les 429 (le test avec des requêtes de dynamique automobile a gardé Dynamique du véhicule, Aérodynamique automobile, Centre de gravité).
- gestion_gpu.py : un seul gros programme à la fois. Mode ollama (coupe ComfyUI), comfy (décharge Ollama, lance ComfyUI), libre (coupe les deux). Branché dans run_pipeline.py et les scripts lancés à la main.

## À vérifier

- Que le branchement de gestion_gpu fonctionne (tester : python -c "import gestion_gpu; gestion_gpu.mode('comfy')" puis mode('ollama')).
- Qualité réelle de la voix et des images sur la vidéo complète.
- Doublons de scripts dans scripts\ (montage.py, tts_piper.py, subtitles.py, comfy_gen.py, ollama_gen.py : anciens ou nouveaux selon l'étape).
- Dépôt GitHub public ou privé.
- Licences des modèles et des voix avant monétisation.
- Origine du mot « copyright » signalé : Whisper sur les silences (activer vad_filter), logos/© dans les images SDXL (renforcer le négatif), ou symbole lu par Piper. Ligne exacte à relever.

## Reste à faire

1. Script : l'IA l'écrit à partir d'une simple idée.
   - Essayer d'abord le titre exact de la page Wikipédia avant la recherche plein texte.
   - Passer MAX_KEEP à 8 et MAX_CANDIDATES à 20.
   - Prompt de requêtes centré sur la dynamique du véhicule (masse, inertie, suspension, pneus, freinage).
   - Repli sur Wikipédia EN si le FR est pauvre.
   - Tester qwen3:14b (Q4) à la place de qwen3:8b.
   - Viser 5 à 6 minutes de qualité avant d'allonger à 8 minutes.
2. Images : tester un checkpoint plus réaliste (RealVisXL, Juggernaut) ou FLUX GGUF, en gardant les noms plan_NNN.png.
3. Voix : tester Chatterbox Multilingual (licence MIT).
4. Miniature et métadonnées finales.
5. Vidéo pilote complète : mesurer la durée totale et le nombre d'interventions manuelles.
6. n8n : collecte de sources et orchestration, déclenchées par une idée en une phrase (run_pipeline.py video_NNN "idée" --phase a).
7. Tri des scripts en doublon.
