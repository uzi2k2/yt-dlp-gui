$target = "$env:USERPROFILE\Downloads\yt-dlp-gui"

cd $env:USERPROFILE\Downloads

if (Test-Path $target) {
    Remove-Item -Recurse -Force $target
}

git clone https://github.com/uzi2k2/yt-dlp-gui

cd yt-dlp-gui

python -m venv .venv
.\.venv\Scripts\activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Write-Host "Setup complete. Run: python main.py"