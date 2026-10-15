"""Un seul gros programme à la fois sur le GPU/RAM : Ollama OU ComfyUI."""
import subprocess, time, json, urllib.request
from pathlib import Path

COMFY_DIR = Path(r"C:\ComfyUI\ComfyUI_windows_portable")
COMFY_URL = "http://127.0.0.1:8188/system_stats"
OLLAMA = "http://127.0.0.1:11434"


def _up(url):
    try:
        urllib.request.urlopen(url, timeout=3)
        return True
    except Exception:
        return False


def stop_comfy():
    ps = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*ComfyUI*' "
          "-and $_.Name -like 'python*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True)
    time.sleep(3)


def stop_ollama():
    try:
        d = json.load(urllib.request.urlopen(OLLAMA + "/api/ps", timeout=5))
        for m in d.get("models", []):
            req = urllib.request.Request(OLLAMA + "/api/generate",
                data=json.dumps({"model": m["name"], "keep_alive": 0}).encode(),
                headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=30).read()
    except Exception:
        pass
    time.sleep(2)


def start_comfy():
    if _up(COMFY_URL):
        return
    print("[gpu] demarrage de ComfyUI...")
    subprocess.Popen([str(COMFY_DIR / "run_nvidia_gpu.bat")], cwd=COMFY_DIR,
                     creationflags=subprocess.CREATE_NEW_CONSOLE)
    for _ in range(90):
        if _up(COMFY_URL):
            print("[gpu] ComfyUI pret")
            return
        time.sleep(2)
    raise SystemExit("ComfyUI ne repond pas apres 3 minutes.")


def mode(nom):
    """'ollama' : coupe ComfyUI. 'comfy' : decharge Ollama et lance ComfyUI. 'libre' : coupe les deux."""
    if nom == "ollama":
        stop_comfy()
    elif nom == "comfy":
        stop_ollama()
        start_comfy()
    else:
        stop_comfy()
        stop_ollama()
    print(f"[gpu] mode {nom}")
