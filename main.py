import os
import sys
import re
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtGui import QIcon
import yt_dlp

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BIN_DIR = os.path.join(BASE_DIR, "bin", "ffmpeg")
FFMPEG_PATH = os.path.join(BIN_DIR, "ffmpeg.exe")
FFPROBE_PATH = os.path.join(BIN_DIR, "ffprobe.exe")
ATOMIC_PATH = os.path.join(BIN_DIR, "AtomicParsley.exe")

AUDIO_DIR = os.path.join(BASE_DIR, "Audios")
VIDEO_DIR = os.path.join(BASE_DIR, "Videos")
IMAGE_DIR = os.path.join(BASE_DIR, "Images")


def check_dependencies():
    missing = []
    for name, path in {
        "ffmpeg.exe": FFMPEG_PATH,
        "ffprobe.exe": FFPROBE_PATH,
        "AtomicParsley.exe": ATOMIC_PATH,
    }.items():
        if not os.path.isfile(path):
            missing.append(name)

    try:
        import mutagen  # noqa
        import PIL  # noqa
    except Exception:
        missing.append("python packages (mutagen / pillow)")

    if missing:
        QtWidgets.QMessageBox.critical(
            None,
            "Missing dependencies",
            "Missing:\n\n" + "\n".join(missing),
        )
        sys.exit(1)


class DownloadWorker(QtCore.QThread):
    log = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal(str)

    def __init__(self, url, mode):
        super().__init__()
        self.url = url
        self.mode = mode

    def run(self):
        try:
            if self.mode == "audio":
                self.download_audio()
            elif self.mode == "video":
                self.download_video()
            elif self.mode == "image":
                self.download_image()
            self.finished.emit("Done ✔")
        except Exception as e:
            self.finished.emit(f"Error: {e}")

    def hook(self, d):
        if d["status"] == "downloading":
            p = re.sub(r"\x1b\[[0-9;]*m", "", d.get("_percent_str", ""))
            self.log.emit(f"Downloading… {p.strip()}")
        elif d["status"] == "finished":
            self.log.emit("Finalizing file...")

    def base_opts(self):
        return {
            "windowsfilenames": True,
            "nooverwrites": True,
            "ffmpeg_location": BIN_DIR,
            "progress_hooks": [self.hook],
            "addmetadata": True,
            "embedmetadata": True,
            "writedescription": False,
        }

    def download_audio(self):
        os.makedirs(AUDIO_DIR, exist_ok=True)

        ydl_opts = {
            **self.base_opts(),
            "format": "bestaudio/best",
            "outtmpl": os.path.join(AUDIO_DIR, "%(title)s.%(ext)s"),
            "writethumbnail": True,
            "postprocessors": [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "320"},
                {"key": "FFmpegMetadata"},
                {"key": "EmbedThumbnail"},
            ],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([self.url])

    def download_video(self):
        os.makedirs(VIDEO_DIR, exist_ok=True)

        ydl_opts = {
            **self.base_opts(),
            "format": "bv*+ba/b",
            "merge_output_format": "mp4",
            "outtmpl": os.path.join(VIDEO_DIR, "%(title)s.%(ext)s"),
            "writethumbnail": True,
            "postprocessors": [
                {"key": "FFmpegMetadata"},
                {"key": "EmbedThumbnail"},
            ],
            # Ensure correct upload date
            "dateafter": None,
        }

        # Workaround to correctly extract upload date as YYYY
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(self.url, download=False)
            if "upload_date" in info and len(info["upload_date"]) >= 8:
                info["upload_date"] = info["upload_date"][:4]  # keep only year
            ydl.download([self.url])

    def download_image(self):
        os.makedirs(IMAGE_DIR, exist_ok=True)

        ydl_opts = {
            **self.base_opts(),
            "skip_download": True,
            "writethumbnail": True,
            "outtmpl": os.path.join(IMAGE_DIR, "%(title)s.%(ext)s"),
            "postprocessors": [
                {"key": "FFmpegMetadata"},  # embed metadata into thumbnail
            ],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([self.url])


class App(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("yt-dlp GUI")
        self.setWindowIcon(QIcon(os.path.join(BASE_DIR, "app_icon.ico")))

        self.url = QtWidgets.QLineEdit()
        self.url.setPlaceholderText("Paste URL here")

        self.audio_btn = QtWidgets.QPushButton("Download Audio (MP3 320)")
        self.video_btn = QtWidgets.QPushButton("Download Video (Best)")
        self.image_btn = QtWidgets.QPushButton("Download Thumbnail (.webp)")

        self.log = QtWidgets.QTextEdit()
        self.log.setReadOnly(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.url)
        layout.addWidget(self.audio_btn)
        layout.addWidget(self.video_btn)
        layout.addWidget(self.image_btn)
        layout.addWidget(self.log)

        self.audio_btn.clicked.connect(lambda: self.start("audio"))
        self.video_btn.clicked.connect(lambda: self.start("video"))
        self.image_btn.clicked.connect(lambda: self.start("image"))

    def start(self, mode):
        if not self.url.text().strip():
            return
        self.worker = DownloadWorker(self.url.text().strip(), mode)
        self.worker.log.connect(self.log.append)
        self.worker.finished.connect(self.log.append)
        self.worker.start()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    check_dependencies()
    w = App()
    w.show()
    sys.exit(app.exec())
