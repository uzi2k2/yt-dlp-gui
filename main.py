import os
import sys
import subprocess
import shutil
import zipfile
from io import BytesIO

from PyQt6 import QtWidgets, QtCore
import requests

# ---------------- Paths ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(BASE_DIR, "bin")
FFMPEG_DIR = os.path.join(BIN_DIR, "ffmpeg")
FFMPEG_EXE = os.path.join(FFMPEG_DIR, "ffmpeg.exe")
DENO_EXE = os.path.expandvars(r"%USERPROFILE%\.deno\bin\deno.exe")

# ---------------- Dependency Check ----------------
def dependencies_installed():
    try:
        import PyQt6
        import requests
        # yt-dlp
        subprocess.run([sys.executable, "-m", "yt_dlp", "--version"], check=True, stdout=subprocess.DEVNULL)

        # FFmpeg: check normalized path + old extracted builds
        ffmpeg_paths = [FFMPEG_EXE]
        old_builds = [f for f in os.listdir(BIN_DIR) if f.startswith("ffmpeg") and "essentials_build" in f]
        for b in old_builds:
            ffmpeg_paths.append(os.path.join(BIN_DIR, b, "bin", "ffmpeg.exe"))
        ffmpeg_ok = any(os.path.exists(p) for p in ffmpeg_paths)
        if not ffmpeg_ok:
            return False
        subprocess.run([ffmpeg_paths[0], "-version"], check=True, stdout=subprocess.DEVNULL)

        # Deno
        if not os.path.exists(DENO_EXE):
            return False
        subprocess.run([DENO_EXE, "--version"], check=True, stdout=subprocess.DEVNULL)

        return True
    except Exception:
        return False

# ---------------- Install FFmpeg ----------------
def download_ffmpeg():
    if os.path.exists(FFMPEG_EXE):
        print("FFmpeg already installed, skipping...")
        return

    url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    os.makedirs(BIN_DIR, exist_ok=True)
    print("Downloading FFmpeg...")
    r = requests.get(url, stream=True)
    r.raise_for_status()
    z = zipfile.ZipFile(BytesIO(r.content))

    temp_dir = os.path.join(BIN_DIR, "ffmpeg_temp")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    z.extractall(temp_dir)

    # Find inner bin folder
    extracted_root = next(f for f in os.listdir(temp_dir) if f.startswith("ffmpeg"))
    extracted_bin = os.path.join(temp_dir, extracted_root, "bin")

    if os.path.exists(FFMPEG_DIR):
        shutil.rmtree(FFMPEG_DIR)
    shutil.move(extracted_bin, FFMPEG_DIR)
    shutil.rmtree(temp_dir, ignore_errors=True)
    print("FFmpeg installed!")

# ---------------- Install Deno ----------------
def install_deno():
    if os.path.exists(DENO_EXE):
        print("Deno already installed, skipping...")
        return
    print("Installing Deno...")
    subprocess.run([
        "powershell",
        "-ExecutionPolicy", "Bypass",
        "-Command",
        "iwr https://deno.land/install.ps1 -useb | iex"
    ], check=True)
    print("Deno installed!")

# ---------------- Install All Dependencies ----------------
def install_dependencies():
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"], check=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pyqt6"], check=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "requests"], check=True)
        download_ffmpeg()
        install_deno()

        QtWidgets.QMessageBox.information(None, "Restart", "Dependencies installed. Restarting app...")
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        QtWidgets.QMessageBox.critical(None, "Error", f"Failed to install dependencies:\n{e}")

# ---------------- Worker Thread ----------------
import yt_dlp

class DownloadWorker(QtCore.QThread):
    progress_signal = QtCore.pyqtSignal(str)
    finished_signal = QtCore.pyqtSignal(str)

    def __init__(self, url, output_folder="Audios"):
        super().__init__()
        self.url = url
        self.output_folder = output_folder

    def run(self):
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{self.output_folder}/%(title)s.%(ext)s',
            'quiet': True,
            'progress_hooks': [self.progress_hook],
            'writethumbnail': True,
            'postprocessors': [
                {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '320'},
                {'key': 'EmbedThumbnail', 'already_have_thumbnail': False},
                {'key': 'FFmpegMetadata'},
            ],
            'convert-thumbnails': 'jpg',
            'ignoreerrors': True,
            'no_warnings': True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            self.finished_signal.emit(f"Download finished: {self.url}")
        except Exception as e:
            self.finished_signal.emit(f"Error: {str(e)}")

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            self.progress_signal.emit(f"Downloading: {d.get('_percent_str', '')} {d.get('filename', '')}")
        elif d['status'] == 'finished':
            self.progress_signal.emit(f"Converting/Finishing: {d.get('filename', '')}")

# ---------------- Main Window ----------------
class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YT-DLP GUI Launcher")
        self.setGeometry(300, 200, 600, 400)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.url_input = QtWidgets.QLineEdit(self)
        self.url_input.setPlaceholderText("Enter URL here")
        self.layout.addWidget(self.url_input)

        self.download_btn = QtWidgets.QPushButton("Download Audio (320 kbps)")
        self.layout.addWidget(self.download_btn)
        self.download_btn.clicked.connect(self.start_download)

        self.log_area = QtWidgets.QTextEdit(self)
        self.log_area.setReadOnly(True)
        self.layout.addWidget(self.log_area)

    def start_download(self):
        url = self.url_input.text().strip()
        if not url:
            self.log_area.append("Status: Please enter a URL")
            return

        self.log_area.append(f"Ready to download: {url}")
        output_folder = "Audios"
        QtCore.QDir().mkpath(output_folder)

        self.worker = DownloadWorker(url, output_folder)
        self.worker.progress_signal.connect(self.update_log)
        self.worker.finished_signal.connect(self.download_finished)
        self.worker.start()

    def update_log(self, message):
        self.log_area.append(message)

    def download_finished(self, message):
        self.log_area.append(message)
        self.log_area.append("-----")

# ---------------- App Startup ----------------
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    if not dependencies_installed():
        win = QtWidgets.QWidget()
        win.setWindowTitle("Setup Required")
        layout = QtWidgets.QVBoxLayout()
        label = QtWidgets.QLabel("Some dependencies are missing.\nClick the button to install everything.")
        button = QtWidgets.QPushButton("Install Everything")
        button.clicked.connect(install_dependencies)
        layout.addWidget(label)
        layout.addWidget(button)
        win.setLayout(layout)
        win.show()
    else:
        win = MainWindow()
        win.show()

    sys.exit(app.exec())
