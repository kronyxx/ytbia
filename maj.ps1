param([string]$Message = "")
$root = "C:\YouTubeIA"
Set-Location $root
$out = Join-Path $root "PROJET_COMPLET.txt"
$exclu = '\\(venv-asr|venv-tts|models|voices|logs|\.git|clips|output|images|audio|__pycache__)\\'
$bin = '.png','.wav','.mp4','.onnx','.safetensors','.pyc','.bak','.srt'
$tous = Get-ChildItem $root -Recurse -File | Where-Object { $_.FullName -notmatch $exclu -and $_.Extension -notin $bin -and $_.Name -notin 'PROJET_COMPLET.txt','timings.json' }
$sb = New-Object System.Text.StringBuilder
[void]$sb.AppendLine("===== EXPORT du " + (Get-Date -Format 'yyyy-MM-dd HH:mm') + " =====")
[void]$sb.AppendLine("===== ARBORESCENCE =====")
foreach ($f in $tous) { [void]$sb.AppendLine($f.FullName.Substring($root.Length + 1)) }
$texte = '.py','.ps1','.txt','.md','.json'
foreach ($f in ($tous | Where-Object { $_.Extension -in $texte })) {
  [void]$sb.AppendLine("")
  [void]$sb.AppendLine("===== " + $f.FullName.Substring($root.Length + 1) + " =====")
  [void]$sb.AppendLine((Get-Content $f.FullName -Raw -Encoding UTF8))
}
[IO.File]::WriteAllText($out, $sb.ToString(), (New-Object System.Text.UTF8Encoding($false)))
"{0:N0} Ko ecrits dans PROJET_COMPLET.txt" -f ((Get-Item $out).Length / 1KB)
if ($Message) { git add . ; git commit -m $Message ; git push }
