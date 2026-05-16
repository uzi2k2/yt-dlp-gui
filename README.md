# yt-dlp-gui
A graphical interface for the command-line tool [yt-dlp](https://github.com/yt-dlp/yt-dlp), built with PyQt6.


## Features:
- Audio downloads (MP3 320kbps)
- Video downloads (MP4 merge)
- Playlist support
- Thumbnail extraction
- Metadata embedding
- Download queue system
- Progress tracking
- Cancel downloads
- Dark-themed UI
- Portable Windows releases


## Portable Release:
Prebuilt Windows versions are available in the [**Releases** section](https://github.com/uzi2k2/yt-dlp-gui/releases).
✔ No Python required  
✔ No setup required  
✔ FFmpeg included in release builds  


## Requirements (for running from source):
- [Python 3.11+](https://www.python.org/downloads/)
- Python dependencies listed in `requirements.txt`
- External dependency: FFmpeg (included in bin/ for local runs, bundled in release builds)


## Installation (Source):

### Option 1 — PowerShell:
```powershell
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
```

### Option 2 — Batch file (Windows double-click):
```bash
@echo off
cd %USERPROFILE%\Downloads

git clone https://github.com/uzi2k2/yt-dlp-gui
cd yt-dlp-gui

python -m venv .venv
call .venv\Scripts\activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo Setup complete!
pause
```

### Option 3 — Manual setup:
```powershell
git clone https://github.com/uzi2k2/yt-dlp-gui
cd yt-dlp-gui

python -m venv .venv
.\.venv\Scripts\activate

python -m pip install -r requirements.txt
python main.py
```

## Usage:
1. Download the application from the [releases](https://github.com/uzi2k2/yt-dlp-gui/releases) as a .zip and then extract it to your desired location. After which open the folder, and run the executable file inside the folder.
2. Choose output folder, which will be saved for your next download. You can also open "settings.ini" and change it from there (the settings.ini is created when choosing a new save file location and created in the root folder of the executable file).
3. Downloads:
- For Audio/Video/Image download, use single video URL(s) (not playlists or mixes), then add them to the queue with "+" button and click Download in the bottom right, to start downloading.
- For Playlist Audio/Playlist Video/Playlist Image downloads, use a playlist or mix URL, then add the link with "+" button and click Download in the bottom right, to start downloading.
Note: 
- Multiple URLs can be added (one per line using Enter).

## Notes
- .venv is not included in the repository
- FFmpeg is bundled in release builds and included in bin/ for local runs
- Save location settings are saved automatically in settings.ini
- This project is open-source and intended for educational and personal use.

## License:
Feel free to fork, modify, and improve this project.