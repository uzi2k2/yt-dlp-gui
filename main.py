import os
import sys
import re
from PyQt6 import QtCore, QtWidgets
import yt_dlp

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, "Audios")
VIDEO_DIR = os.path.join(BASE_DIR, "Videos")


class DownloadWorker(QtCore.QThread):
    log = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def __init__(self, url, mode):
        super().__init__()
        self.url = url
        self.mode = mode

    def run(self):
        try:
            if self.mode == "audio":
                self.download_audio()
            else:
                self.download_video()
        finally:
            self.finished.emit()

    def hook(self, d):
        if d["status"] == "downloading":
            p = re.sub(r"\x1b\[[0-9;]*m", "", d.get("_percent_str", ""))
            self.log.emit(f"Downloading… {p.strip()}")
        elif d["status"] == "finished":
            self.log.emit("Finalizing file...")

    def download_audio(self):
        os.makedirs(AUDIO_DIR, exist_ok=True)

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(AUDIO_DIR, "%(title)s.%(ext)s"),
            "windowsfilenames": True,
            "nooverwrites": True,
            "writethumbnail": True,
            "addmetadata": True,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "320",
                },
                {"key": "EmbedThumbnail"},
            ],
            "postprocessor_args": {
                "FFmpegExtractAudio": ["-vn", "-ab", "320k"]
            },
            "progress_hooks": [self.hook],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([self.url])

    def download_video(self):
        os.makedirs(VIDEO_DIR, exist_ok=True)

        ydl_opts = {
            "format": "bv*+ba/b",
            "merge_output_format": "mp4",
            "outtmpl": os.path.join(VIDEO_DIR, "%(title)s.%(ext)s"),
            "windowsfilenames": True,
            "nooverwrites": True,
            "writethumbnail": True,
            "addmetadata": True,
            "postprocessors": [
                {"key": "EmbedThumbnail"},
            ],
            "progress_hooks": [self.hook],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([self.url])


class App(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("yt-dlp GUI")

        self.url = QtWidgets.QLineEdit()
        self.url.setPlaceholderText("Paste URL here")

        self.audio_btn = QtWidgets.QPushButton("Download Audio (MP3 320)")
        self.video_btn = QtWidgets.QPushButton("Download Video (Best)")

        self.log = QtWidgets.QTextEdit()
        self.log.setReadOnly(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.url)
        layout.addWidget(self.audio_btn)
        layout.addWidget(self.video_btn)
        layout.addWidget(self.log)

        self.audio_btn.clicked.connect(lambda: self.start("audio"))
        self.video_btn.clicked.connect(lambda: self.start("video"))

    def start(self, mode):
        if not self.url.text().strip():
            return
        self.worker = DownloadWorker(self.url.text().strip(), mode)
        self.worker.log.connect(self.log.append)
        self.worker.start()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = App()
    w.show()
    sys.exit(app.exec())
