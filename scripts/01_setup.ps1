# Étape 1 — Prépare les dossiers et VÉRIFIE chaque outil. Ne modifie rien d'autre.
# powershell -ExecutionPolicy Bypass -File .\01_setup.ps1
$Root = "C:\YouTubeIA"
foreach ($d in "scripts","prompts","workflows","voices","projects","logs","models") { New-Item -ItemType Directory -Force -Path "$Root\$d" | Out-Null }
function Check($name, $block) {
    try { $out = & $block 2>&1 | Select-Object -First 3; Write-Host "[OK]     $name" -ForegroundColor Green; $out | ForEach-Object { Write-Host "         $_" } }
    catch { Write-Host "[MANQUE] $name" -ForegroundColor Red }
}
Write-Host "`n=== Vérification de l'environnement ===`n"
Check "GPU NVIDIA" { nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader }
Check "winget"     { winget --version }
Check "FFmpeg"     { ffmpeg -version }
Check "FFprobe"    { ffprobe -version }
Check "Python 3.11" { py -3.11 --version }
Check "Ollama"     { ollama --version }
Check "Node.js (n8n)" { node --version }
Write-Host ("`nEspace libre C: {0} Go (visé : 100+) | RAM : {1} Go" -f [math]::Round((Get-PSDrive C).Free/1GB), [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB))
Write-Host "Copie ensuite les dossiers scripts, prompts, workflows du kit dans $Root."
