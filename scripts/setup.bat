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