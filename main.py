import os
import re
import sys

from dataclasses import dataclass

import yt_dlp

from PyQt6 import QtCore, QtWidgets
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)


# =========================================================
# PATHS
# =========================================================

if getattr(sys, "frozen", False):

    BASE_DIR = os.path.dirname(sys.executable)

    # IMPORTANT FOR PYINSTALLER
    INTERNAL_DIR = getattr(sys, "_MEIPASS", BASE_DIR)

else:

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    INTERNAL_DIR = BASE_DIR


# =========================================================
# RESOURCE PATHS
# =========================================================

def resource_path(relative_path):

    if hasattr(sys, "_MEIPASS"):

        return os.path.join(
            sys._MEIPASS,
            relative_path
        )

    return os.path.join(
        BASE_DIR,
        relative_path
    )


# =========================================================
# FFMPEG PATHS
# =========================================================

FFMPEG_DIR = os.path.join(
    INTERNAL_DIR,
    "bin",
    "ffmpeg"
)

FFMPEG_EXE = os.path.join(
    FFMPEG_DIR,
    "ffmpeg.exe"
)

FFPROBE_EXE = os.path.join(
    FFMPEG_DIR,
    "ffprobe.exe"
)

ATOMICPARSLEY_EXE = os.path.join(
    FFMPEG_DIR,
    "AtomicParsley.exe"
)

DEFAULT_DOWNLOAD_DIR = os.path.join(
    os.path.expanduser("~"),
    "Downloads",
    "YT-DLP-Downloads"
)

SETTINGS_FILE = os.path.join(
    BASE_DIR,
    "settings.ini"
)

os.makedirs(DEFAULT_DOWNLOAD_DIR, exist_ok=True)


# =========================================================
# SETTINGS
# =========================================================

settings = QtCore.QSettings(
    SETTINGS_FILE,
    QtCore.QSettings.Format.IniFormat
)


def get_download_dir():

    path = settings.value(
        "download_dir",
        DEFAULT_DOWNLOAD_DIR
    )

    os.makedirs(path, exist_ok=True)

    return path


def set_download_dir(path):

    settings.setValue(
        "download_dir",
        path
    )


# =========================================================
# HELPERS
# =========================================================

ANSI = re.compile(r"\x1b\[[0-9;]*m")


def clean(text):

    return ANSI.sub("", text or "")


def sanitize(url):

    url = url.strip()

    url = re.sub(
        r"&start_radio=[^&]+",
        "",
        url
    )

    return url


def safe_playlist_name(name):

    if not name:
        return "Unknown Playlist"

    invalid = r'<>:"/\\|?*'

    for ch in invalid:
        name = name.replace(ch, "_")

    return name.strip()


# =========================================================
# DATA
# =========================================================

@dataclass
class QueueItem:

    url: str
    mode: str
    row: int
    title: str = ""
    is_playlist: bool = False


# =========================================================
# TITLE WORKER
# =========================================================

class TitleWorker(QtCore.QThread):

    done = QtCore.pyqtSignal(
        int,
        str,
        bool
    )

    def __init__(self, row, url, mode):

        super().__init__()

        self.row = row
        self.url = url
        self.mode = mode

    def run(self):

        is_playlist_mode = "Playlist" in self.mode

        title = self.url
        is_playlist = is_playlist_mode

        try:

            opts = {
                "quiet": True,
                "skip_download": True,
                "extract_flat": True,
                "noplaylist": not is_playlist_mode,
                "no_warnings": True,
            }

            with yt_dlp.YoutubeDL(opts) as ydl:

                info = ydl.extract_info(
                    self.url,
                    download=False
                )

                if info:

                    if info.get("_type") == "playlist":

                        playlist_title = info.get(
                            "title",
                            "Unknown Playlist"
                        )

                        title = safe_playlist_name(
                            playlist_title
                        )

                        is_playlist = True

                    else:

                        title = info.get(
                            "title",
                            self.url
                        )

        except Exception:
            pass

        self.done.emit(
            self.row,
            title,
            is_playlist
        )


# =========================================================
# DOWNLOAD WORKER
# =========================================================

class DownloadWorker(QtCore.QThread):

    progress = QtCore.pyqtSignal(
        int,
        float,
        str,
        str
    )

    status = QtCore.pyqtSignal(
        int,
        str
    )

    finished_download = QtCore.pyqtSignal(
        int,
        bool,
        str
    )

    def __init__(self, item, save_dir):

        super().__init__()

        self.item = item
        self.save_dir = save_dir

        self.stop_flag = False

    # =====================================================

    def stop(self):

        self.stop_flag = True

        try:
            self.requestInterruption()
        except Exception:
            pass

    # =====================================================

    def hook(self, d):

        if self.stop_flag or self.isInterruptionRequested():

            raise Exception("CANCELLED_BY_USER")

        status = d.get("status")

        if status == "downloading":

            percent = clean(
                d.get("_percent_str", "0%")
            ).replace("%", "").strip()

            try:
                percent = float(percent)
            except Exception:
                percent = 0

            speed = clean(
                d.get("_speed_str", "-")
            )

            eta = clean(
                d.get("_eta_str", "-")
            )

            self.progress.emit(
                self.item.row,
                percent,
                speed,
                eta
            )

        elif status == "finished":

            self.status.emit(
                self.item.row,
                "Finalizing..."
            )

    # =====================================================

    def base_opts(self):

        opts = {
            "windowsfilenames": True,
            "nooverwrites": False,

            # IMPORTANT
            "ffmpeg_location": FFMPEG_DIR,

            "progress_hooks": [self.hook],

            "quiet": True,
            "no_warnings": True,

            "retries": 10,
            "fragment_retries": 10,

            "addmetadata": True,
            "embedmetadata": True,

            "writethumbnail": True,

            "ignoreerrors": False,
        }

        # FORCE EXECUTABLE PATHS
        if os.path.exists(FFMPEG_EXE):
            opts["ffmpeg_location"] = FFMPEG_DIR

        return opts

    # =====================================================

    def playlist_template(self):

        return os.path.join(
            self.save_dir,
            "%(playlist)s",
            "%(playlist_index)03d - %(title)s.%(ext)s"
        )

    # =====================================================

    def run(self):

        try:

            url = sanitize(self.item.url)

            mode = self.item.mode

            # =================================================
            # AUDIO
            # =================================================

            if mode == "Audio":

                opts = {
                    **self.base_opts(),

                    "noplaylist": True,

                    "format": "bestaudio/best",

                    "outtmpl": os.path.join(
                        self.save_dir,
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

            elif mode == "Video":

                opts = {
                    **self.base_opts(),

                    "noplaylist": True,

                    "format": "bv*+ba/b",

                    "merge_output_format": "mp4",

                    "outtmpl": os.path.join(
                        self.save_dir,
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

            elif mode == "Image":

                opts = {
                    **self.base_opts(),

                    "noplaylist": True,

                    "skip_download": True,

                    "outtmpl": os.path.join(
                        self.save_dir,
                        "%(title)s.%(ext)s"
                    ),

                    "postprocessors": [
                        {
                            "key": "FFmpegThumbnailsConvertor",
                            "format": "webp",
                        }
                    ],
                }

            elif mode == "Playlist Audio":

                opts = {
                    **self.base_opts(),

                    "noplaylist": False,
                    "extract_flat": False,

                    "format": "bestaudio/best",

                    "outtmpl": self.playlist_template(),

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

            elif mode == "Playlist Video":

                opts = {
                    **self.base_opts(),

                    "noplaylist": False,
                    "extract_flat": False,

                    "format": "bv*+ba/b",

                    "merge_output_format": "mp4",

                    "outtmpl": self.playlist_template(),

                    "postprocessors": [
                        {
                            "key": "FFmpegMetadata"
                        },
                        {
                            "key": "EmbedThumbnail"
                        },
                    ],
                }

            elif mode == "Playlist Image":

                opts = {
                    **self.base_opts(),

                    "noplaylist": False,
                    "extract_flat": False,

                    "skip_download": True,

                    "outtmpl": self.playlist_template(),

                    "postprocessors": [
                        {
                            "key": "FFmpegThumbnailsConvertor",
                            "format": "webp",
                        }
                    ],
                }

            else:
                return

            if not os.path.exists(FFMPEG_EXE):

                self.finished_download.emit(
                    self.item.row,
                    False,
                    f"ffmpeg.exe not found:\n{FFMPEG_EXE}"
                )

                return

            with yt_dlp.YoutubeDL(opts) as ydl:

                ydl.download([url])

            self.finished_download.emit(
                self.item.row,
                True,
                "Finished"
            )

        except Exception as e:

            error_text = str(e)

            if (
                self.stop_flag
                or "CANCELLED_BY_USER" in error_text
            ):

                self.finished_download.emit(
                    self.item.row,
                    False,
                    "Cancelled"
                )

                return

            self.finished_download.emit(
                self.item.row,
                False,
                error_text
            )


# =========================================================
# MAIN WINDOW
# =========================================================

class App(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            "yt-dlp GUI - by uzi2k2"
        )

        self.resize(1250, 720)

        icon_path = resource_path(
            "app_icon.ico"
        )

        if os.path.exists(icon_path):

            self.setWindowIcon(
                QIcon(icon_path)
            )

        self.queue = []

        self.current_worker = None

        self.done_count = 0
        self.fail_count = 0
        self.cancel_count = 0

        self.running = False

        self.build_ui()

    # =====================================================

    def build_ui(self):

        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: white;
                font-size: 14px;
            }

            QPlainTextEdit,
            QLineEdit,
            QComboBox {
                background-color: #2a2a2a;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                padding: 6px;
            }

            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                padding: 6px 12px;
            }

            QPushButton:hover {
                background-color: #3a3a3a;
            }

            QTableWidget {
                background-color: #232323;
                border: 1px solid #3c3c3c;
                gridline-color: #2f2f2f;
            }

            QHeaderView::section {
                background-color: #2b2b2b;
                padding: 6px;
                border: none;
            }

            QProgressBar {
                border: 1px solid #444;
                border-radius: 5px;
                text-align: center;
                background-color: #2b2b2b;
            }

            QProgressBar::chunk {
                background-color: #00aa55;
                border-radius: 5px;
            }
        """)

        main_layout = QVBoxLayout(self)

        params_box = QGroupBox("Parameters")

        params_layout = QGridLayout()

        self.url_input = QPlainTextEdit()

        self.url_input.setPlaceholderText(
            "Paste one or multiple URLs..."
        )

        self.url_input.setFixedHeight(78)

        self.path_input = QtWidgets.QLineEdit()

        self.path_input.setText(
            get_download_dir()
        )

        self.path_input.setFixedHeight(32)

        self.browse_btn = QPushButton(
            "Browse..."
        )

        self.mode_combo = QComboBox()

        self.mode_combo.addItems([
            "Audio",
            "Video",
            "Image",
            "Playlist Audio",
            "Playlist Video",
            "Playlist Image",
        ])

        self.add_btn = QPushButton("+")

        params_layout.addWidget(QLabel("Video URL(s)"), 0, 0)
        params_layout.addWidget(self.url_input, 0, 1, 1, 4)

        params_layout.addWidget(QLabel("Save to"), 1, 0)
        params_layout.addWidget(self.path_input, 1, 1)
        params_layout.addWidget(self.browse_btn, 1, 2)
        params_layout.addWidget(self.mode_combo, 1, 3)
        params_layout.addWidget(self.add_btn, 1, 4)

        params_box.setLayout(params_layout)

        main_layout.addWidget(params_box)

        downloads_group = QGroupBox("Downloads")

        downloads_layout = QVBoxLayout(downloads_group)

        self.table = QTableWidget()

        self.table.setColumnCount(6)

        self.table.setHorizontalHeaderLabels([
            "Title",
            "Mode",
            "Progress",
            "Status",
            "Speed",
            "ETA",
        ])

        self.table.verticalHeader().setVisible(False)

        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )

        self.table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )

        header = self.table.horizontalHeader()

        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.Stretch
        )

        downloads_layout.addWidget(self.table)

        main_layout.addWidget(downloads_group)

        bottom_frame = QFrame()

        bottom_layout = QHBoxLayout(bottom_frame)

        self.clear_btn = QPushButton("🗑 Clear")
        self.cancel_btn = QPushButton("✖ Cancel")
        self.download_btn = QPushButton("⬇ Download")

        self.stats_label = QLabel(
            "Done: 0 | Failed: 0 | Cancelled: 0"
        )

        bottom_layout.addWidget(self.clear_btn)
        bottom_layout.addWidget(self.cancel_btn)
        bottom_layout.addWidget(self.stats_label)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.download_btn)

        main_layout.addWidget(bottom_frame)

        self.browse_btn.clicked.connect(self.browse)
        self.add_btn.clicked.connect(self.add_to_queue)
        self.download_btn.clicked.connect(self.start_queue)
        self.clear_btn.clicked.connect(self.clear_queue)
        self.cancel_btn.clicked.connect(self.cancel_current)

    def browse(self):

        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Download Folder",
            self.path_input.text()
        )

        if folder:

            self.path_input.setText(folder)

            set_download_dir(folder)

    def add_to_queue(self):

        text = self.url_input.toPlainText().strip()

        if not text:
            return

        urls = [
            sanitize(u)
            for u in text.splitlines()
            if u.strip()
        ]

        mode = self.mode_combo.currentText()

        for url in urls:

            row = self.table.rowCount()

            self.table.insertRow(row)

            self.table.setItem(
                row,
                0,
                QTableWidgetItem("Fetching title...")
            )

            self.table.setItem(
                row,
                1,
                QTableWidgetItem(mode)
            )

            progress = QProgressBar()

            progress.setValue(0)

            self.table.setCellWidget(
                row,
                2,
                progress
            )

            self.table.setItem(
                row,
                3,
                QTableWidgetItem("Queued")
            )

            self.table.setItem(
                row,
                4,
                QTableWidgetItem("-")
            )

            self.table.setItem(
                row,
                5,
                QTableWidgetItem("-")
            )

            item = QueueItem(
                url=url,
                mode=mode,
                row=row
            )

            self.queue.append(item)

            title_worker = TitleWorker(
                row,
                url,
                mode
            )

            title_worker.done.connect(
                self.set_title
            )

            title_worker.start()

            item._title_worker = title_worker

        self.url_input.clear()

    def set_title(
        self,
        row,
        title,
        is_playlist
    ):

        display = (
            f"📂 {title}"
            if is_playlist
            else title
        )

        self.table.setItem(
            row,
            0,
            QTableWidgetItem(display)
        )

    def start_queue(self):

        if self.running:
            return

        if not self.queue:
            return

        self.running = True

        self.download_next()

    def download_next(self):

        if not self.queue:

            self.running = False

            return

        item = self.queue.pop(0)

        save_dir = self.path_input.text().strip()

        if not save_dir:
            save_dir = get_download_dir()

        os.makedirs(save_dir, exist_ok=True)

        self.current_worker = DownloadWorker(
            item,
            save_dir
        )

        self.current_worker.progress.connect(
            self.update_progress
        )

        self.current_worker.status.connect(
            self.update_status
        )

        self.current_worker.finished_download.connect(
            self.download_finished
        )

        self.update_status(
            item.row,
            "Starting"
        )

        self.current_worker.start()

    def update_progress(
        self,
        row,
        percent,
        speed,
        eta
    ):

        progress = self.table.cellWidget(row, 2)

        if progress:
            progress.setValue(int(percent))

        self.table.item(row, 4).setText(speed)
        self.table.item(row, 5).setText(eta)

    def update_status(self, row, text):

        self.table.item(row, 3).setText(text)

    def download_finished(
        self,
        row,
        ok,
        message
    ):

        self.cancel_btn.setEnabled(True)

        if ok:

            self.done_count += 1

            self.update_status(row, "Done")

            bar = self.table.cellWidget(row, 2)

            if bar:
                bar.setValue(100)

        else:

            if message == "Cancelled":

                self.cancel_count += 1

                self.update_status(
                    row,
                    "Cancelled"
                )

            else:

                self.fail_count += 1

                self.update_status(
                    row,
                    f"Failed: {message}"
                )

        self.stats_label.setText(
            f"Done: {self.done_count} | "
            f"Failed: {self.fail_count} | "
            f"Cancelled: {self.cancel_count}"
        )

        self.current_worker = None

        QtCore.QTimer.singleShot(
            300,
            self.download_next
        )

    def cancel_current(self):

        if not self.current_worker:
            return

        self.current_worker.stop()

        self.update_status(
            self.current_worker.item.row,
            "Cancelling..."
        )

        self.cancel_btn.setEnabled(False)

    def clear_queue(self):

        if self.running:

            QMessageBox.warning(
                self,
                "Busy",
                "Cannot clear while downloading."
            )

            return

        self.queue.clear()

        self.table.setRowCount(0)


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    app = QApplication(sys.argv)

    app_icon = resource_path(
        "app_icon.ico"
    )

    if os.path.exists(app_icon):

        app.setWindowIcon(
            QIcon(app_icon)
        )

    window = App()

    window.show()

    sys.exit(app.exec())
