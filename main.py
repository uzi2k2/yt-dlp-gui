import os
import sys
import re
import subprocess
from dataclasses import dataclass

from PyQt6 import QtCore, QtWidgets
from PyQt6.QtWidgets import QAbstractItemView
from PyQt6.QtGui import QIcon

import yt_dlp


# ---------------- PATHS ----------------

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

BIN_DIR = os.path.join(BASE_DIR, "bin", "ffmpeg")

AUDIO_DIR = os.path.join(BASE_DIR, "Audios")
VIDEO_DIR = os.path.join(BASE_DIR, "Videos")
IMAGE_DIR = os.path.join(BASE_DIR, "Images")


# ---------------- HELPERS ----------------

ANSI = re.compile(r"\x1b\[[0-9;]*m")


def clean(text):
    return ANSI.sub("", text or "")


# ---------------- SANITIZE ----------------

def sanitize(url: str):

    url = url.strip()

    # REMOVE RADIO GARBAGE
    url = re.sub(r"&start_radio=[^&]+", "", url)

    return url


# ---------------- DIRS ----------------

def ensure_dirs():

    os.makedirs(AUDIO_DIR, exist_ok=True)
    os.makedirs(VIDEO_DIR, exist_ok=True)
    os.makedirs(IMAGE_DIR, exist_ok=True)


# ---------------- DATA ----------------

@dataclass
class QueueItem:
    url: str
    mode: str
    title: str = ""


# ---------------- DRAG & DROP LIST ----------------

class QueueList(QtWidgets.QListWidget):

    def __init__(self):

        super().__init__()

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

        self.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )

        self.setDragDropMode(
            QAbstractItemView.DragDropMode.InternalMove
        )


# ---------------- WORKER ----------------

class Worker(QtCore.QThread):

    log = QtCore.pyqtSignal(str)
    progress = QtCore.pyqtSignal(dict)
    done = QtCore.pyqtSignal(bool)

    def __init__(self, item: QueueItem):

        super().__init__()

        self.item = item
        self.stop_flag = False

    def stop(self):
        self.stop_flag = True

    # ---------------- PROGRESS ----------------

    def hook(self, d):

        if self.stop_flag:
            raise yt_dlp.utils.DownloadError("Cancelled")

        status = d.get("status")

        if status == "downloading":

            self.progress.emit({
                "pct": clean(d.get("_percent_str", "0%")).strip(),
                "speed": clean(d.get("_speed_str", "-")),
                "eta": clean(d.get("_eta_str", "-")),
            })

        elif status == "finished":

            self.log.emit("Finalizing file...")

    # ---------------- OPTIONS ----------------

    def base_opts(self):

        return {
            "windowsfilenames": True,
            "nooverwrites": False,

            "ffmpeg_location": BIN_DIR,

            "progress_hooks": [self.hook],

            "quiet": True,
            "no_warnings": False,

            "retries": 10,
            "fragment_retries": 10,

            "addmetadata": True,
            "embedmetadata": True,

            "writethumbnail": True,
        }

    # ---------------- RUN ----------------

    def run(self):

        try:

            url = sanitize(self.item.url)

            if self.item.mode == "Audio":

                ok = self.download_audio(url)

            elif self.item.mode == "Video":

                ok = self.download_video(url)

            elif self.item.mode == "Playlist Audio":

                ok = self.download_playlist_audio(url)

            elif self.item.mode == "Playlist Video":

                ok = self.download_playlist_video(url)

            else:

                ok = self.download_image(url)

            self.done.emit(ok)

        except Exception as e:

            self.log.emit(f"ERROR: {e}")

            self.done.emit(False)

    # ---------------- AUDIO ----------------

    def download_audio(self, url):

        try:

            opts = {
                **self.base_opts(),

                "noplaylist": True,

                "format": "bestaudio/best",

                "outtmpl": os.path.join(
                    AUDIO_DIR,
                    "%(title)s.%(ext)s"
                ),

                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "320",
                    },
                    {
                        "key": "FFmpegMetadata"
                    },
                    {
                        "key": "EmbedThumbnail"
                    },
                ],
            }

            with yt_dlp.YoutubeDL(opts) as ydl:

                ydl.download([url])

            return True

        except Exception as e:

            self.log.emit(str(e))

            return False

    # ---------------- VIDEO ----------------

    def download_video(self, url):

        try:

            opts = {
                **self.base_opts(),

                "noplaylist": True,

                "format": "bv*+ba/b",

                "merge_output_format": "mp4",

                "outtmpl": os.path.join(
                    VIDEO_DIR,
                    "%(title)s.%(ext)s"
                ),

                "postprocessors": [
                    {
                        "key": "FFmpegMetadata"
                    },
                    {
                        "key": "EmbedThumbnail"
                    },
                ],
            }

            with yt_dlp.YoutubeDL(opts) as ydl:

                ydl.download([url])

            return True

        except Exception as e:

            self.log.emit(str(e))

            return False

    # ---------------- PLAYLIST AUDIO ----------------

    def download_playlist_audio(self, url):

        try:

            opts = {
                **self.base_opts(),

                "noplaylist": False,

                "format": "bestaudio/best",

                "outtmpl": os.path.join(
                    AUDIO_DIR,
                    "%(playlist)s",
                    "%(playlist_index)s - %(title)s.%(ext)s"
                ),

                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "320",
                    },
                    {
                        "key": "FFmpegMetadata"
                    },
                    {
                        "key": "EmbedThumbnail"
                    },
                ],
            }

            with yt_dlp.YoutubeDL(opts) as ydl:

                ydl.download([url])

            return True

        except Exception as e:

            self.log.emit(str(e))

            return False

    # ---------------- PLAYLIST VIDEO ----------------

    def download_playlist_video(self, url):

        try:

            opts = {
                **self.base_opts(),

                "noplaylist": False,

                "format": "bv*+ba/b",

                "merge_output_format": "mp4",

                "outtmpl": os.path.join(
                    VIDEO_DIR,
                    "%(playlist)s",
                    "%(playlist_index)s - %(title)s.%(ext)s"
                ),

                "postprocessors": [
                    {
                        "key": "FFmpegMetadata"
                    },
                    {
                        "key": "EmbedThumbnail"
                    },
                ],
            }

            with yt_dlp.YoutubeDL(opts) as ydl:

                ydl.download([url])

            return True

        except Exception as e:

            self.log.emit(str(e))

            return False

    # ---------------- IMAGE ----------------

    def download_image(self, url):

        try:

            opts = {
                **self.base_opts(),

                "noplaylist": True,

                "skip_download": True,

                "outtmpl": os.path.join(
                    IMAGE_DIR,
                    "%(title)s.%(ext)s"
                ),

                "postprocessors": [
                    {
                        "key": "FFmpegThumbnailsConvertor",
                        "format": "webp",
                    }
                ],
            }

            with yt_dlp.YoutubeDL(opts) as ydl:

                ydl.download([url])

            return True

        except Exception as e:

            self.log.emit(str(e))

            return False


# ---------------- MAIN APP ----------------

class App(QtWidgets.QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("yt-dlp GUI - by uzi2k2")

        icon_path = os.path.join(BASE_DIR, "app_icon.ico")

        if os.path.exists(icon_path):

            self.setWindowIcon(QIcon(icon_path))

        self.queue = []

        self.worker = None
        self.current = None

        self.running = False

        self.done_count = 0
        self.fail_count = 0
        self.cancel_count = 0

        # ---------------- UI ----------------

        self.url = QtWidgets.QLineEdit()

        self.url.setPlaceholderText(
            "Paste URL"
        )

        self.mode = QtWidgets.QComboBox()

        self.mode.addItems([
            "Audio",
            "Video",
            "Image",
            "Playlist Audio",
            "Playlist Video"
        ])

        self.add_btn = QtWidgets.QPushButton("Add to Queue")

        self.start_btn = QtWidgets.QPushButton("Start Downloading Queue")

        self.clear_btn = QtWidgets.QPushButton(
            "Clear Queue"
        )

        self.cancel_btn = QtWidgets.QPushButton(
            "Cancel Queue"
        )

        self.update_btn = QtWidgets.QPushButton(
            "Update yt-dlp"
        )

        self.list = QueueList()

        self.progress = QtWidgets.QLabel(
            "Idle"
        )

        self.stats = QtWidgets.QLabel(
            "Done: 0 | Failed: 0 | Cancelled: 0"
        )

        # ---------------- LAYOUT ----------------

        layout = QtWidgets.QVBoxLayout(self)

        layout.addWidget(self.url)
        layout.addWidget(self.mode)

        layout.addWidget(self.add_btn)
        layout.addWidget(self.start_btn)
        layout.addWidget(self.clear_btn)
        layout.addWidget(self.cancel_btn)
        layout.addWidget(self.update_btn)

        layout.addWidget(self.list)

        layout.addWidget(self.progress)
        layout.addWidget(self.stats)

        # ---------------- SIGNALS ----------------

        self.add_btn.clicked.connect(
            self.add
        )

        self.start_btn.clicked.connect(
            self.start
        )

        self.clear_btn.clicked.connect(
            self.clear
        )

        self.cancel_btn.clicked.connect(
            self.cancel
        )

        self.update_btn.clicked.connect(
            self.update_ytdlp
        )

    # ---------------- FETCH TITLE ----------------

    def fetch_title(self, url, mode):

        # SKIP PLAYLIST PARSING

        if "Playlist" in mode:

            return url

        try:

            opts = {
                "quiet": True,
                "skip_download": True,
                "noplaylist": True,
            }

            with yt_dlp.YoutubeDL(opts) as ydl:

                info = ydl.extract_info(
                    url,
                    download=False
                )

                return info.get(
                    "title",
                    url
                )

        except:

            return url

    # ---------------- UPDATE BUTTON ----------------

    def update_ytdlp(self):

        self.progress.setText(
            "Updating yt-dlp..."
        )

        try:

            subprocess.call([
                sys.executable,
                "-m",
                "pip",
                "install",
                "-U",
                "yt-dlp"
            ])

            QtWidgets.QMessageBox.information(
                self,
                "Updated",
                "yt-dlp has been updated successfully! \n" 
                "Restarting the app is recommended."
            )

            self.progress.setText(
                "yt-dlp updated ✔"
            )

        except Exception as e:

            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                str(e)
            )

    # ---------------- ADD ----------------

    def add(self):

        url = sanitize(
            self.url.text()
        )

        if not url:
            return

        mode = self.mode.currentText()

        # PREVENT DUPLICATES

        for q in self.queue:

            if q.url == url and q.mode == mode:

                self.progress.setText(
                    "Already in queue — skipped"
                )

                return

        title = self.fetch_title(
            url,
            mode
        )

        item = QueueItem(
            url=url,
            mode=mode,
            title=title
        )

        self.queue.append(item)

        self.list.addItem(
            f"{item.mode} -> {title}"
        )

        self.progress.setText(
            "Added to queue ✔"
        )

        self.url.clear()

    # ---------------- CLEAR ----------------

    def clear(self):

        self.queue.clear()

        self.list.clear()

        self.progress.setText(
            "Queue cleared"
        )

    # ---------------- START ----------------

    def start(self):

        if self.running:
            return

        if not self.queue:
            return

        self.running = True

        self.next()

    # ---------------- NEXT ----------------

    def next(self):

        if not self.queue:

            self.running = False

            self.progress.setText(
                "Queue finished ✔"
            )

            return

        self.current = self.queue.pop(0)

        self.worker = Worker(
            self.current
        )

        self.worker.progress.connect(
            self.update_progress
        )

        self.worker.log.connect(
            self.progress.setText
        )

        self.worker.done.connect(
            self.finished
        )

        self.worker.start()

    # ---------------- PROGRESS ----------------

    def update_progress(self, d):

        self.progress.setText(
            f"{d['pct']} | "
            f"{d['speed']} | "
            f"ETA {d['eta']}"
        )

    # ---------------- FINISHED ----------------

    def finished(self, ok):

        if ok:

            self.done_count += 1

            self.list.addItem(
                "✔ Done"
            )

        else:

            self.fail_count += 1

            self.list.addItem(
                "✖ Failed"
            )

        self.stats.setText(
            f"Done: {self.done_count} | "
            f"Failed: {self.fail_count} | "
            f"Cancelled: {self.cancel_count}"
        )

        self.current = None

        self.next()

    # ---------------- CANCEL ----------------

    def cancel(self):

        if not self.worker:
            return

        if not self.running:
            return

        self.worker.stop()

        self.worker.terminate()

        self.cancel_count += 1

        self.stats.setText(
            f"Done: {self.done_count} | "
            f"Failed: {self.fail_count} | "
            f"Cancelled: {self.cancel_count}"
        )

        self.progress.setText(
            "Cancelled current download"
        )

        self.current = None

        self.next()


# ---------------- MAIN ----------------

if __name__ == "__main__":

    app = QtWidgets.QApplication(sys.argv)

    ensure_dirs()

    w = App()

    w.resize(900, 760)

    w.show()

    sys.exit(app.exec())
