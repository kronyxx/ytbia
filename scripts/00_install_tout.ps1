# Installation complète du studio YouTube IA (Windows 11, RTX 3080 10 Go, 16 Go RAM).
# Relançable sans risque : chaque étape est ignorée si elle est déjà faite.
# Usage, depuis le dossier du kit décompressé (PowerShell, sans droits admin) :
#   powershell -ExecutionPolicy Bypass -File .\kit\scripts\00_install_tout.ps1
$ErrorActionPreference = "Continue"
$Root  = "C:\YouTubeIA"
$Kit   = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)   # dossier "kit"
$Comfy = "C:\ComfyUI"
$Results = [ordered]@{}

function Step($name, $block) {
    Write-Host "`n=== $name ===" -ForegroundColor Cyan
    try { & $block; $script:Results[$name] = "OK" }
    catch { Write-Host "ERREUR : $_" -ForegroundColor Red; $script:Results[$name] = "ECHEC : $_" }
}
function RefreshPath {
    $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
}
function Have($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
function WingetInstall($id) {
    winget install --id $id -e --accept-package-agreements --accept-source-agreements --silent
    RefreshPath
}

Step "Dossiers + copie du kit" {
    foreach ($d in "scripts","prompts","workflows","voices","projects","logs","models") {
        New-Item -ItemType Directory -Force -Path "$Root\$d" | Out-Null }
    foreach ($d in "scripts","prompts","workflows") { Copy-Item "$Kit\$d\*" "$Root\$d" -Recurse -Force }
}

Step "GPU NVIDIA" { nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader }
Step "winget"     { if (-not (Have winget)) { throw "winget absent : installe 'App Installer' depuis le Microsoft Store" } }
Step "FFmpeg"     { if (-not (Have ffmpeg)) { WingetInstall "Gyan.FFmpeg.Essentials" }; ffmpeg -version | Select-Object -First 1 }
Step "Python 3.11" { if (-not (Get-Command py -ErrorAction SilentlyContinue) -or -not (py -3.11 --version 2>$null)) { WingetInstall "Python.Python.3.11" }; py -3.11 --version }
Step "Node.js LTS" { if (-not (Have node)) { WingetInstall "OpenJS.NodeJS.LTS" }; node --version }
Step "7-Zip"       { if (-not (Test-Path "C:\Program Files\7-Zip\7z.exe")) { WingetInstall "7zip.7zip" } }
Step "Ollama"      { if (-not (Have ollama)) { WingetInstall "Ollama.Ollama" }; ollama --version }

Step "Modèle qwen3:8b (~5 Go)" {
    if (-not (Have ollama)) { throw "Ollama introuvable : ferme/rouvre PowerShell puis relance ce script" }
    Start-Sleep 3
    ollama pull qwen3:8b
}

Step "Venv voix (Piper)" {
    $py = "$Root\venv-tts\Scripts\python.exe"
    if (-not (Test-Path $py)) { py -3.11 -m venv "$Root\venv-tts" }
    & $py -m pip install --upgrade pip
    & $py -m pip install piper-tts
    & $py -m piper.download_voices fr_FR-siwis-medium --data-dir "$Root\voices"
    if (-not (Test-Path "$Root\voices\fr_FR-siwis-medium.onnx")) { throw "voix absente : vérifie le nom dans le catalogue Piper puis règle PIPER_VOICE" }
}

Step "Venv sous-titres (faster-whisper)" {
    $py = "$Root\venv-asr\Scripts\python.exe"
    if (-not (Test-Path $py)) { py -3.11 -m venv "$Root\venv-asr" }
    & $py -m pip install --upgrade pip
    & $py -m pip install faster-whisper
}

Step "ComfyUI portable (~2-3 Go)" {
    if (-not (Test-Path "$Comfy\ComfyUI_windows_portable")) {
        New-Item -ItemType Directory -Force -Path $Comfy | Out-Null
        $arc = "$Comfy\comfyui.7z"
        Invoke-WebRequest "https://github.com/comfyanonymous/ComfyUI/releases/latest/download/ComfyUI_windows_portable_nvidia.7z" -OutFile $arc
        & "C:\Program Files\7-Zip\7z.exe" x $arc "-o$Comfy" -y | Out-Null
        Remove-Item $arc
    }
}

Step "Checkpoint SDXL Base 1.0 (~6,9 Go)" {
    $dir = Get-ChildItem "$Comfy" -Recurse -Directory -Filter checkpoints -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $dir) { throw "dossier models\checkpoints introuvable : place le fichier à la main" }
    $f = Join-Path $dir.FullName "sd_xl_base_1.0.safetensors"
    if (-not (Test-Path $f) -or (Get-Item $f).Length -lt 6GB) {
        Invoke-WebRequest "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors" -OutFile $f
    }
}

Step "Variables d'environnement" { setx COMFY_URL "http://127.0.0.1:8188" | Out-Null }

Write-Host "`n================ RÉSUMÉ ================" -ForegroundColor Cyan
foreach ($k in $Results.Keys) {
    $c = if ($Results[$k] -eq "OK") { "Green" } else { "Red" }
    Write-Host ("{0,-38} {1}" -f $k, $Results[$k]) -ForegroundColor $c
}
Write-Host "`nSi une ligne est en échec : corrige, puis relance ce même script. Ensuite lis la suite dans le README."
