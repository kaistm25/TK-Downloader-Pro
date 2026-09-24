#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup.py - TK Downloader Pro v1.2.0 (VERSION FINALE)
=====================================================
Script auto-contenu : génère, installe, vérifie et lance tout le projet.
"""

import os
import sys
import ast
import shutil
import subprocess
import platform
import urllib.request
import zipfile
import logging
import argparse
import venv
import traceback
from pathlib import Path
from datetime import datetime

# ==================== CONFIGURATION ====================

APP_NAME = "TK Downloader Pro"
APP_VERSION = "1.2.0"
SRC_DIR = Path("src")
VENV_DIR = Path("venv")
ICON_FILE = "icon.ico"
STARTUP_LOG = Path("startup_error.log")

ARIA2_VERSION = "1.37.0"
ARIA2_URL_WIN = (
    f"https://github.com/aria2/aria2/releases/download/"
    f"release-{ARIA2_VERSION}/aria2-{ARIA2_VERSION}-win-64bit-build1.zip"
)

REQUIRED_PACKAGES = {
    "PyQt5>=5.15.0": "PyQt5",
    "aria2p>=0.12.0": "aria2p",
    "pytubefix>=10.0.0": "pytubefix",
    "yt-dlp>=2024.0.0": "yt_dlp",
    "requests>=2.30.0": "requests",
}

# ==================== LOGGER ====================

class ColoredFormatter(logging.Formatter):
    COLORS = {'DEBUG': '\033[36m', 'INFO': '\033[32m', 'WARNING': '\033[33m',
              'ERROR': '\033[31m', 'CRITICAL': '\033[35m'}
    RESET, BOLD = '\033[0m', '\033[1m'

    def format(self, record):
        c = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{c}{self.BOLD}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logger():
    logger = logging.getLogger("setup")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    ch = logging.StreamHandler()
    ch.setFormatter(ColoredFormatter('%(levelname)s | %(message)s'))
    logger.addHandler(ch)
    Path("build_logs").mkdir(exist_ok=True)
    fh = logging.FileHandler(
        Path("build_logs") / f"setup_{datetime.now():%Y%m%d_%H%M%S}.log",
        encoding='utf-8')
    fh.setFormatter(logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s'))
    logger.addHandler(fh)
    return logger


LOG = setup_logger()


def banner(text):
    LOG.info("=" * 70)
    LOG.info(f"  {text}")
    LOG.info("=" * 70)


def run(cmd, check=True, capture=False, env=None):
    return subprocess.run(cmd, check=check, capture_output=capture, text=True,
                          encoding='utf-8', errors='replace', shell=False, env=env)


def write_startup_log(msg):
    try:
        with open(STARTUP_LOG, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*70}\n{datetime.now().isoformat()}\n{msg}\n")
    except Exception:
        pass


# ============================================================================
# VÉRIFICATIONS SYNTAXIQUES
# ============================================================================

def check_python_syntax(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        ast.parse(source, filename=str(file_path))
        return True, None
    except SyntaxError as e:
        err = (f"SyntaxError dans {file_path}\n"
               f"  Ligne {e.lineno}, col {e.offset}\n"
               f"  Code: {e.text.strip() if e.text else 'N/A'}\n"
               f"  Message: {e.msg}")
        return False, err
    except Exception as e:
        return False, f"Erreur lecture {file_path}: {e}"


def verify_all_sources():
    banner("🔍 Vérification syntaxique de tous les fichiers")
    errors = []
    py_files = list(SRC_DIR.rglob("*.py"))
    if not py_files:
        LOG.error(f"❌ Aucun fichier .py trouvé dans {SRC_DIR}/")
        return False
    for py_file in py_files:
        ok, err = check_python_syntax(py_file)
        rel = py_file.relative_to(SRC_DIR)
        if ok:
            LOG.info(f"  ✅ {rel}")
        else:
            LOG.error(f"  ❌ {rel}")
            LOG.error(f"     {err}")
            errors.append((py_file, err))
    if errors:
        LOG.error(f"\n❌ {len(errors)} fichier(s) avec erreurs!")
        write_startup_log("SYNTAX ERRORS:\n" + "\n".join(e[1] for e in errors))
        return False
    LOG.info(f"\n✅ {len(py_files)} fichiers valides")
    return True


def verify_imports(venv_mgr):
    banner("🔍 Vérification des imports")
    test_script = (
        "import sys\n"
        "sys.path.insert(0, '.')\n"
        "tests = [\n"
        "    ('src.core.database', 'DatabaseManager'),\n"
        "    ('src.core.logger', 'LogManager'),\n"
        "    ('src.core.platforms', 'detect_platform'),\n"
        "    ('src.core.constants', 'SUPPORTED_PLATFORMS'),\n"
        "    ('src.ui.theme', 'apply_modern_theme'),\n"
        "    ('src.ui.main_window', 'YouTubeDownloaderPro'),\n"
        "    ('src.utils.icon_utils', 'get_app_icon_path'),\n"
        "    ('src.widgets.download_item', 'DownloadItemWidget'),\n"
        "    ('src.widgets.history_item', 'HistoryItemWidget'),\n"
        "    ('src.dialogs.settings_dialog', 'SettingsDialog'),\n"
        "    ('src.dialogs.extension_dialog', 'ExtensionDialog'),\n"
        "    ('src.dialogs.log_dialog', 'LogDialog'),\n"
        "    ('src.tabs.history_tab', 'HistoryTab'),\n"
        "    ('src.workers.download_worker', 'DownloadWorker'),\n"
        "    ('src.workers.torrent_worker', 'TorrentWorker'),\n"
        "]\n"
        "errors = []\n"
        "for module, symbol in tests:\n"
        "    try:\n"
        "        mod = __import__(module, fromlist=[symbol])\n"
        "        getattr(mod, symbol)\n"
        "        print(f'  OK: {module}.{symbol}')\n"
        "    except Exception as e:\n"
        "        import traceback\n"
        "        err = f'FAIL: {module}.{symbol}\\n{traceback.format_exc()}'\n"
        "        errors.append(err)\n"
        "        print(err)\n"
        "if errors:\n"
        "    print('\\n=== ERREURS ===')\n"
        "    for e in errors:\n"
        "        print(e)\n"
        "    sys.exit(1)\n"
        "sys.exit(0)\n"
    )
    try:
        result = venv_mgr.run_python(["-c", test_script], capture=True, check=False)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.strip():
                    LOG.info(f"  {line}")
            LOG.info("✅ Tous les imports fonctionnent")
            return True
        else:
            LOG.error("❌ Erreurs d'import détectées:")
            LOG.error(result.stdout)
            if result.stderr:
                LOG.error(result.stderr)
            write_startup_log(f"IMPORT ERRORS:\n{result.stdout}\n{result.stderr}")
            return False
    except Exception as e:
        LOG.error(f"❌ Erreur: {e}")
        return False


# ============================================================================
# VENV MANAGER
# ============================================================================

class VenvManager:
    def __init__(self, venv_path=VENV_DIR):
        self.venv_path = Path(venv_path)
        self.is_windows = platform.system() == "Windows"

    @property
    def python_exe(self):
        return (self.venv_path / "Scripts" / "python.exe") if self.is_windows \
               else (self.venv_path / "bin" / "python")

    def exists(self):
        return self.python_exe.exists()

    def create(self, force=False):
        banner("🌐 Création de l'environnement virtuel")
        if self.exists() and not force:
            LOG.info(f"✅ Venv existant: {self.venv_path}")
            return True
        if force and self.venv_path.exists():
            LOG.info(f"🧹 Suppression ancien venv...")
            shutil.rmtree(self.venv_path, ignore_errors=True)
        LOG.info(f"📦 Création du venv (30-60 sec)...")
        try:
            venv.EnvBuilder(system_site_packages=False, clear=True,
                            with_pip=True, upgrade_deps=True).create(str(self.venv_path))
            LOG.info("✅ Venv créé")
        except Exception as e:
            LOG.error(f"❌ Erreur: {e}")
            return False
        if not self.python_exe.exists():
            LOG.error(f"❌ Python venv introuvable")
            return False
        LOG.info("🔄 Mise à jour pip/setuptools/wheel...")
        try:
            self.run_pip(["install", "--upgrade", "pip", "setuptools", "wheel"],
                         capture=True)
        except Exception:
            pass
        return True

    def run_python(self, args, capture=False, check=True):
        return run([str(self.python_exe)] + args, capture=capture, check=check)

    def run_pip(self, args, capture=False, check=True):
        return run([str(self.python_exe), "-m", "pip"] + args, capture=capture, check=check)

    def check_package(self, import_name):
        try:
            r = self.run_python(["-c", f"import {import_name}"], capture=True, check=False)
            return r.returncode == 0
        except Exception:
            return False

    def install_package(self, package):
        LOG.info(f"📦 {package}...")
        try:
            r = self.run_pip(["install", "--upgrade", package], capture=True, check=False)
            if r.returncode == 0:
                LOG.info(f"  ✅")
                return True
            LOG.error(f"  ❌ {r.stderr[:200] if r.stderr else ''}")
            return False
        except Exception as e:
            LOG.error(f"  ❌ {e}")
            return False

    def get_env(self):
        env = os.environ.copy()
        scripts = str(self.venv_path / ("Scripts" if self.is_windows else "bin"))
        env["PATH"] = scripts + os.pathsep + env.get("PATH", "")
        env["VIRTUAL_ENV"] = str(self.venv_path)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUNBUFFERED"] = "1"
        return env

    def info(self):
        banner("🌐 Environnement virtuel")
        if not self.exists():
            LOG.warning("❌ Aucun venv")
            return False
        LOG.info(f"📁 {self.venv_path.absolute()}")
        try:
            r = self.run_python(["--version"], capture=True)
            LOG.info(f"🐍 {r.stdout.strip()}")
        except Exception:
            pass
        return True


# ============================================================================
# SOURCE FILES
# ============================================================================

SOURCE_FILES = {}

SOURCE_FILES['__init__.py'] = '''"""TK Downloader Pro"""
__version__ = "1.2.0"
'''

SOURCE_FILES['main.py'] = r'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Point d'entrée TK Downloader Pro."""
import sys
import traceback
from pathlib import Path

STARTUP_LOG = Path(__file__).resolve().parent.parent / "startup_error.log"


def _log(msg):
    try:
        with open(STARTUP_LOG, 'a', encoding='utf-8') as f:
            from datetime import datetime
            f.write(f"\n[{datetime.now().isoformat()}] {msg}\n")
    except Exception:
        pass


def _fatal(title, msg):
    full = f"{title}\n\n{msg}"
    print(full, file=sys.stderr)
    _log(full)
    try:
        from PyQt5.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance() or QApplication([])
        QMessageBox.critical(None, title, msg[:2000])
    except Exception:
        pass


try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    _log("1: sys.path OK")
except Exception:
    _fatal("Erreur", traceback.format_exc())
    sys.exit(1)

try:
    from PyQt5.QtWidgets import QApplication, QMessageBox
    from PyQt5.QtGui import QIcon
    from PyQt5.QtCore import QTimer
    _log("2: PyQt5 OK")
except Exception:
    _fatal("PyQt5 manquant", "Installez PyQt5: python setup.py install")
    sys.exit(1)

try:
    from src.ui.main_window import YouTubeDownloaderPro
    _log("3: main_window OK")
except Exception:
    _fatal("Erreur import main_window", traceback.format_exc())
    sys.exit(1)

try:
    from src.ui.theme import apply_modern_theme
    from src.utils.icon_utils import get_app_icon_path
    from src.core.logger import LogManager
    _log("4: thème + utils OK")
except Exception:
    _fatal("Erreur import", traceback.format_exc())
    sys.exit(1)


def main():
    try:
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        try:
            apply_modern_theme(app)
        except Exception:
            _log(f"WARN theme: {traceback.format_exc()}")

        icon_path = get_app_icon_path()
        if icon_path:
            app.setWindowIcon(QIcon(str(icon_path)))

        lm = LogManager()

        def handle_exception(exc_type, exc_value, exc_tb):
            err = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
            print("UNHANDLED:", err, file=sys.stderr)
            _log(f"UNHANDLED:\n{err}")
            try:
                lm.log('exception', err)
            except Exception:
                pass
            try:
                QMessageBox.critical(None, "Crash", f"Erreur:\n{err[:2000]}")
            except Exception:
                pass

        sys.excepthook = handle_exception

        window = YouTubeDownloaderPro()
        _log("5: fenêtre créée")

        if len(sys.argv) > 1:
            url = sys.argv[1]
            if url.startswith(("http://", "https://")):
                window.url_input.setText(url)
                QTimer.singleShot(1000, window.start_single_download)

        window.show()
        return app.exec_()
    except Exception:
        _fatal("Erreur fatale", traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
'''

SOURCE_FILES['core/__init__.py'] = '"""Core package."""\n'

SOURCE_FILES['core/constants.py'] = '''"""Constantes globales."""
import sys
import threading
from pathlib import Path

THUMBNAIL_CACHE_DIR = Path.home() / ".youtube_downloader_thumbnails"
MAX_THUMBNAIL_CONCURRENCY = 4
THUMBNAIL_SEMAPHORE = threading.BoundedSemaphore(MAX_THUMBNAIL_CONCURRENCY)

SUPPORTED_PLATFORMS = [
    "youtube.com", "youtu.be", "facebook.com", "fb.watch", "instagram.com",
    "twitter.com", "x.com", "tiktok.com", "vimeo.com", "dailymotion.com",
    "twitch.tv", "reddit.com", "linkedin.com", "pinterest.com", "snapchat.com",
    "telegram.org", "whatsapp.com", "discord.com", "spotify.com", "soundcloud.com",
    "bandcamp.com", "mixcloud.com", "audiomack.com", "deezer.com", "tidal.com"
]

try:
    import ctypes
    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001
    SLEEP_PREVENTION_AVAILABLE = sys.platform == 'win32' and hasattr(ctypes, 'windll')
except (ImportError, AttributeError):
    SLEEP_PREVENTION_AVAILABLE = False
    ES_CONTINUOUS = 0
    ES_SYSTEM_REQUIRED = 0
'''

SOURCE_FILES['core/platforms.py'] = '''"""Détection de plateforme."""
import urllib.parse
from .constants import SUPPORTED_PLATFORMS


def detect_platform(url):
    try:
        parsed = urllib.parse.urlparse(url.strip())
        hostname = (parsed.hostname or '').lower().rstrip('.')
    except Exception:
        hostname = ''
    for platform in SUPPORTED_PLATFORMS:
        if hostname == platform or hostname.endswith('.' + platform):
            return platform.split('.')[0] if '.' in platform else platform
    path_lower = urllib.parse.unquote(urllib.parse.urlparse(url).path).lower()
    if any(path_lower.endswith(ext) for ext in
           ['.mp4', '.mp3', '.zip', '.exe', '.apk', '.rar', '.7z', '.pdf', '.dmg', '.msi']):
        return "file"
    return "direct"
'''

SOURCE_FILES['core/logger.py'] = '''"""Gestionnaire de logs."""
import os
import sys
import json
from pathlib import Path
from datetime import datetime


class LogManager:
    @staticmethod
    def _app_dir():
        try:
            return Path(__file__).resolve().parent.parent.parent
        except Exception:
            try:
                return Path(sys.argv[0]).resolve().parent
            except Exception:
                return Path.cwd()

    def __init__(self, path=None, txt_path=None):
        app_dir = self._app_dir()
        try:
            app_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        self.jsonl_path = Path(path) if path else app_dir / "downloader_logs.jsonl"
        self.txt_path = Path(txt_path) if txt_path else app_dir / "downloader_logs.txt"
        try:
            self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
            self.txt_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        self.path = self.jsonl_path

    def log(self, level, message, download_id=None, url=None, extra=None):
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level, 'message': str(message),
            'download_id': download_id, 'url': url, 'extra': extra,
        }
        try:
            with open(self.jsonl_path, 'a', encoding='utf-8') as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + '\\n')
        except Exception:
            pass
        try:
            parts = [f"[{timestamp_str}]", f"[{level.upper()}]"]
            if download_id:
                parts.append(f"[id={download_id}]")
            if url:
                short_url = url if len(url) <= 120 else url[:117] + '...'
                parts.append(f"[url={short_url}]")
            header = ' '.join(parts)
            msg_text = str(message).replace('\\r\\n', '\\n').replace('\\r', '\\n')
            with open(self.txt_path, 'a', encoding='utf-8') as fh:
                fh.write(f"{header}\\n")
                for ln in msg_text.split('\\n'):
                    fh.write(f"  {ln}\\n")
                if extra:
                    try:
                        if isinstance(extra, dict):
                            if 'traceback' in extra:
                                fh.write("  --- TRACEBACK ---\\n")
                                for tb_line in str(extra['traceback']).split('\\n'):
                                    if tb_line.strip():
                                        fh.write(f"    {tb_line}\\n")
                            other = {k: v for k, v in extra.items() if k != 'traceback'}
                            if other:
                                fh.write(f"  extra={json.dumps(other, ensure_ascii=False, default=str)}\\n")
                        else:
                            fh.write(f"  extra={str(extra)}\\n")
                    except Exception:
                        pass
                fh.write("\\n")
        except Exception:
            pass

    def read_logs(self, limit=1000):
        if not os.path.exists(self.jsonl_path):
            return []
        out = []
        try:
            with open(self.jsonl_path, 'r', encoding='utf-8') as fh:
                for line in fh:
                    try:
                        out.append(json.loads(line))
                    except Exception:
                        continue
            return out[-limit:]
        except Exception:
            return []

    def clear(self):
        deleted = False
        for p in (self.jsonl_path, self.txt_path):
            try:
                if os.path.exists(p):
                    os.remove(p)
                    deleted = True
            except Exception:
                pass
        return deleted
'''

SOURCE_FILES['core/database.py'] = '''"""Gestionnaire de base de données SQLite."""
import os
import sqlite3
import threading
from pathlib import Path
from datetime import datetime


class DatabaseManager:
    def __init__(self):
        self.db_path = Path.home() / ".youtube_downloader_history.db"
        self.conn = None
        self.cursor = None
        self.pending_updates = {}
        self.batch_lock = threading.Lock()
        self._thread_lock = threading.RLock()
        self.init_database()

    def get_cursor(self):
        return self.conn.cursor() if self.conn else None

    def init_database(self):
        try:
            self.conn = sqlite3.connect(str(self.db_path), timeout=10, check_same_thread=False)
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.cursor = self.conn.cursor()
            self.cursor.execute("""CREATE TABLE IF NOT EXISTS download_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                download_id TEXT UNIQUE, url TEXT NOT NULL, title TEXT,
                file_path TEXT, quality TEXT, is_audio INTEGER, status TEXT,
                start_time TEXT, end_time TEXT, download_time TEXT DEFAULT NULL,
                file_size REAL, error_message TEXT, use_cookies INTEGER DEFAULT 0,
                progress INTEGER DEFAULT 0, speed TEXT DEFAULT '',
                scheduled_time TEXT DEFAULT NULL, queue_order INTEGER DEFAULT 0,
                is_sequential INTEGER DEFAULT 0, platform TEXT DEFAULT ''
            )""")
            self.cursor.execute("""CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY, value TEXT
            )""")
            self.conn.commit()
        except Exception as e:
            print(f"Erreur init DB: {e}")
            self.conn = None
            self.cursor = None

    def add_download(self, download_id, url, title, quality, is_audio, start_time,
                     save_path=None, use_cookies=True, queue_order=0,
                     is_sequential=False, platform=""):
        if not self.conn:
            return
        with self._thread_lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute("""INSERT OR REPLACE INTO download_history
                    (download_id, url, title, quality, is_audio, start_time,
                     download_time, status, file_path, use_cookies, queue_order,
                     is_sequential, platform)
                    VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?)""",
                    (download_id, url, title[:200] if title else url[:200], quality,
                     1 if is_audio else 0, start_time, "En cours", save_path,
                     1 if use_cookies else 0, queue_order,
                     1 if is_sequential else 0, platform[:50] if platform else ""))
                self.conn.commit()
            except Exception as e:
                print(f"Erreur add: {e}")

    def get_active_downloads(self):
        if not self.conn:
            return []
        with self._thread_lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute("""SELECT download_id, url, quality, is_audio,
                    file_path, title, use_cookies, queue_order, is_sequential, platform
                    FROM download_history
                    WHERE status IN ('En cours', 'Erreur', 'Interrompu',
                                     'في الانتظار', 'مجدول')
                       OR status LIKE '⚠️ Erreur%'""")
                return cursor.fetchall()
            except Exception as e:
                print(f"Erreur get active: {e}")
                return []

    def update_download(self, download_id, status, file_path=None, error_message=None):
        if not self.conn:
            return
        with self._thread_lock:
            try:
                end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor = self.conn.cursor()
                if status == "Terminé" and file_path:
                    fs = 0
                    if os.path.exists(file_path):
                        fs = os.path.getsize(file_path) / (1024 * 1024)
                    cursor.execute("""UPDATE download_history SET status=?, end_time=?,
                        download_time=?, file_path=?, file_size=?, error_message=?
                        WHERE download_id=?""",
                        (status, end_time, end_time, file_path, fs, error_message, download_id))
                elif status == "Erreur":
                    cursor.execute("""UPDATE download_history SET status=?, end_time=?,
                        error_message=? WHERE download_id=?""",
                        (status, end_time, error_message, download_id))
                else:
                    cursor.execute("UPDATE download_history SET status=? WHERE download_id=?",
                                   (status, download_id))
                self.conn.commit()
            except Exception as e:
                print(f"Erreur update: {e}")

    def update_queue_order(self, download_id, queue_order, is_sequential=True):
        if not self.conn:
            return False
        with self._thread_lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute("UPDATE download_history SET queue_order=?, is_sequential=? WHERE download_id=?",
                               (int(queue_order), 1 if is_sequential else 0, download_id))
                self.conn.commit()
                return True
            except Exception:
                return False

    def enqueue_update(self, download_id, status=None, file_path=None,
                       error_message=None, title=None, progress=None, speed=None):
        if not self.conn:
            return
        with self.batch_lock:
            row = self.pending_updates.get(download_id, {})
            if status is not None: row['status'] = status
            if file_path is not None: row['file_path'] = file_path
            if error_message is not None: row['error_message'] = error_message
            if title is not None: row['title'] = title[:200]
            if progress is not None: row['progress'] = int(progress)
            if speed is not None: row['speed'] = str(speed)
            self.pending_updates[download_id] = row

    def flush_updates(self):
        if not self.conn:
            return
        with self.batch_lock, self._thread_lock:
            if not self.pending_updates:
                return
            try:
                cursor = self.conn.cursor()
                cursor.execute('BEGIN')
                for did, values in list(self.pending_updates.items()):
                    fields, params = [], []
                    if values.get('title') is not None:
                        fields.append('title=?'); params.append(values['title'])
                    if values.get('progress') is not None:
                        fields.append('progress=?'); params.append(values['progress'])
                    if values.get('speed') is not None:
                        fields.append('speed=?'); params.append(values['speed'])
                    status = values.get('status')
                    if status is not None:
                        if 'Terminé' in status:
                            end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            fields.extend(['status=?', 'end_time=?', 'download_time=?'])
                            params.extend(['Terminé', end_time, end_time])
                            fp = values.get('file_path')
                            fields.append('file_path=?'); params.append(fp)
                            fs = 0
                            if fp and os.path.exists(fp):
                                fs = os.path.getsize(fp) / (1024 * 1024)
                            fields.append('file_size=?'); params.append(fs)
                            fields.append('error_message=?'); params.append(values.get('error_message'))
                        elif 'Erreur' in status:
                            end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            fields.extend(['status=?', 'end_time=?'])
                            params.extend(['Erreur', end_time])
                            if values.get('error_message') is not None:
                                fields.append('error_message=?'); params.append(values['error_message'])
                            if values.get('file_path') is not None:
                                fields.append('file_path=?'); params.append(values['file_path'])
                        elif 'Annulé' in status or 'Interrompu' in status:
                            end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            norm = 'Annulé' if 'Annulé' in status else 'Interrompu'
                            fields.extend(['status=?', 'end_time=?'])
                            params.extend([norm, end_time])
                        else:
                            fields.append('status=?'); params.append(status)
                    if not fields:
                        continue
                    params.append(did)
                    cursor.execute('UPDATE download_history SET ' + ', '.join(fields) +
                                   ' WHERE download_id=?', tuple(params))
                self.conn.commit()
                self.pending_updates.clear()
            except Exception as e:
                print(f"Erreur flush: {e}")
                try:
                    self.conn.rollback()
                except Exception:
                    pass

    def get_history(self, limit=100):
        if not self.conn:
            return []
        with self._thread_lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute("""SELECT download_id, url, title, quality,
                    CASE WHEN is_audio=1 THEN 'Audio (MP3)' ELSE 'Vidéo' END,
                    status, file_path, datetime(start_time), datetime(end_time),
                    ROUND(file_size, 2),
                    COALESCE(datetime(download_time), datetime(end_time),
                             datetime(start_time), datetime('now'))
                    FROM download_history WHERE start_time IS NOT NULL
                    ORDER BY datetime(COALESCE(download_time, end_time, start_time)) DESC
                    LIMIT ?""", (limit,))
                return cursor.fetchall()
            except Exception as e:
                print(f"Erreur get history: {e}")
                return []

    def clear_history(self):
        if not self.conn:
            return False
        with self._thread_lock:
            try:
                self.conn.cursor().execute('DELETE FROM download_history')
                self.conn.commit()
                return True
            except Exception:
                return False

    def delete_history_item(self, download_id):
        if not self.conn:
            return False
        with self._thread_lock:
            try:
                self.conn.cursor().execute('DELETE FROM download_history WHERE download_id=?',
                                           (download_id,))
                self.conn.commit()
                return True
            except Exception:
                return False

    def save_preference(self, key, value):
        if not self.conn:
            return
        with self._thread_lock:
            try:
                self.conn.cursor().execute('INSERT OR REPLACE INTO preferences (key, value) VALUES (?, ?)',
                                           (key, value))
                self.conn.commit()
            except Exception:
                pass

    def get_preference(self, key, default=None):
        if not self.conn:
            return default
        with self._thread_lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute('SELECT value FROM preferences WHERE key=?', (key,))
                result = cursor.fetchone()
                return result[0] if result else default
            except Exception:
                return default

    def close(self):
        if self.conn:
            try:
                self.flush_updates()
            except Exception:
                pass
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None
            self.cursor = None
'''

SOURCE_FILES['utils/__init__.py'] = '"""Utils package."""\n'

SOURCE_FILES['utils/icon_utils.py'] = '''"""Utilitaires pour les icônes."""
from pathlib import Path


def get_app_icon_path():
    try:
        base_dir = Path(__file__).resolve().parent.parent.parent
    except Exception:
        base_dir = Path.cwd()
    for icon_name in ("icon.ico", "icon.png", "icon.svg"):
        p = base_dir / icon_name
        if p.exists():
            return p
    return None
'''

SOURCE_FILES['utils/system_utils.py'] = '''"""Utilitaires système."""
import sys

try:
    import ctypes
    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001
    SLEEP_PREVENTION_AVAILABLE = sys.platform == 'win32' and hasattr(ctypes, 'windll')
except (ImportError, AttributeError):
    SLEEP_PREVENTION_AVAILABLE = False
    ES_CONTINUOUS = 0
    ES_SYSTEM_REQUIRED = 0
'''

SOURCE_FILES['workers/__init__.py'] = '"""Workers package."""\n'

SOURCE_FILES['workers/download_worker.py'] = r'''"""Worker de téléchargement yt-dlp + HTTP direct."""
import os
import re
import time
from PyQt5.QtCore import QThread, pyqtSignal
from ..core.constants import SUPPORTED_PLATFORMS
from ..core.platforms import detect_platform
from ..core.logger import LogManager

try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except ImportError:
    YTDLP_AVAILABLE = False

import requests


class DownloadWorker(QThread):
    progress_signal = pyqtSignal(int, str, str)
    status_signal = pyqtSignal(str, str)
    finished_signal = pyqtSignal(str, bool, str)
    title_signal = pyqtSignal(str, str)

    def __init__(self, download_id, url, save_path, quality,
                 is_audio_only=False, use_cookies=False, retry_count=0,
                 resume_file_path=None):
        super().__init__()
        self.download_id = download_id
        self.url = url
        self.save_path = save_path
        self.quality = quality
        self.is_audio_only = is_audio_only
        self.use_cookies = use_cookies
        self.retry_count = retry_count
        self.resume_file_path = resume_file_path
        self.output_path = None
        self.is_paused = False
        self.is_cancelled = False
        self.video_title = ""
        self.start_time = time.time()
        self.last_update_time = time.time()
        self.last_downloaded_size = 0
        self.last_speed_text = "0 KB/s"
        self.platform = detect_platform(url)

    def format_speed(self, bps):
        if bps >= 1024 * 1024:
            return f"{bps / (1024 * 1024):.2f} MB/s"
        elif bps >= 1024:
            return f"{bps / 1024:.1f} KB/s"
        return f"{bps:.0f} B/s"

    def _get_speed_text(self, downloaded_bytes):
        now = time.time()
        elapsed = now - self.last_update_time
        if elapsed <= 0:
            return self.last_speed_text
        delta = downloaded_bytes - self.last_downloaded_size
        if elapsed < 0.5 and self.last_speed_text:
            return self.last_speed_text
        speed = delta / elapsed
        self.last_downloaded_size = downloaded_bytes
        self.last_update_time = now
        self.last_speed_text = self.format_speed(speed)
        return self.last_speed_text

    def _yt_progress(self, d):
        while self.is_paused and not self.is_cancelled:
            time.sleep(0.5)
        if d.get('status') == 'downloading':
            p = str(d.get('_percent_str', '0%')).replace('%', '')
            try:
                percentage = int(float(p))
            except Exception:
                percentage = 0
            try:
                if d.get('downloaded_bytes') is not None:
                    speed_text = self._get_speed_text(int(d['downloaded_bytes']))
                else:
                    speed_text = str(d.get('_speed_str', '0 KB/s'))
            except Exception:
                speed_text = str(d.get('_speed_str', '0 KB/s'))
            try:
                self.progress_signal.emit(max(0, min(100, percentage)),
                                          self.download_id, speed_text)
            except Exception:
                pass
        elif d.get('status') == 'finished':
            try:
                self.progress_signal.emit(100, self.download_id, "مكتمل")
            except Exception:
                pass

    def _is_platform_supported(self):
        supported = ['youtube', 'youtu', 'facebook', 'fb', 'instagram', 'twitter',
                     'x', 'tiktok', 'vimeo', 'dailymotion', 'twitch', 'reddit',
                     'linkedin', 'pinterest', 'snapchat', 'spotify', 'soundcloud',
                     'bandcamp', 'mixcloud', 'audiomack', 'deezer', 'tidal']
        return self.platform in supported or any(p in self.platform for p in supported)

    def _quality_format(self, quality):
        limits = {'Haute qualité (1080p)': 1080,
                  'Moyenne qualité (720p)': 720,
                  'Basse qualité (360p)': 360}
        height = limits.get(quality, 1080)
        return f'bestvideo[height<={height}]+bestaudio/best[height<={height}]/best'

    def run(self):
        lm = LogManager()
        try:
            lm.log('info', f"Début download: {self.platform}",
                   download_id=self.download_id, url=self.url)
        except Exception:
            pass
        if YTDLP_AVAILABLE and (self._is_platform_supported() or
                                any(p in self.url.lower() for p in SUPPORTED_PLATFORMS)):
            self._run_ytdlp()
        else:
            self._run_direct()

    def _run_ytdlp(self):
        worker_ref = self
        log_ref = LogManager()

        class MyLogger:
            def debug(self, msg):
                try:
                    log_ref.log('debug', f"[yt-dlp] {msg}",
                                download_id=worker_ref.download_id, url=worker_ref.url)
                except Exception:
                    pass
            def warning(self, msg):
                try:
                    log_ref.log('warning', f"[yt-dlp] {msg}",
                                download_id=worker_ref.download_id, url=worker_ref.url)
                except Exception:
                    pass
            def error(self, msg):
                try:
                    log_ref.log('error', f"[yt-dlp] {msg}",
                                download_id=worker_ref.download_id, url=worker_ref.url)
                except Exception:
                    pass

        ydl_opts = {
            'format': ('bestaudio/best' if self.is_audio_only
                       else self._quality_format(self.quality)),
            'outtmpl': os.path.join(self.save_path, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': False,
            'retries': 10,
            'fragment_retries': 10,
            'socket_timeout': 30,
            'no_color': True,
            'noplaylist': True,
            'ignoreerrors': False,
            'extract_flat': False,
            'progress_hooks': [lambda d, w=worker_ref: w._yt_progress(d)],
            'logger': MyLogger(),
        }
        if self.is_audio_only:
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]

        browsers = ['chrome', 'edge', 'brave', 'chromium', 'firefox'] if self.use_cookies else []
        browsers.append(None)

        info = None
        last_exc = None
        working_browser = None
        for browser in browsers:
            if self.is_cancelled:
                self.finished_signal.emit(self.download_id, False, "تم الإلغاء")
                return
            opts = dict(ydl_opts)
            if browser:
                opts['cookiesfrombrowser'] = (browser,)
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(self.url, download=False)
                working_browser = browser
                break
            except Exception as e:
                last_exc = e
                continue

        if info is None:
            self.finished_signal.emit(self.download_id, False,
                                      f"Échec extraction: {last_exc}")
            return

        title = info.get('title') or self.url.split('/')[-1].split('?')[0]
        self.video_title = self.clean_filename(title)
        self.title_signal.emit(self.download_id, self.video_title)
        self.status_signal.emit(self.download_id, f"📥 {self.video_title[:40]}...")

        final_filename = None
        try:
            opts = dict(ydl_opts)
            if working_browser:
                opts['cookiesfrombrowser'] = (working_browser,)
            with yt_dlp.YoutubeDL(opts) as ydl:
                final_info = ydl.extract_info(self.url, download=True)
                final_filename = ydl.prepare_filename(final_info)
        except Exception as e:
            self.finished_signal.emit(self.download_id, False, str(e))
            return

        if not final_filename or not os.path.exists(final_filename):
            if os.path.exists(self.save_path):
                recent = []
                for f in os.listdir(self.save_path):
                    fp = os.path.join(self.save_path, f)
                    if os.path.isfile(fp) and time.time() - os.path.getmtime(fp) < 300:
                        recent.append((fp, os.path.getmtime(fp)))
                if recent:
                    recent.sort(key=lambda x: x[1], reverse=True)
                    final_filename = recent[0][0]

        if final_filename and os.path.exists(final_filename):
            self.output_path = final_filename
            self.finished_signal.emit(self.download_id, True, final_filename)
        else:
            self.finished_signal.emit(self.download_id, False,
                                      "Fichier introuvable après téléchargement")

    def _run_direct(self):
        download_url = self.url
        try:
            head = requests.head(download_url, allow_redirects=True, timeout=10)
            cd = head.headers.get('Content-Disposition', '')
            if 'filename=' in cd:
                filename = cd.split('filename=')[-1].strip('"').strip("'")
            else:
                filename = self.url.split("/")[-1].split("?")[0] or "downloaded_file"
        except Exception:
            filename = self.url.split("/")[-1].split("?")[0] or "downloaded_file"

        if not filename or "." not in filename:
            filename = f"download_{int(time.time())}"

        filename = self.clean_filename(filename)
        self.video_title = filename
        self.title_signal.emit(self.download_id, self.video_title)

        output_path = (self.resume_file_path if self.resume_file_path
                       else os.path.join(self.save_path, filename))
        self.output_path = output_path

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*', 'Accept-Encoding': 'identity',
        }

        downloaded = 0
        if os.path.exists(output_path):
            downloaded = os.path.getsize(output_path)
            headers['Range'] = f'bytes={downloaded}-'
            self.status_signal.emit(self.download_id,
                                    f"🔄 Reprise depuis {downloaded / (1024 * 1024):.1f} MB...")

        try:
            response = requests.get(download_url, stream=True, timeout=30, headers=headers)
            if response.status_code == 416:
                self.progress_signal.emit(100, self.download_id, "مكتمل")
                self.finished_signal.emit(self.download_id, True, output_path)
                return
            if downloaded > 0 and response.status_code != 206:
                response.close()
                response = requests.get(download_url, stream=True, timeout=30,
                                        headers={'User-Agent': headers['User-Agent']})
                downloaded = 0
                mode = 'wb'
            else:
                mode = 'ab' if downloaded > 0 else 'wb'

            response.raise_for_status()
            total = int(response.headers.get('content-length', 0)) + downloaded

            with open(output_path, mode) as f:
                self.last_downloaded_size = downloaded
                self.last_update_time = time.time()
                for chunk in response.iter_content(chunk_size=1024 * 64):
                    while self.is_paused and not self.is_cancelled:
                        time.sleep(0.5)
                    if self.is_cancelled:
                        response.close()
                        self.finished_signal.emit(self.download_id, False, "تم الإلغاء")
                        return
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            pct = int((downloaded / total) * 100)
                            speed = self._get_speed_text(downloaded)
                            self.progress_signal.emit(pct, self.download_id, speed)
            response.close()

            if os.path.exists(output_path) and os.path.getsize(output_path) >= 1024:
                self.finished_signal.emit(self.download_id, True, output_path)
            else:
                self.finished_signal.emit(self.download_id, False, "Fichier vide ou corrompu")
        except Exception as e:
            self.finished_signal.emit(self.download_id, False, str(e))

    def clean_filename(self, filename):
        filename = str(filename or 'downloaded_file')
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)
        filename = filename.rstrip(' .') or 'downloaded_file'
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:max(1, 200 - len(ext))] + ext
        return filename

    def pause(self):
        self.is_paused = True
        self.status_signal.emit(self.download_id, "⏸️ متوقف مؤقتاً")

    def resume(self):
        self.is_paused = False
        self.status_signal.emit(self.download_id, "🔄 استئناف...")

    def cancel(self):
        self.is_cancelled = True
'''

SOURCE_FILES['workers/torrent_worker.py'] = r'''"""Worker pour téléchargement Torrent (aria2p)."""
import os
import time
from PyQt5.QtCore import QThread, pyqtSignal

try:
    import aria2p
    ARIA2P_AVAILABLE = True
except ImportError:
    ARIA2P_AVAILABLE = False


class TorrentWorker(QThread):
    progress_signal = pyqtSignal(int, str, str)
    status_signal = pyqtSignal(str, str)
    finished_signal = pyqtSignal(str, bool, str)
    title_signal = pyqtSignal(str, str)

    def __init__(self, download_id, torrent_source, save_path):
        super().__init__()
        self.download_id = download_id
        self.torrent_source = torrent_source
        self.save_path = save_path
        self.is_cancelled = False
        self.is_paused = False
        self.aria2_process = None
        self.api = None
        self.download = None

    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def run(self):
        try:
            if not ARIA2P_AVAILABLE:
                self.finished_signal.emit(self.download_id, False,
                                          "aria2p non installé: pip install aria2p")
                return
            import subprocess
            import socket
            aria2c_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aria2c.exe")
            if not os.path.exists(aria2c_path):
                aria2c_path = "aria2c"
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.bind(('127.0.0.1', 0))
                rpc_port = probe.getsockname()[1]
            self.aria2_process = subprocess.Popen([
                aria2c_path, "--enable-rpc", "--rpc-listen-all=false",
                f"--rpc-listen-port={rpc_port}",
                "--dir=" + self.save_path, "--seed-time=0"
            ], creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            time.sleep(1)
            self.api = aria2p.API(aria2p.Client(host="http://127.0.0.1",
                                                 port=rpc_port, secret=""))
            self.status_signal.emit(self.download_id, "Ajout du torrent...")
            if self.torrent_source.startswith("magnet:"):
                self.download = self.api.add_magnet(self.torrent_source)
            else:
                if not os.path.exists(self.torrent_source):
                    self.finished_signal.emit(self.download_id, False, "Torrent introuvable")
                    return
                self.download = self.api.add_torrent(self.torrent_source)
            while self.download.is_metadata and not self.is_cancelled:
                time.sleep(0.5)
                self.download.update()
            if self.is_cancelled:
                return
            torrent_name = self.download.name.replace("[METADATA]", "").strip()
            self.title_signal.emit(self.download_id, torrent_name)
            self.status_signal.emit(self.download_id, "Connexion aux peers...")
            while not self.is_cancelled:
                self.download.update()
                if self.download.is_complete:
                    self.progress_signal.emit(100, self.download_id, "Complet")
                    self.finished_signal.emit(self.download_id, True,
                                              os.path.join(self.save_path, torrent_name))
                    break
                if self.download.has_failed:
                    self.finished_signal.emit(self.download_id, False,
                                              self.download.error_message)
                    break
                progress = int(self.download.progress)
                speed = self.download.download_speed
                speed_text = f"{self.format_size(speed)}/s | Peers: {self.download.connections}"
                self.progress_signal.emit(progress, self.download_id, speed_text)
                self.status_signal.emit(self.download_id, f"📥 {progress}%")
                while self.is_paused and not self.is_cancelled:
                    if not self.download.is_paused:
                        self.download.pause()
                    time.sleep(0.5)
                if self.is_paused and not self.download.is_paused:
                    self.download.pause()
                elif not self.is_paused and self.download.is_paused:
                    self.download.resume()
                time.sleep(1)
            if self.is_cancelled and self.download:
                self.download.remove()
                self.finished_signal.emit(self.download_id, False, "Annulé")
        except Exception as e:
            import traceback
            self.finished_signal.emit(self.download_id, False, f"{e}\n{traceback.format_exc()}")
        finally:
            if self.aria2_process:
                try:
                    self.aria2_process.terminate()
                    self.aria2_process.wait()
                except Exception:
                    pass

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def cancel(self):
        self.is_cancelled = True
'''

SOURCE_FILES['ui/__init__.py'] = '"""UI package."""\n'

SOURCE_FILES['ui/theme.py'] = '''"""Thème moderne global."""
from PyQt5.QtGui import QFont


class Colors:
    PRIMARY = "#2563EB"
    PRIMARY_HOVER = "#1D4ED8"
    PRIMARY_PRESSED = "#1E40AF"
    PRIMARY_LIGHT = "#DBEAFE"
    PRIMARY_TEXT = "#FFFFFF"
    SUCCESS = "#10B981"
    SUCCESS_HOVER = "#059669"
    SUCCESS_LIGHT = "#D1FAE5"
    WARNING = "#F59E0B"
    WARNING_HOVER = "#D97706"
    WARNING_LIGHT = "#FEF3C7"
    DANGER = "#EF4444"
    DANGER_HOVER = "#DC2626"
    DANGER_LIGHT = "#FEE2E2"
    INFO = "#3B82F6"
    INFO_HOVER = "#2563EB"
    INFO_LIGHT = "#DBEAFE"
    BG_MAIN = "#F9FAFB"
    BG_CARD = "#FFFFFF"
    BG_SIDEBAR = "#F3F4F6"
    BG_INPUT = "#FFFFFF"
    BG_HOVER = "#F3F4F6"
    BG_DISABLED = "#E5E7EB"
    TEXT_PRIMARY = "#111827"
    TEXT_SECONDARY = "#4B5563"
    TEXT_MUTED = "#9CA3AF"
    TEXT_INVERSE = "#FFFFFF"
    TEXT_DISABLED = "#9CA3AF"
    BORDER = "#E5E7EB"
    BORDER_HOVER = "#D1D5DB"
    BORDER_FOCUS = "#2563EB"
    GRADIENT_BLUE = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3B82F6, stop:1 #2563EB)"


SCROLLBAR_STYLE = f"""
QScrollBar:vertical {{
    background: {Colors.BG_SIDEBAR};
    width: 12px;
    margin: 0px;
    border-radius: 6px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: {Colors.BORDER_HOVER};
    min-height: 40px;
    border-radius: 6px;
    margin: 2px;
}}
QScrollBar::handle:vertical:hover {{
    background: {Colors.TEXT_MUTED};
}}
QScrollBar::handle:vertical:pressed {{
    background: {Colors.PRIMARY};
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    background: none;
    height: 0px;
    border: none;
}}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: none;
}}
QScrollBar:horizontal {{
    background: {Colors.BG_SIDEBAR};
    height: 12px;
    margin: 0px;
    border-radius: 6px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: {Colors.BORDER_HOVER};
    min-width: 40px;
    border-radius: 6px;
    margin: 2px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {Colors.TEXT_MUTED};
}}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    background: none;
    width: 0px;
    border: none;
}}
QScrollArea {{
    background: transparent;
    border: none;
}}
"""


def get_global_stylesheet():
    return f"""
QWidget {{
    font-family: 'Segoe UI', 'Tahoma', 'Arial', sans-serif;
    font-size: 13px;
    color: {Colors.TEXT_PRIMARY};
}}
QMainWindow {{ background-color: {Colors.BG_MAIN}; }}
QDialog {{ background-color: {Colors.BG_CARD}; }}
QGroupBox {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 10px;
    margin-top: 14px;
    padding: 12px;
    font-weight: 600;
    color: {Colors.TEXT_PRIMARY};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: {Colors.PRIMARY};
    background-color: {Colors.BG_CARD};
}}
QLabel {{ color: {Colors.TEXT_PRIMARY}; background: transparent; }}
QPushButton {{
    background-color: {Colors.PRIMARY};
    color: {Colors.TEXT_INVERSE};
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: 600;
    font-size: 13px;
    min-height: 20px;
}}
QPushButton:hover {{ background-color: {Colors.PRIMARY_HOVER}; }}
QPushButton:pressed {{ background-color: {Colors.PRIMARY_PRESSED}; }}
QPushButton:disabled {{
    background-color: {Colors.BG_DISABLED};
    color: {Colors.TEXT_DISABLED};
}}
QLineEdit, QComboBox, QSpinBox, QTimeEdit {{
    background-color: {Colors.BG_INPUT};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    padding: 8px 12px;
    selection-background-color: {Colors.PRIMARY};
    selection-color: {Colors.TEXT_INVERSE};
    min-height: 20px;
}}
QLineEdit:focus, QComboBox:focus, QTimeEdit:focus {{
    border: 2px solid {Colors.BORDER_FOCUS};
    padding: 7px 11px;
}}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {Colors.TEXT_SECONDARY};
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {Colors.BG_CARD};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    padding: 4px;
    selection-background-color: {Colors.PRIMARY};
    selection-color: {Colors.TEXT_INVERSE};
    outline: none;
}}
QTextEdit, QPlainTextEdit {{
    background-color: {Colors.BG_INPUT};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    padding: 8px;
    selection-background-color: {Colors.PRIMARY};
    selection-color: {Colors.TEXT_INVERSE};
}}
QCheckBox {{ color: {Colors.TEXT_PRIMARY}; spacing: 8px; padding: 4px; }}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid {Colors.BORDER_HOVER};
    background-color: {Colors.BG_CARD};
}}
QCheckBox::indicator:hover {{ border-color: {Colors.PRIMARY}; }}
QCheckBox::indicator:checked {{
    background-color: {Colors.PRIMARY};
    border-color: {Colors.PRIMARY};
}}
QProgressBar {{
    background-color: {Colors.BG_SIDEBAR};
    border: none;
    border-radius: 6px;
    text-align: center;
    color: {Colors.TEXT_PRIMARY};
    font-weight: 600;
    font-size: 11px;
    min-height: 12px;
}}
QProgressBar::chunk {{
    background: {Colors.GRADIENT_BLUE};
    border-radius: 6px;
}}
QTabWidget::pane {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 10px;
    top: -1px;
}}
QTabBar {{ background: transparent; qproperty-drawBase: 0; }}
QTabBar::tab {{
    background-color: transparent;
    color: {Colors.TEXT_SECONDARY};
    padding: 10px 20px;
    margin-right: 4px;
    border: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
    font-size: 13px;
    min-width: 80px;
}}
QTabBar::tab:hover {{
    background-color: {Colors.BG_HOVER};
    color: {Colors.PRIMARY};
}}
QTabBar::tab:selected {{
    background-color: {Colors.BG_CARD};
    color: {Colors.PRIMARY};
    border-bottom: 3px solid {Colors.PRIMARY};
}}
QTableWidget, QTableView {{
    background-color: {Colors.BG_CARD};
    alternate-background-color: {Colors.BG_SIDEBAR};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    gridline-color: {Colors.BORDER};
    selection-background-color: {Colors.PRIMARY_LIGHT};
    selection-color: {Colors.TEXT_PRIMARY};
    outline: none;
}}
QHeaderView::section {{
    background-color: {Colors.BG_SIDEBAR};
    color: {Colors.TEXT_SECONDARY};
    padding: 8px;
    border: none;
    border-bottom: 1px solid {Colors.BORDER};
    font-weight: 600;
    font-size: 12px;
}}
QMenuBar {{
    background-color: {Colors.BG_CARD};
    color: {Colors.TEXT_PRIMARY};
    border-bottom: 1px solid {Colors.BORDER};
    padding: 4px;
}}
QMenuBar::item {{
    background: transparent;
    padding: 6px 12px;
    border-radius: 6px;
}}
QMenuBar::item:selected {{
    background-color: {Colors.PRIMARY_LIGHT};
    color: {Colors.PRIMARY};
}}
QMenu {{
    background-color: {Colors.BG_CARD};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    padding: 4px;
}}
QMenu::item {{ padding: 8px 20px; border-radius: 4px; }}
QMenu::item:selected {{
    background-color: {Colors.PRIMARY_LIGHT};
    color: {Colors.PRIMARY};
}}
QStatusBar {{
    background-color: {Colors.BG_CARD};
    color: {Colors.TEXT_SECONDARY};
    border-top: 1px solid {Colors.BORDER};
    padding: 4px 8px;
}}
{SCROLLBAR_STYLE}
"""


def apply_modern_theme(app):
    try:
        font = QFont("Segoe UI", 10)
        app.setFont(font)
    except Exception:
        pass
    app.setStyleSheet(get_global_stylesheet())
'''

# ---------- widgets ----------
SOURCE_FILES['widgets/__init__.py'] = '"""Widgets package."""\n'

SOURCE_FILES['widgets/download_item.py'] = r'''"""Widget pour un élément de téléchargement."""
import os
import sys
import hashlib
import threading
import requests
from PyQt5.QtWidgets import (QFrame, QHBoxLayout, QVBoxLayout, QLabel,
                              QProgressBar, QPushButton, QMessageBox,
                              QInputDialog, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, QUrl
from PyQt5.QtGui import QPixmap, QDesktopServices
from ..core.constants import THUMBNAIL_CACHE_DIR, THUMBNAIL_SEMAPHORE
from ..ui.theme import Colors


class DownloadItemWidget(QFrame):
    thumb_signal = pyqtSignal(object)

    def __init__(self, download_id, url, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.download_id = download_id
        self.url = url
        self.pinned = False
        self.video_title = "جاري جلب المعلومات..."
        self.file_path = None
        self._thumb_active = True
        self._compact_mode = False
        self.resume_file_path = None
        self.queue_order = 0
        self.initUI()
        self.thumb_signal.connect(self._update_thumb_ui, Qt.QueuedConnection)
        self.load_thumbnail()

    def _update_thumb_ui(self, data):
        if isinstance(data, str):
            self.thumb_label.setPixmap(QPixmap())
            self.thumb_label.setText(data)
        elif isinstance(data, bytes):
            pix = QPixmap()
            pix.loadFromData(data)
            w, h = (90, 54) if self._compact_mode else (120, 68)
            scaled = pix.scaled(w, h, Qt.KeepAspectRatioByExpanding,
                                Qt.SmoothTransformation)
            self.thumb_label.setText("")
            self.thumb_label.setPixmap(scaled)

    def initUI(self):
        self.setObjectName("DownloadItem")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(110)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(14)

        self.thumb_container = QFrame()
        self.thumb_container.setFixedSize(120, 68)
        self.thumb_container.setStyleSheet(
            f"background-color: {Colors.BG_SIDEBAR}; "
            f"border-radius: 8px; border: 1px solid {Colors.BORDER};")
        tl = QVBoxLayout(self.thumb_container)
        tl.setContentsMargins(0, 0, 0, 0)
        self.thumb_label = QLabel("🎬")
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: 22px; "
            f"background: transparent; border: none;")
        tl.addWidget(self.thumb_label)
        layout.addWidget(self.thumb_container)

        info = QVBoxLayout()
        info.setSpacing(6)
        header = QHBoxLayout()
        header.setSpacing(8)
        self.title_label = QLabel(self.video_title)
        self.title_label.setStyleSheet(
            f"font-weight: 600; font-size: 13px; "
            f"color: {Colors.TEXT_PRIMARY}; background: transparent;")
        self.status_badge = QLabel("قيد الانتظار")
        self.status_badge.setAlignment(Qt.AlignCenter)
        self.status_badge.setMinimumWidth(90)
        self._set_badge_style("waiting")
        header.addWidget(self.title_label, 1)
        header.addWidget(self.status_badge)
        info.addLayout(header)

        self.url_label = QLabel(self.url)
        self.url_label.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: 11px; background: transparent;")
        info.addWidget(self.url_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        info.addWidget(self.progress_bar)

        stats = QHBoxLayout()
        self.percentage_label = QLabel("0%")
        self.percentage_label.setStyleSheet(
            f"font-weight: 700; color: {Colors.TEXT_PRIMARY}; "
            f"font-size: 12px; background: transparent;")
        self.speed_label = QLabel("0 KB/s")
        self.speed_label.setStyleSheet(
            f"color: {Colors.SUCCESS}; font-size: 11px; "
            f"font-weight: 600; background: transparent;")
        stats.addWidget(self.percentage_label)
        stats.addStretch()
        stats.addWidget(self.speed_label)
        info.addLayout(stats)
        layout.addLayout(info, 1)

        actions = QVBoxLayout()
        actions.setSpacing(6)
        top = QHBoxLayout()
        top.setSpacing(6)

        self.pin_btn = QPushButton("📌")
        self.pin_btn.setCheckable(True)
        self.pin_btn.setFixedSize(36, 36)
        self.pin_btn.setCursor(Qt.PointingHandCursor)
        self.pin_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_SIDEBAR};
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                font-size: 15px;
            }}
            QPushButton:hover {{
                background-color: {Colors.WARNING_LIGHT};
                border-color: {Colors.WARNING};
                color: {Colors.WARNING_HOVER};
            }}
            QPushButton:checked {{
                background-color: {Colors.WARNING_LIGHT};
                border-color: {Colors.WARNING};
            }}
        """)
        self.pin_btn.clicked.connect(self.toggle_pin)

        self.cancel_btn = QPushButton("✕")
        self.cancel_btn.setFixedSize(36, 36)
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.DANGER_LIGHT};
                color: {Colors.DANGER};
                border: 1px solid {Colors.DANGER};
                border-radius: 8px;
                font-size: 15px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.DANGER};
                color: white;
            }}
        """)
        self.cancel_btn.clicked.connect(self.cancel_download)

        self.move_up_btn = QPushButton("⬆")
        self.move_up_btn.setFixedSize(36, 36)
        self.move_up_btn.setCursor(Qt.PointingHandCursor)
        self.move_up_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SUCCESS_LIGHT};
                color: {Colors.SUCCESS_HOVER};
                border: 1px solid {Colors.SUCCESS};
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {Colors.SUCCESS}; color: white; }}
        """)
        self.move_up_btn.clicked.connect(self.move_up_in_queue)
        self.move_up_btn.hide()

        self.move_down_btn = QPushButton("⬇")
        self.move_down_btn.setFixedSize(36, 36)
        self.move_down_btn.setCursor(Qt.PointingHandCursor)
        self.move_down_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.INFO_LIGHT};
                color: {Colors.INFO_HOVER};
                border: 1px solid {Colors.INFO};
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {Colors.INFO}; color: white; }}
        """)
        self.move_down_btn.clicked.connect(self.move_down_in_queue)
        self.move_down_btn.hide()

        top.addWidget(self.pin_btn)
        top.addWidget(self.cancel_btn)
        top.addStretch()
        top.addWidget(self.move_up_btn)
        top.addWidget(self.move_down_btn)
        actions.addLayout(top)

        bottom = QHBoxLayout()
        bottom.setSpacing(6)
        self.retry_btn = QPushButton("🔁 إعادة")
        self.retry_btn.setFixedHeight(34)
        self.retry_btn.setCursor(Qt.PointingHandCursor)
        self.retry_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SUCCESS};
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                padding: 0 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {Colors.SUCCESS_HOVER}; }}
        """)
        self.retry_btn.clicked.connect(self.retry_download)
        self.retry_btn.hide()

        self.edit_url_btn = QPushButton("✏️ الرابط")
        self.edit_url_btn.setFixedHeight(34)
        self.edit_url_btn.setCursor(Qt.PointingHandCursor)
        self.edit_url_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.INFO};
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                padding: 0 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {Colors.INFO_HOVER}; }}
        """)
        self.edit_url_btn.clicked.connect(self.edit_download_url)
        self.edit_url_btn.hide()

        bottom.addWidget(self.retry_btn)
        bottom.addWidget(self.edit_url_btn)
        bottom.addStretch()
        actions.addLayout(bottom)
        layout.addLayout(actions)

        self.setStyleSheet(f"""
            QFrame#DownloadItem {{
                background-color: {Colors.BG_CARD};
                border: 1px solid {Colors.BORDER};
                border-radius: 12px;
            }}
            QFrame#DownloadItem:hover {{ border: 1px solid {Colors.PRIMARY}; }}
        """)

    def _set_badge_style(self, kind):
        styles = {
            "waiting": f"background-color: {Colors.WARNING_LIGHT}; color: {Colors.WARNING_HOVER};",
            "active": f"background-color: {Colors.INFO_LIGHT}; color: {Colors.INFO_HOVER};",
            "success": f"background-color: {Colors.SUCCESS_LIGHT}; color: {Colors.SUCCESS_HOVER};",
            "error": f"background-color: {Colors.DANGER_LIGHT}; color: {Colors.DANGER_HOVER};",
        }
        s = styles.get(kind, styles["waiting"])
        self.status_badge.setStyleSheet(
            f"QLabel {{ {s} padding: 4px 10px; border-radius: 10px; "
            f"font-size: 11px; font-weight: 700; }}")

    def set_compact(self, compact):
        self._compact_mode = compact
        self.setMinimumHeight(80 if compact else 110)
        self.url_label.setVisible(not compact)
        if compact:
            self.thumb_container.setFixedSize(90, 54)
        else:
            self.thumb_container.setFixedSize(120, 68)

    def load_thumbnail(self):
        def fetch():
            with THUMBNAIL_SEMAPHORE:
                try:
                    if not self._thumb_active:
                        return
                    THUMBNAIL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
                    key = hashlib.sha1(self.url.encode('utf-8')).hexdigest()
                    cache_file = THUMBNAIL_CACHE_DIR / f"{key}.jpg"
                    if cache_file.exists():
                        with open(cache_file, 'rb') as f:
                            if self._thumb_active:
                                self.thumb_signal.emit(f.read())
                        return
                    url_lower = self.url.lower()
                    thumb = None
                    if 'youtube' in url_lower or 'youtu.be' in url_lower:
                        from urllib.parse import urlparse, parse_qs
                        p = urlparse(self.url)
                        vid = None
                        if 'youtu' in p.netloc and p.query:
                            vid = parse_qs(p.query).get('v', [None])[0]
                        if not vid and p.path:
                            vid = p.path.split('/')[-1].split('?')[0]
                        if vid:
                            thumb = f'https://img.youtube.com/vi/{vid}/mqdefault.jpg'
                    if thumb:
                        resp = requests.get(thumb, timeout=6)
                        if resp.status_code == 200:
                            try:
                                cache_file.write_bytes(resp.content)
                            except Exception:
                                pass
                            if self._thumb_active:
                                self.thumb_signal.emit(resp.content)
                            return
                    if self._thumb_active:
                        self.thumb_signal.emit("🎬")
                except Exception:
                    if self._thumb_active:
                        try:
                            self.thumb_signal.emit("📄")
                        except Exception:
                            pass
        threading.Thread(target=fetch, daemon=True).start()

    def toggle_pin(self):
        self.pinned = not self.pinned
        self.pin_btn.setChecked(self.pinned)
        if self.main_window:
            try:
                self.main_window.pin_download(self.download_id, self.pinned)
            except Exception:
                pass

    def update_progress(self, value):
        self.progress_bar.setValue(value)
        self.percentage_label.setText(f"{value}%")

    def update_speed(self, text):
        self.speed_label.setText(text)

    def update_status(self, status):
        self.status_badge.setText(status)
        if "Terminé" in status or "تم" in status:
            self._set_badge_style("success")
            self.show_finish_actions()
        elif "Erreur" in status or "خطأ" in status or "❌" in status or "Annulé" in status:
            self._set_badge_style("error")
            self.show_error_actions()
        elif "متوقف" in status or "Paused" in status or "في الانتظار" in status:
            self._set_badge_style("waiting")
        else:
            self._set_badge_style("active")

    def show_finish_actions(self):
        try:
            self.cancel_btn.hide()
            self.retry_btn.hide()
            self.edit_url_btn.hide()
            if not hasattr(self, 'open_btn'):
                self.open_btn = QPushButton("▶️ تشغيل")
                self.open_btn.setFixedHeight(34)
                self.open_btn.setCursor(Qt.PointingHandCursor)
                self.open_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {Colors.SUCCESS};
                        color: white;
                        border: none;
                        border-radius: 8px;
                        font-weight: 600;
                        padding: 0 12px;
                        font-size: 12px;
                    }}
                    QPushButton:hover {{ background-color: {Colors.SUCCESS_HOVER}; }}
                """)
                self.open_btn.clicked.connect(self.open_file)
                self.layout().itemAt(2).layout().addWidget(self.open_btn)
            if not hasattr(self, 'folder_btn'):
                self.folder_btn = QPushButton("📁 المجلد")
                self.folder_btn.setFixedHeight(34)
                self.folder_btn.setCursor(Qt.PointingHandCursor)
                self.folder_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {Colors.INFO};
                        color: white;
                        border: none;
                        border-radius: 8px;
                        font-weight: 600;
                        padding: 0 12px;
                        font-size: 12px;
                    }}
                    QPushButton:hover {{ background-color: {Colors.INFO_HOVER}; }}
                """)
                self.folder_btn.clicked.connect(self.open_folder)
                self.layout().itemAt(2).layout().addWidget(self.folder_btn)
            self.open_btn.show()
            self.folder_btn.show()
        except Exception:
            pass

    def open_file(self):
        if self.file_path and os.path.exists(self.file_path):
            self.safe_open(self.file_path)
        else:
            QMessageBox.warning(self, "الملف غير موجود", "لم يتم العثور على الملف")

    def open_folder(self):
        if self.file_path:
            folder = os.path.dirname(self.file_path)
            if os.path.exists(folder):
                self.safe_open(folder)

    def safe_open(self, path):
        try:
            if not path:
                return
            path = os.path.abspath(os.path.normpath(path))
            if not os.path.exists(path):
                return
            if sys.platform == 'win32':
                os.startfile(path)
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        except Exception:
            try:
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))
            except Exception:
                pass

    def update_title(self, title):
        self.video_title = title
        short = title[:60] + "..." if len(title) > 60 else title
        self.title_label.setText(short)
        self.title_label.setToolTip(title)

    def show_error_actions(self):
        self.retry_btn.show()
        self.edit_url_btn.show()

    def hide_error_actions(self):
        self.retry_btn.hide()
        self.edit_url_btn.hide()

    def retry_download(self):
        if self.main_window:
            try:
                self.main_window.retry_download(self.download_id)
            except Exception:
                pass

    def edit_download_url(self):
        new_url, ok = QInputDialog.getText(self, 'تحديث الرابط', 'الرابط الجديد:', text=self.url)
        if ok and new_url:
            self.url = new_url.strip()
            self.url_label.setText(self.url)
            if self.main_window:
                try:
                    self.main_window.change_download_url(self.download_id, self.url)
                except Exception:
                    pass

    def cancel_download(self):
        if self.main_window:
            self.main_window.cancel_download(self.download_id)

    def move_up_in_queue(self):
        if self.main_window:
            self.main_window.reorder_sequential_queue(self.download_id, -1)

    def move_down_in_queue(self):
        if self.main_window:
            self.main_window.reorder_sequential_queue(self.download_id, 1)

    def cleanup(self):
        self._thumb_active = False
        try:
            self.thumb_signal.disconnect()
        except Exception:
            pass
'''

SOURCE_FILES['widgets/history_item.py'] = r'''"""Widget pour un élément d'historique."""
import os
import sys
import hashlib
import threading
import requests
from PyQt5.QtWidgets import (QFrame, QHBoxLayout, QVBoxLayout, QLabel,
                              QPushButton, QMessageBox, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, QUrl
from PyQt5.QtGui import QPixmap, QDesktopServices
from ..core.constants import THUMBNAIL_CACHE_DIR, THUMBNAIL_SEMAPHORE
from ..ui.theme import Colors


class HistoryItemWidget(QFrame):
    thumb_signal = pyqtSignal(object)

    def __init__(self, record, parent_tab=None):
        super().__init__()
        self.parent_tab = parent_tab
        if len(record) >= 11:
            (self.download_id, self.url, self.title, self.quality, self.type,
             self.status, self.file_path, self.start_time, self.end_time,
             self.file_size, self.download_time) = record
        else:
            (self.download_id, self.url, self.title, self.quality, self.type,
             self.status, self.file_path, self.start_time, self.end_time,
             self.file_size) = record
            self.download_time = self.end_time or self.start_time
        self._thumb_active = True
        self.initUI()
        self.thumb_signal.connect(self._update_thumb_ui, Qt.QueuedConnection)
        self.load_thumbnail()

    def _update_thumb_ui(self, data):
        if isinstance(data, str):
            self.thumb_label.setPixmap(QPixmap())
            self.thumb_label.setText(data)
        elif isinstance(data, bytes):
            pix = QPixmap()
            pix.loadFromData(data)
            self.thumb_label.setText("")
            self.thumb_label.setPixmap(pix.scaled(120, 68, Qt.KeepAspectRatioByExpanding,
                                                  Qt.SmoothTransformation))

    def initUI(self):
        self.setObjectName("HistoryItem")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(130)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(14)

        self.thumb_container = QFrame()
        self.thumb_container.setFixedSize(120, 68)
        self.thumb_container.setStyleSheet(
            f"background-color: {Colors.BG_SIDEBAR}; "
            f"border-radius: 8px; border: 1px solid {Colors.BORDER};")
        tl = QVBoxLayout(self.thumb_container)
        tl.setContentsMargins(0, 0, 0, 0)
        self.thumb_label = QLabel("🎬")
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: 22px; "
            f"background: transparent; border: none;")
        tl.addWidget(self.thumb_label)
        layout.addWidget(self.thumb_container)

        info = QVBoxLayout()
        info.setSpacing(6)
        header = QHBoxLayout()
        title_text = self.title if self.title else self.url
        self.title_label = QLabel(title_text[:70] + "..." if len(title_text) > 70 else title_text)
        self.title_label.setStyleSheet(
            f"font-weight: 600; font-size: 13px; "
            f"color: {Colors.TEXT_PRIMARY}; background: transparent;")
        badge = QLabel()
        if self.status == "Terminé":
            badge.setText("✅ مكتمل")
            badge.setStyleSheet(
                f"background-color: {Colors.SUCCESS_LIGHT}; "
                f"color: {Colors.SUCCESS_HOVER}; padding: 4px 10px; "
                f"border-radius: 10px; font-size: 11px; font-weight: 700;")
        elif self.status == "Erreur":
            badge.setText("❌ خطأ")
            badge.setStyleSheet(
                f"background-color: {Colors.DANGER_LIGHT}; "
                f"color: {Colors.DANGER_HOVER}; padding: 4px 10px; "
                f"border-radius: 10px; font-size: 11px; font-weight: 700;")
        else:
            badge.setText(self.status)
            badge.setStyleSheet(
                f"background-color: {Colors.INFO_LIGHT}; "
                f"color: {Colors.INFO_HOVER}; padding: 4px 10px; "
                f"border-radius: 10px; font-size: 11px; font-weight: 700;")
        header.addWidget(self.title_label, 1)
        header.addWidget(badge)
        info.addLayout(header)

        display_date = self.download_time or self.end_time or self.start_time or "-"
        details = (f"📅 {display_date}   •   ⚖️ {self.file_size} MB   "
                   f"•   🎥 {self.quality}   •   📂 {self.type}")
        dl = QLabel(details)
        dl.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;")
        info.addWidget(dl)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.open_btn = QPushButton("▶️ تشغيل")
        self.open_btn.setFixedHeight(34)
        self.open_btn.setCursor(Qt.PointingHandCursor)
        self.open_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SUCCESS};
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                padding: 0 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {Colors.SUCCESS_HOVER}; }}
        """)
        self.open_btn.clicked.connect(lambda: self.safe_open(self.file_path))

        self.folder_btn = QPushButton("📁 المجلد")
        self.folder_btn.setFixedHeight(34)
        self.folder_btn.setCursor(Qt.PointingHandCursor)
        self.folder_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.INFO};
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                padding: 0 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {Colors.INFO_HOVER}; }}
        """)
        self.folder_btn.clicked.connect(lambda: self.safe_open(
            os.path.dirname(self.file_path) if self.file_path else None))

        self.delete_btn = QPushButton("🗑️ حذف")
        self.delete_btn.setFixedHeight(34)
        self.delete_btn.setCursor(Qt.PointingHandCursor)
        self.delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_CARD};
                color: {Colors.DANGER};
                border: 1px solid {Colors.DANGER};
                border-radius: 8px;
                font-weight: 600;
                padding: 0 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {Colors.DANGER};
                color: white;
            }}
        """)
        self.delete_btn.clicked.connect(lambda: self.parent_tab.delete_item(
            self.download_id, self))

        actions.addWidget(self.open_btn)
        actions.addWidget(self.folder_btn)
        actions.addWidget(self.delete_btn)
        actions.addStretch()
        info.addLayout(actions)
        layout.addLayout(info, 1)

        self.setStyleSheet(f"""
            QFrame#HistoryItem {{
                background-color: {Colors.BG_CARD};
                border: 1px solid {Colors.BORDER};
                border-radius: 12px;
            }}
            QFrame#HistoryItem:hover {{ border: 1px solid {Colors.PRIMARY}; }}
        """)

    def safe_open(self, path):
        try:
            if not path:
                return
            path = os.path.abspath(os.path.normpath(path))
            if not os.path.exists(path):
                QMessageBox.warning(self, "Introuvable", f"Chemin introuvable:\n{path}")
                return
            if sys.platform == 'win32':
                os.startfile(path)
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        except Exception as e:
            try:
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))
            except Exception:
                QMessageBox.critical(self, "Erreur", f"Échec: {e}")

    def load_thumbnail(self):
        def fetch():
            with THUMBNAIL_SEMAPHORE:
                try:
                    if not self._thumb_active:
                        return
                    THUMBNAIL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
                    key = hashlib.sha1(self.url.encode('utf-8')).hexdigest()
                    cache_file = THUMBNAIL_CACHE_DIR / f"{key}.jpg"
                    if cache_file.exists():
                        with open(cache_file, 'rb') as f:
                            if self._thumb_active:
                                self.thumb_signal.emit(f.read())
                        return
                    url_lower = self.url.lower()
                    thumb = None
                    if 'youtube' in url_lower or 'youtu.be' in url_lower:
                        from urllib.parse import urlparse, parse_qs
                        p = urlparse(self.url)
                        vid = None
                        if 'youtu' in p.netloc and p.query:
                            vid = parse_qs(p.query).get('v', [None])[0]
                        if not vid and p.path:
                            vid = p.path.split('/')[-1].split('?')[0]
                        if vid:
                            thumb = f'https://img.youtube.com/vi/{vid}/mqdefault.jpg'
                    if thumb:
                        resp = requests.get(thumb, timeout=6)
                        if resp.status_code == 200:
                            try:
                                cache_file.write_bytes(resp.content)
                            except Exception:
                                pass
                            if self._thumb_active:
                                self.thumb_signal.emit(resp.content)
                            return
                    if self._thumb_active:
                        self.thumb_signal.emit("🎬" if "Vidéo" in self.type else "🎵")
                except Exception:
                    if self._thumb_active:
                        try:
                            self.thumb_signal.emit("📄")
                        except Exception:
                            pass
        threading.Thread(target=fetch, daemon=True).start()
'''

# ---------- dialogs ----------
SOURCE_FILES['dialogs/__init__.py'] = '"""Dialogs package."""\n'

SOURCE_FILES['dialogs/log_dialog.py'] = r'''"""Boîte de dialogue des logs."""
import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextEdit,
                              QPushButton, QMessageBox, QFileDialog, QLabel)
from PyQt5.QtCore import QTimer, Qt
from ..core.logger import LogManager
from ..ui.theme import Colors


class LogDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle('📋 سجل الأخطاء')
        self.setMinimumSize(800, 500)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        header = QLabel("📋 سجل الأخطاء والعمليات")
        header.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(header)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view, 1)
        btns = QHBoxLayout()
        btns.setSpacing(8)
        refresh = QPushButton("🔄 تحديث")
        refresh.setFixedHeight(38)
        refresh.setCursor(Qt.PointingHandCursor)
        refresh.clicked.connect(self.load_logs)
        export = QPushButton("💾 تصدير")
        export.setFixedHeight(38)
        export.setCursor(Qt.PointingHandCursor)
        export.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.INFO};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {Colors.INFO_HOVER}; }}
        """)
        export.clicked.connect(self.export_logs)
        clear = QPushButton("🗑️ مسح")
        clear.setFixedHeight(38)
        clear.setCursor(Qt.PointingHandCursor)
        clear.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.DANGER};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {Colors.DANGER_HOVER}; }}
        """)
        clear.clicked.connect(self.clear_logs)
        btns.addWidget(refresh)
        btns.addWidget(export)
        btns.addStretch()
        btns.addWidget(clear)
        layout.addLayout(btns)
        QTimer.singleShot(50, self.load_logs)

    def load_logs(self):
        lm = LogManager()
        entries = lm.read_logs(2000)
        lines = []
        for e in entries:
            lines.append(f"[{e.get('timestamp')}] [{e.get('level')}] "
                         f"id={e.get('download_id')} url={e.get('url')}\n"
                         f"{e.get('message')}\n")
        self.log_view.setPlainText('\n'.join(lines[::-1]))

    def clear_logs(self):
        lm = LogManager()
        if QMessageBox.question(self, 'تأكيد', 'مسح السجل نهائياً؟',
                                QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No) == QMessageBox.Yes:
            lm.clear()
            self.load_logs()

    def export_logs(self):
        path, _ = QFileDialog.getSaveFileName(self, 'تصدير', os.path.expanduser('~'),
                                               'JSONL (*.jsonl);;All (*)')
        if not path:
            return
        lm = LogManager()
        try:
            with open(path, 'w', encoding='utf-8') as dst:
                if os.path.exists(lm.path):
                    with open(lm.path, 'r', encoding='utf-8') as src:
                        dst.write(src.read())
            QMessageBox.information(self, 'تم', 'Exporté')
        except Exception as e:
            QMessageBox.warning(self, 'خطأ', str(e))
'''

SOURCE_FILES['dialogs/settings_dialog.py'] = r'''"""Boîte de dialogue des paramètres."""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QComboBox, QGroupBox, QCheckBox, QTimeEdit,
                              QPushButton)
from PyQt5.QtCore import QTime, Qt
from .log_dialog import LogDialog
from ..ui.theme import Colors


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle('⚙️ إعدادات')
        self.setMinimumWidth(480)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        header = QLabel("⚙️ إعدادات التطبيق")
        header.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(header)

        lang_group = QGroupBox("اللغة")
        lg = QVBoxLayout(lang_group)
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(['العربية', 'Français', 'English'])
        lg.addWidget(self.lang_combo)
        layout.addWidget(lang_group)

        sched_group = QGroupBox("جدولة التحميلات")
        sg = QVBoxLayout(sched_group)
        self.sched_checkbox = QCheckBox('تفعيل الجدولة اليومية')
        self.sched_time = QTimeEdit()
        self.sched_time.setDisplayFormat('HH:mm')
        sg.addWidget(self.sched_checkbox)
        tl = QHBoxLayout()
        tl.addWidget(QLabel('ابدأ عند:'))
        tl.addWidget(self.sched_time)
        tl.addStretch()
        sg.addLayout(tl)
        layout.addWidget(sched_group)
        layout.addStretch()

        btns = QHBoxLayout()
        btns.setSpacing(8)
        logs = QPushButton("📋 عرض السجل")
        logs.setFixedHeight(40)
        logs.setCursor(Qt.PointingHandCursor)
        logs.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_SIDEBAR};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {Colors.BG_HOVER}; }}
        """)
        logs.clicked.connect(lambda: LogDialog(self.parent).exec_())
        cancel = QPushButton('إلغاء')
        cancel.setFixedHeight(40)
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_SIDEBAR};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 0 20px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {Colors.BG_HOVER}; }}
        """)
        cancel.clicked.connect(self.reject)
        save = QPushButton('💾 حفظ')
        save.setFixedHeight(40)
        save.setCursor(Qt.PointingHandCursor)
        save.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 24px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {Colors.PRIMARY_HOVER}; }}
        """)
        save.clicked.connect(self.save)
        btns.addWidget(logs)
        btns.addStretch()
        btns.addWidget(cancel)
        btns.addWidget(save)
        layout.addLayout(btns)

        if self.parent and hasattr(self.parent, 'db_manager'):
            lang = self.parent.db_manager.get_preference('app_language', 'العربية')
            idx = self.lang_combo.findText(lang)
            if idx >= 0:
                self.lang_combo.setCurrentIndex(idx)
            enabled = self.parent.db_manager.get_preference('scheduler_enabled', '0')
            self.sched_checkbox.setChecked(str(enabled) in ('1', 'True', 'true'))
            t = self.parent.db_manager.get_preference('scheduler_time', '02:00')
            try:
                hh, mm = t.split(':')
                self.sched_time.setTime(QTime(int(hh), int(mm)))
            except Exception:
                pass

    def save(self):
        if not self.parent or not hasattr(self.parent, 'db_manager'):
            return
        self.parent.db_manager.save_preference('app_language', self.lang_combo.currentText())
        self.parent.db_manager.save_preference(
            'scheduler_enabled', '1' if self.sched_checkbox.isChecked() else '0')
        self.parent.db_manager.save_preference(
            'scheduler_time', self.sched_time.time().toString('HH:mm'))
        self.accept()
'''

SOURCE_FILES['dialogs/extension_dialog.py'] = r'''"""Boîte de dialogue pour l'extension navigateur."""
import os
import sys
from pathlib import Path
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QLineEdit, QPushButton, QMessageBox, QApplication)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices
from ..ui.theme import Colors


class ExtensionDialog(QDialog):
    def __init__(self, ext_path, parent=None):
        super().__init__(parent)
        self.ext_path = ext_path
        self.setMinimumWidth(600)
        self.initUI()

    def initUI(self):
        self.setWindowTitle("🧩 تثبيت إضافة المتصفح")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        header = QLabel("🧩 تثبيت الإضافة")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {Colors.PRIMARY};")
        layout.addWidget(header)
        subtitle = QLabel("لربط المتصفح بالبرنامج مباشرة، اتبع الخطوات التالية:")
        subtitle.setAlignment(Qt.AlignRight)
        subtitle.setStyleSheet(f"font-size: 13px; color: {Colors.TEXT_SECONDARY};")
        layout.addWidget(subtitle)
        steps = QLabel(
            "<div style='direction: rtl; text-align: right; line-height: 1.8;'>"
            "<b>1.</b> اضغط على زر <b>فتح صفحة الإضافات</b> أدناه.<br>"
            "<b>2.</b> فعّل <b>وضع المطور (Developer Mode)</b> أعلى الصفحة.<br>"
            "<b>3.</b> اضغط على <b>تحميل إضافة غير محزمة (Load unpacked)</b>.<br>"
            "<b>4.</b> الصق المسار المنسوخ تلقائياً واضغط Enter."
            "</div>")
        steps.setWordWrap(True)
        steps.setStyleSheet(
            f"background-color: {Colors.INFO_LIGHT}; color: {Colors.TEXT_PRIMARY}; "
            f"padding: 14px; border-radius: 8px; "
            f"border-left: 4px solid {Colors.PRIMARY};")
        layout.addWidget(steps)

        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        self.path_edit = QLineEdit(str(self.ext_path))
        self.path_edit.setReadOnly(True)
        copy_btn = QPushButton("📋 نسخ")
        copy_btn.setFixedHeight(38)
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {Colors.PRIMARY_HOVER}; }}
        """)
        copy_btn.clicked.connect(self.copy_path)
        path_row.addWidget(copy_btn)
        path_row.addWidget(self.path_edit)
        layout.addLayout(path_row)

        btns = QHBoxLayout()
        btns.setSpacing(10)
        open_folder = QPushButton("📁 فتح المجلد")
        open_folder.setFixedHeight(46)
        open_folder.setCursor(Qt.PointingHandCursor)
        open_folder.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.INFO};
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{ background-color: {Colors.INFO_HOVER}; }}
        """)
        open_folder.clicked.connect(self.open_folder)
        open_page = QPushButton("🌐 فتح صفحة الإضافات")
        open_page.setFixedHeight(46)
        open_page.setCursor(Qt.PointingHandCursor)
        open_page.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SUCCESS};
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{ background-color: {Colors.SUCCESS_HOVER}; }}
        """)
        open_page.clicked.connect(self.open_extensions_page)
        btns.addWidget(open_folder)
        btns.addWidget(open_page)
        layout.addLayout(btns)

        close = QPushButton("إغلاق")
        close.setFixedHeight(40)
        close.setCursor(Qt.PointingHandCursor)
        close.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_SIDEBAR};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {Colors.BG_HOVER}; }}
        """)
        close.clicked.connect(self.accept)
        layout.addWidget(close)
        self.copy_path(silent=True)

    def copy_path(self, silent=False):
        QApplication.clipboard().setText(str(self.ext_path))
        if not silent:
            QMessageBox.information(self, "تم", "تم النسخ")

    def open_extensions_page(self):
        url = "chrome://extensions/"
        QApplication.clipboard().setText(url)
        QDesktopServices.openUrl(QUrl(url))

    def open_folder(self):
        try:
            if sys.platform == 'win32':
                os.startfile(os.path.normpath(str(self.ext_path)))
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.ext_path)))
        except Exception:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.ext_path)))
'''

# ---------- tabs ----------
SOURCE_FILES['tabs/__init__.py'] = '"""Tabs package."""\n'

SOURCE_FILES['tabs/history_tab.py'] = r'''"""Onglet d'historique."""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QScrollArea, QFrame, QMessageBox, QLabel)
from PyQt5.QtCore import QTimer, Qt
from ..widgets.history_item import HistoryItemWidget
from ..ui.theme import Colors


class HistoryTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        header = QLabel("📜 سجل التحميلات")
        header.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(header)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        refresh = QPushButton("🔄 تحديث")
        refresh.setFixedHeight(38)
        refresh.setCursor(Qt.PointingHandCursor)
        refresh.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.INFO};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 18px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {Colors.INFO_HOVER}; }}
        """)
        refresh.clicked.connect(self.refresh_history)
        clear = QPushButton("🗑️ مسح السجل")
        clear.setFixedHeight(38)
        clear.setCursor(Qt.PointingHandCursor)
        clear.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.DANGER};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 18px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {Colors.DANGER_HOVER}; }}
        """)
        clear.clicked.connect(self.clear_all_history)
        controls.addWidget(refresh)
        controls.addWidget(clear)
        controls.addStretch()
        layout.addLayout(controls)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.area = QWidget()
        self.area.setStyleSheet("background: transparent;")
        self.history_layout = QVBoxLayout(self.area)
        self.history_layout.setContentsMargins(0, 0, 8, 0)
        self.history_layout.setSpacing(10)
        self.history_layout.addStretch()
        self.scroll.setWidget(self.area)
        layout.addWidget(self.scroll, 1)
        QTimer.singleShot(500, self.refresh_history)

    def refresh_history(self):
        if not hasattr(self.parent, 'db_manager') or not self.parent.db_manager:
            return
        while self.history_layout.count() > 1:
            item = self.history_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for record in self.parent.db_manager.get_history(200):
            self.history_layout.insertWidget(
                self.history_layout.count() - 1,
                HistoryItemWidget(record, self))

    def delete_item(self, download_id, widget):
        if QMessageBox.question(self, 'تأكيد', 'حذف هذا العنصر؟',
                                 QMessageBox.Yes | QMessageBox.No,
                                 QMessageBox.No) == QMessageBox.Yes:
            if hasattr(self.parent, 'db_manager') and self.parent.db_manager:
                if self.parent.db_manager.delete_history_item(download_id):
                    widget.deleteLater()

    def clear_all_history(self):
        if QMessageBox.question(self, 'تأكيد', 'مسح كل السجل؟',
                                 QMessageBox.Yes | QMessageBox.No,
                                 QMessageBox.No) == QMessageBox.Yes:
            if hasattr(self.parent, 'db_manager') and self.parent.db_manager:
                self.parent.db_manager.clear_history()
                self.refresh_history()
'''

# ---------- UI Main Window ----------
SOURCE_FILES['ui/main_window.py'] = r'''"""Fenêtre principale - version modulaire avec UI moderne."""
import os
import sys
import json
import math
import threading
import urllib.parse
import secrets
import logging
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QLineEdit, QPushButton, QProgressBar,
                              QComboBox, QFileDialog, QMessageBox, QTextEdit,
                              QFrame, QCheckBox, QTabWidget, QTableWidget,
                              QTableWidgetItem, QHeaderView, QScrollArea,
                              QAction, QStatusBar, QGroupBox, QInputDialog,
                              QDialog, QApplication, QSizePolicy)
from PyQt5.QtCore import (Qt, QThread, pyqtSignal, pyqtSlot, QUrl, QTimer,
                          QMetaObject, Q_ARG)
from PyQt5.QtGui import QIcon

from ..core.database import DatabaseManager
from ..core.logger import LogManager
from ..core.platforms import detect_platform
from ..workers.download_worker import DownloadWorker
from ..workers.torrent_worker import TorrentWorker
from ..widgets.download_item import DownloadItemWidget
from ..dialogs.settings_dialog import SettingsDialog
from ..dialogs.extension_dialog import ExtensionDialog
from ..tabs.history_tab import HistoryTab
from ..utils.icon_utils import get_app_icon_path
from ..utils.system_utils import (SLEEP_PREVENTION_AVAILABLE,
                                   ES_CONTINUOUS, ES_SYSTEM_REQUIRED)
from .theme import Colors

try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except ImportError:
    YTDLP_AVAILABLE = False

try:
    import aria2p
    ARIA2P_AVAILABLE = True
except ImportError:
    ARIA2P_AVAILABLE = False

import ctypes


class NetworkChecker(QThread):
    connection_status = pyqtSignal(bool)

    def run(self):
        import socket
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            self.connection_status.emit(True)
        except Exception:
            self.connection_status.emit(False)


class SafeStatusBar(QStatusBar):
    def showMessage(self, text, msecs=0):
        if threading.current_thread() is threading.main_thread():
            super().showMessage(text, msecs)
        else:
            QMetaObject.invokeMethod(self, "_show_message", Qt.QueuedConnection,
                                      Q_ARG(str, text), Q_ARG(int, msecs))

    @pyqtSlot(str, int)
    def _show_message(self, text, msecs):
        super().showMessage(text, msecs)


def make_scroll_area():
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    return scroll


class YouTubeDownloaderPro(QMainWindow):
    external_download_signal = pyqtSignal(str)
    browser_download_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.downloads = {}
        self.download_items = {}
        self.torrent_downloads = {}
        self.torrent_items = {}
        self.server_clients = {}
        self.server_clients_lock = threading.Lock()
        self._http_server = None
        self.server_port = 9191
        self.server_host = '0.0.0.0'
        self.server_running = False
        self.finalized_downloads = set()
        self.next_id = 1
        self.active_downloads_count = 0
        self.checker = None
        self.db_manager = DatabaseManager()
        self.db_flush_timer = QTimer(self)
        self.db_flush_timer.setSingleShot(True)
        self.db_flush_timer.timeout.connect(self.flush_db_updates)
        self.last_clipboard_url = ""
        self.pending_ui_updates = {}
        self.pending_ui_lock = threading.Lock()
        self.ui_update_timer = QTimer(self)
        self.ui_update_timer.setInterval(100)
        self.ui_update_timer.timeout.connect(self.flush_ui_updates)
        self.ui_update_timer.start()
        self.sequential_mode = True
        self.sequential_queue = []
        self.current_sequential_download = None
        self.sequential_running = False
        self.sequential_checkbox = None
        self.pending_remove_timers = {}
        self.default_path = str(Path.home() / "Downloads" / "TK Downloads")
        Path(self.default_path).mkdir(parents=True, exist_ok=True)
        self.initUI()
        self.external_download_signal.connect(self.handle_external_download, Qt.QueuedConnection)
        self.browser_download_signal.connect(self.start_download_from_browser, Qt.QueuedConnection)
        self.scheduler_timer = QTimer(self)
        self.scheduler_timer.setInterval(60 * 1000)
        self.scheduler_timer.timeout.connect(self.check_scheduler)
        self.scheduler_enabled = False
        self.scheduler_time = '02:00'
        QTimer.singleShot(100, self.delayed_init)

    def delayed_init(self):
        try:
            self.load_settings()
        except Exception:
            logging.exception("load_settings failed")
        try:
            self.setup_clipboard_monitor()
        except Exception:
            logging.exception("setup_clipboard_monitor failed")
        try:
            self.start_local_server()
        except Exception:
            logging.exception("start_local_server failed")
        QTimer.singleShot(1000, self.restore_active_downloads)
        try:
            self.scheduler_timer.start()
        except Exception:
            pass

    def restore_active_downloads(self):
        if not self.db_manager:
            return
        try:
            active = self.db_manager.get_active_downloads()
        except Exception:
            return
        if not active:
            return
        for row in active:
            if len(row) >= 10:
                did, url, quality, is_audio, save_path, title, use_cookies, qo, is_seq, platform = row[:10]
            else:
                did, url, quality, is_audio, save_path, title, use_cookies, qo, is_seq = row[:9]
                platform = ""
            if is_seq and qo > 0:
                self.sequential_queue.append({
                    'download_id': did, 'url': url, 'save_path': save_path,
                    'quality': quality, 'is_audio': bool(is_audio),
                    'use_cookies': bool(use_cookies), 'queue_order': qo,
                    'status': 'في الانتظار', 'platform': platform,
                    'display_name': title or self.get_queue_display_name(url),
                })
                widget = self.add_download_widget_only(did, url, "⏳ في الانتظار",
                                                        quality, bool(is_audio),
                                                        bool(use_cookies), section='waiting')
                widget.update_title(title or url)
            else:
                self.add_download(did, url, save_path, quality, bool(is_audio),
                                   bool(use_cookies))
                if title and did in self.download_items:
                    self.download_items[did].update_title(title)
        if self.sequential_queue and not self.sequential_running:
            QTimer.singleShot(2000, self.start_sequential_download)

    def flush_db_updates(self):
        if hasattr(self, 'db_manager') and self.db_manager:
            self.db_manager.flush_updates()

    def schedule_db_flush(self, delay=2500):
        if hasattr(self, 'db_flush_timer'):
            self.db_flush_timer.start(delay)

    def get_queue_display_name(self, url, fallback="ملف جديد"):
        try:
            parsed = urllib.parse.urlparse(url)
            host = parsed.netloc.lower().replace('www.', '')
            path_name = os.path.basename(parsed.path)
            path_name = urllib.parse.unquote(path_name).split('?')[0].split('#')[0].strip()
            if path_name and '.' in path_name:
                return path_name
            if 'youtube' in host or 'youtu.be' in host:
                qs = urllib.parse.parse_qs(parsed.query)
                vid = qs.get('v', [None])[0]
                if vid:
                    return f"YouTube Video ({vid})"
            if path_name:
                return path_name
            if host:
                return f"{host} link"
        except Exception:
            pass
        return fallback

    def initUI(self):
        self.setWindowTitle(f"TK Downloader Pro - v1.2.0")
        icon_path = get_app_icon_path()
        if icon_path:
            self.setWindowIcon(QIcon(str(icon_path)))
        self.setMinimumSize(1100, 800)

        menubar = self.menuBar()
        file_menu = menubar.addMenu('📁 Fichier')
        exit_action = QAction('❌ Quitter', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        integ = menubar.addMenu('🌐 Navigateur')
        ext_action = QAction("🧩 Installer l'extension", self)
        ext_action.triggered.connect(self.install_extension_help)
        integ.addAction(ext_action)
        settings_action = QAction('⚙️ إعدادات', self)
        settings_action.triggered.connect(self.open_settings_dialog)
        integ.addAction(settings_action)

        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        status_card = QFrame()
        status_card.setStyleSheet(
            f"background-color: {Colors.BG_CARD}; "
            f"border: 1px solid {Colors.BORDER}; border-radius: 12px;")
        sl = QHBoxLayout(status_card)
        sl.setContentsMargins(18, 14, 18, 14)
        sl.setSpacing(16)
        self.downloads_count_label = QLabel("📥 لا توجد تحميلات")
        self.downloads_count_label.setStyleSheet(
            f"font-weight: 700; font-size: 13px; color: {Colors.TEXT_PRIMARY};")
        self.downloads_count_label.setMinimumWidth(180)
        self.overall_progress_bar = QProgressBar()
        self.overall_progress_bar.setFixedHeight(14)
        self.overall_progress_bar.setValue(0)
        self.overall_status_label = QLabel("جاهز")
        self.overall_status_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; font-weight: 600;")
        self.overall_status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.overall_status_label.setMinimumWidth(140)
        sl.addWidget(self.downloads_count_label)
        sl.addWidget(self.overall_progress_bar, 1)
        sl.addWidget(self.overall_status_label)
        main_layout.addWidget(status_card)

        self.statusBar = SafeStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("✅ جاهز — أضف رابطاً للبدء")

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        main_layout.addWidget(self.tabs, 1)
        self.setCentralWidget(main_widget)

        self.single_tab = QWidget()
        self.setup_single_tab()
        self.tabs.addTab(self.single_tab, "📹 تحميل مفرد")

        self.batch_tab = QWidget()
        self.setup_batch_tab()
        self.tabs.addTab(self.batch_tab, "📚 تحميل جماعي")

        self.torrent_tab = QWidget()
        self.setup_torrent_tab()
        self.tabs.addTab(self.torrent_tab, "🌀 Torrents")

        self.active_tab = QWidget()
        self.setup_active_tab()
        self.tabs.addTab(self.active_tab, "⬇️ التنزيلات النشطة")

        self.history_tab = HistoryTab(self)
        self.tabs.addTab(self.history_tab, "📜 السجل")

        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self.check_network)
        self.check_timer.start(5000)

    def setup_single_tab(self):
        outer_layout = QVBoxLayout(self.single_tab)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        scroll = make_scroll_area()
        outer_layout.addWidget(scroll)
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        header = QLabel("📹 تحميل من رابط")
        header.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(header)

        url_group = QGroupBox("🔗 الرابط")
        ul = QVBoxLayout(url_group)
        ul.setSpacing(8)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(
            "https://www.youtube.com/... أو https://site.com/file.zip")
        self.url_input.setMinimumHeight(42)
        ul.addWidget(self.url_input)
        layout.addWidget(url_group)

        opts = QGroupBox("⚙️ الخيارات")
        ol = QVBoxLayout(opts)
        ol.setSpacing(10)
        ql = QHBoxLayout()
        qlabel = QLabel("الجودة:")
        qlabel.setStyleSheet(
            f"font-weight: 600; color: {Colors.TEXT_PRIMARY}; background: transparent;")
        ql.addWidget(qlabel)
        self.quality_combo = QComboBox()
        self.quality_combo.addItems([
            "Haute qualité (1080p)",
            "Moyenne qualité (720p)",
            "Basse qualité (360p)"
        ])
        self.quality_combo.setMinimumHeight(38)
        ql.addWidget(self.quality_combo, 1)
        ol.addLayout(ql)
        self.audio_checkbox = QCheckBox("🎵 وضع الصوت فقط (MP3)")
        ol.addWidget(self.audio_checkbox)
        self.clipboard_checkbox = QCheckBox("📋 مراقبة الحافظة تلقائياً")
        self.clipboard_checkbox.setChecked(True)
        ol.addWidget(self.clipboard_checkbox)
        self.cookies_checkbox = QCheckBox("🍪 استخدام كوكيز المتصفح")
        self.cookies_checkbox.setChecked(True)
        ol.addWidget(self.cookies_checkbox)
        layout.addWidget(opts)

        path_group = QGroupBox("💾 مكان الحفظ")
        pl = QHBoxLayout(path_group)
        pl.setSpacing(8)
        self.path_display = QLineEdit()
        self.path_display.setReadOnly(True)
        self.path_display.setMinimumHeight(38)
        self.path_display.setText(self.default_path)
        browse = QPushButton("📁 اختيار")
        browse.setFixedHeight(38)
        browse.setCursor(Qt.PointingHandCursor)
        browse.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_SIDEBAR};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {Colors.BG_HOVER}; }}
        """)
        browse.clicked.connect(self.browse_folder)
        pl.addWidget(self.path_display, 1)
        pl.addWidget(browse)
        layout.addWidget(path_group)

        btns = QHBoxLayout()
        btns.setSpacing(10)
        dl_btn = QPushButton("🚀 بدء التحميل")
        dl_btn.setFixedHeight(52)
        dl_btn.setCursor(Qt.PointingHandCursor)
        dl_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: 700;
            }}
            QPushButton:hover {{ background-color: {Colors.PRIMARY_HOVER}; }}
        """)
        dl_btn.clicked.connect(self.start_single_download)
        btns.addWidget(dl_btn, 1)
        self.sequential_btn = QPushButton("⏳ إلغاء التسلسل")
        self.sequential_btn.setFixedHeight(52)
        self.sequential_btn.setCheckable(True)
        self.sequential_btn.setChecked(True)
        self.sequential_btn.setCursor(Qt.PointingHandCursor)
        self.sequential_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.WARNING};
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 13px;
                font-weight: 700;
                padding: 0 20px;
            }}
            QPushButton:hover {{ background-color: {Colors.WARNING_HOVER}; }}
            QPushButton:checked {{ background-color: {Colors.SUCCESS}; }}
        """)
        self.sequential_btn.clicked.connect(self.toggle_sequential_mode)
        btns.addWidget(self.sequential_btn, 1)
        layout.addLayout(btns)

        info = QLabel(
            "🌐 المنصات المدعومة: YouTube • Facebook • Instagram • TikTok • "
            "Twitter/X • Vimeo • Dailymotion • Twitch • Spotify • SoundCloud ...")
        info.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: 11px; "
            f"background-color: {Colors.BG_SIDEBAR}; "
            f"padding: 10px 14px; border-radius: 8px;")
        info.setWordWrap(True)
        layout.addWidget(info)
        layout.addStretch()
        scroll.setWidget(container)

    def toggle_sequential_mode(self):
        self.sequential_mode = self.sequential_btn.isChecked()
        self.sequential_btn.setText(
            "⏳ إلغاء التسلسل" if self.sequential_mode else "⏳ تفعيل التسلسل")
        if self.sequential_checkbox:
            self.sequential_checkbox.setChecked(self.sequential_mode)

    def setup_batch_tab(self):
        outer = QVBoxLayout(self.batch_tab)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = make_scroll_area()
        outer.addWidget(scroll)
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        header = QLabel("📚 تحميل جماعي")
        header.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(header)

        url_group = QGroupBox("📝 قائمة الروابط (رابط في كل سطر)")
        ul = QVBoxLayout(url_group)
        self.urls_list = QTextEdit()
        self.urls_list.setPlaceholderText(
            "https://www.youtube.com/watch?v=...\n"
            "https://www.facebook.com/...\n"
            "https://www.instagram.com/...\n"
            "https://site.com/file.zip")
        self.urls_list.setMinimumHeight(180)
        ul.addWidget(self.urls_list)
        layout.addWidget(url_group)

        opts = QGroupBox("⚙️ الخيارات")
        ol = QVBoxLayout(opts)
        ol.setSpacing(10)
        ql = QHBoxLayout()
        qlabel = QLabel("الجودة:")
        qlabel.setStyleSheet(
            f"font-weight: 600; color: {Colors.TEXT_PRIMARY}; background: transparent;")
        ql.addWidget(qlabel)
        self.batch_quality = QComboBox()
        self.batch_quality.addItems([
            "Haute qualité (1080p)",
            "Moyenne qualité (720p)",
            "Basse qualité (360p)"
        ])
        self.batch_quality.setMinimumHeight(38)
        ql.addWidget(self.batch_quality, 1)
        ol.addLayout(ql)
        self.batch_audio = QCheckBox("🎵 وضع الصوت فقط لكل الروابط")
        ol.addWidget(self.batch_audio)
        self.batch_cookies = QCheckBox("🍪 استخدام كوكيز المتصفح")
        self.batch_cookies.setChecked(True)
        ol.addWidget(self.batch_cookies)
        self.batch_sequential = QCheckBox("🔁 تحميل تسلسلي")
        ol.addWidget(self.batch_sequential)
        layout.addWidget(opts)

        start_btn = QPushButton("🎬 بدء التحميل الجماعي")
        start_btn.setFixedHeight(50)
        start_btn.setCursor(Qt.PointingHandCursor)
        start_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SUCCESS};
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{ background-color: {Colors.SUCCESS_HOVER}; }}
        """)
        start_btn.clicked.connect(self.start_batch_download)
        layout.addWidget(start_btn)

        table_group = QGroupBox("📊 حالة التحميلات")
        tl = QVBoxLayout(table_group)
        self.batch_table = QTableWidget()
        self.batch_table.setColumnCount(5)
        self.batch_table.setHorizontalHeaderLabels(
            ["الرابط", "الحالة", "التقدم", "السرعة", "ID"])
        self.batch_table.horizontalHeader().setStretchLastSection(True)
        self.batch_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.batch_table.setColumnHidden(4, True)
        self.batch_table.setAlternatingRowColors(True)
        self.batch_table.setMinimumHeight(250)
        tl.addWidget(self.batch_table)
        layout.addWidget(table_group)
        layout.addStretch()
        scroll.setWidget(container)

    def setup_torrent_tab(self):
        outer = QVBoxLayout(self.torrent_tab)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = make_scroll_area()
        outer.addWidget(scroll)
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        header = QLabel("🌀 Torrents")
        header.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(header)

        src_group = QGroupBox("🔗 المصدر")
        sl = QVBoxLayout(src_group)
        sl.setSpacing(10)
        il = QHBoxLayout()
        self.torrent_input = QLineEdit()
        self.torrent_input.setPlaceholderText(
            "magnet:?xt=urn:btih:... أو مسار ملف .torrent")
        self.torrent_input.setMinimumHeight(42)
        browse = QPushButton("📂 فتح")
        browse.setFixedHeight(42)
        browse.setCursor(Qt.PointingHandCursor)
        browse.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_SIDEBAR};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {Colors.BG_HOVER}; }}
        """)
        browse.clicked.connect(self.browse_torrent_file)
        il.addWidget(self.torrent_input, 1)
        il.addWidget(browse)
        sl.addLayout(il)

        pl = QHBoxLayout()
        plabel = QLabel("📁 مكان الحفظ:")
        plabel.setStyleSheet(
            f"font-weight: 600; color: {Colors.TEXT_PRIMARY}; background: transparent;")
        pl.addWidget(plabel)
        self.torrent_path_display = QLineEdit()
        self.torrent_path_display.setReadOnly(True)
        self.torrent_path_display.setText(self.default_path)
        self.torrent_path_display.setMinimumHeight(38)
        browse_p = QPushButton("📁 اختيار")
        browse_p.setFixedHeight(38)
        browse_p.setCursor(Qt.PointingHandCursor)
        browse_p.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_SIDEBAR};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {Colors.BG_HOVER}; }}
        """)
        browse_p.clicked.connect(self.browse_torrent_path)
        pl.addWidget(self.torrent_path_display, 1)
        pl.addWidget(browse_p)
        sl.addLayout(pl)
        layout.addWidget(src_group)

        start_btn = QPushButton("🚀 بدء تحميل Torrent")
        start_btn.setFixedHeight(50)
        start_btn.setCursor(Qt.PointingHandCursor)
        start_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SUCCESS};
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{ background-color: {Colors.SUCCESS_HOVER}; }}
        """)
        start_btn.clicked.connect(self.start_torrent_download)
        layout.addWidget(start_btn)

        list_group = QGroupBox("📊 Torrents النشطة")
        ll = QVBoxLayout(list_group)
        self.torrent_scroll = make_scroll_area()
        self.torrent_area = QWidget()
        self.torrent_area.setStyleSheet("background: transparent;")
        self.torrent_layout = QVBoxLayout(self.torrent_area)
        self.torrent_layout.setContentsMargins(0, 0, 8, 0)
        self.torrent_layout.setSpacing(10)
        self.torrent_layout.addStretch()
        self.torrent_scroll.setWidget(self.torrent_area)
        self.torrent_scroll.setMinimumHeight(250)
        ll.addWidget(self.torrent_scroll)
        layout.addWidget(list_group)
        layout.addStretch()
        scroll.setWidget(container)

    def browse_torrent_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "اختر ملف Torrent", "", "Torrent (*.torrent)")
        if f:
            self.torrent_input.setText(f)

    def browse_torrent_path(self):
        d = QFileDialog.getExistingDirectory(self, "اختر مجلد الحفظ")
        if d:
            self.torrent_path_display.setText(d)

    def start_torrent_download(self):
        src = self.torrent_input.text().strip()
        if not src:
            QMessageBox.warning(self, "خطأ", "أدخل رابط magnet أو ملف .torrent")
            return
        did = str(self.next_id)
        self.next_id += 1
        self.add_torrent_download(did, src, self.torrent_path_display.text())
        self.torrent_input.clear()

    def add_torrent_download(self, download_id, source, save_path):
        try:
            worker = TorrentWorker(download_id, source, save_path)
            worker.progress_signal.connect(self.update_torrent_progress, Qt.QueuedConnection)
            worker.status_signal.connect(self.update_torrent_status, Qt.QueuedConnection)
            worker.finished_signal.connect(self.torrent_finished, Qt.QueuedConnection)
            worker.title_signal.connect(self.on_torrent_title, Qt.QueuedConnection)
            widget = self.create_torrent_widget(download_id, source)
            self.torrent_layout.insertWidget(0, widget)
            self.torrent_items[download_id] = widget
            self.torrent_downloads[download_id] = worker
            worker.start()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", str(e))

    def create_torrent_widget(self, download_id, source):
        frame = QFrame()
        frame.setStyleSheet(
            f"background-color: {Colors.BG_CARD}; "
            f"border: 1px solid {Colors.BORDER}; border-radius: 10px;")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)
        title = QLabel(source[:80] + "..." if len(source) > 80 else source)
        title.setStyleSheet(
            f"font-weight: 600; color: {Colors.TEXT_PRIMARY}; background: transparent;")
        title.setWordWrap(True)
        status = QLabel("⏳ بدء...")
        status.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; background: transparent;")
        progress = QProgressBar()
        progress.setFixedHeight(8)
        progress.setTextVisible(False)
        speed = QLabel("0 KB/s")
        speed.setStyleSheet(
            f"color: {Colors.SUCCESS}; font-size: 12px; font-weight: 600; background: transparent;")
        btns = QHBoxLayout()
        btns.setSpacing(6)
        pause = QPushButton("⏸️")
        pause.setFixedSize(36, 36)
        pause.setCursor(Qt.PointingHandCursor)
        pause.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.WARNING};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
            }}
            QPushButton:hover {{ background-color: {Colors.WARNING_HOVER}; }}
        """)
        pause.clicked.connect(lambda: self.pause_torrent(download_id))
        resume = QPushButton("▶️")
        resume.setFixedSize(36, 36)
        resume.setCursor(Qt.PointingHandCursor)
        resume.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SUCCESS};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
            }}
            QPushButton:hover {{ background-color: {Colors.SUCCESS_HOVER}; }}
        """)
        resume.clicked.connect(lambda: self.resume_torrent(download_id))
        resume.hide()
        cancel = QPushButton("❌")
        cancel.setFixedSize(36, 36)
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.DANGER};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
            }}
            QPushButton:hover {{ background-color: {Colors.DANGER_HOVER}; }}
        """)
        cancel.clicked.connect(lambda: self.cancel_torrent(download_id))
        btns.addWidget(pause)
        btns.addWidget(resume)
        btns.addWidget(cancel)
        btns.addStretch()
        layout.addWidget(title)
        layout.addWidget(status)
        layout.addWidget(progress)
        layout.addWidget(speed)
        layout.addLayout(btns)
        frame.title_label = title
        frame.status_label = status
        frame.progress_bar = progress
        frame.speed_label = speed
        frame.pause_btn = pause
        frame.resume_btn = resume
        frame.cancel_btn = cancel
        return frame

    def on_torrent_title(self, did, title):
        if did in self.torrent_items:
            self.torrent_items[did].title_label.setText(title[:80])

    def update_torrent_progress(self, p, did, speed):
        if did in self.torrent_items:
            w = self.torrent_items[did]
            w.progress_bar.setValue(p)
            w.speed_label.setText(speed)

    def update_torrent_status(self, did, status):
        if did in self.torrent_items:
            w = self.torrent_items[did]
            w.status_label.setText(status)
            if "Paused" in status:
                w.pause_btn.hide()
                w.resume_btn.show()
            else:
                w.pause_btn.show()
                w.resume_btn.hide()

    def torrent_finished(self, did, success, msg):
        if did in self.torrent_items:
            w = self.torrent_items[did]
            w.status_label.setText("✅ مكتمل" if success else f"❌ {msg}")
            w.pause_btn.hide()
            w.resume_btn.hide()
        if did in self.torrent_downloads:
            del self.torrent_downloads[did]

    def pause_torrent(self, did):
        if did in self.torrent_downloads:
            self.torrent_downloads[did].pause()

    def resume_torrent(self, did):
        if did in self.torrent_downloads:
            self.torrent_downloads[did].resume()

    def cancel_torrent(self, did):
        if did in self.torrent_downloads:
            self.torrent_downloads[did].cancel()

    def setup_active_tab(self):
        layout = QVBoxLayout(self.active_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        header = QLabel("⬇️ التنزيلات النشطة")
        header.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(header)

        card = QFrame()
        card.setStyleSheet(
            f"background-color: {Colors.BG_CARD}; "
            f"border: 1px solid {Colors.BORDER}; border-radius: 12px;")
        cl = QHBoxLayout(card)
        cl.setContentsMargins(14, 12, 14, 12)
        cl.setSpacing(8)

        pause_all = QPushButton("⏸️ إيقاف الكل")
        pause_all.setFixedHeight(38)
        pause_all.setCursor(Qt.PointingHandCursor)
        pause_all.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.WARNING};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {Colors.WARNING_HOVER}; }}
        """)
        pause_all.clicked.connect(self.pause_all_downloads)

        resume_all = QPushButton("▶️ استئناف الكل")
        resume_all.setFixedHeight(38)
        resume_all.setCursor(Qt.PointingHandCursor)
        resume_all.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SUCCESS};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {Colors.SUCCESS_HOVER}; }}
        """)
        resume_all.clicked.connect(self.resume_all_downloads)

        cancel_all = QPushButton("❌ إلغاء الكل")
        cancel_all.setFixedHeight(38)
        cancel_all.setCursor(Qt.PointingHandCursor)
        cancel_all.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.DANGER};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {Colors.DANGER_HOVER}; }}
        """)
        cancel_all.clicked.connect(self.cancel_all_downloads)

        cl.addWidget(pause_all)
        cl.addWidget(resume_all)
        cl.addWidget(cancel_all)
        cl.addStretch()

        self.sequential_checkbox = QCheckBox("🔁 تسلسلي")
        self.sequential_checkbox.setChecked(True)
        self.sequential_checkbox.stateChanged.connect(self.on_sequential_checkbox_changed)
        cl.addWidget(self.sequential_checkbox)

        clear_q = QPushButton("🗑️ تنظيف")
        clear_q.setFixedHeight(38)
        clear_q.setCursor(Qt.PointingHandCursor)
        clear_q.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_SIDEBAR};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {Colors.BG_HOVER}; }}
        """)
        clear_q.clicked.connect(self.clear_sequential_queue)
        cl.addWidget(clear_q)

        reverse_q = QPushButton("⇅ عكس")
        reverse_q.setFixedHeight(38)
        reverse_q.setCursor(Qt.PointingHandCursor)
        reverse_q.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.INFO};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {Colors.INFO_HOVER}; }}
        """)
        reverse_q.clicked.connect(self.reverse_sequential_queue)
        cl.addWidget(reverse_q)

        layout.addWidget(card)

        self.active_scroll = make_scroll_area()
        self.active_downloads_area = QWidget()
        self.active_downloads_area.setStyleSheet("background: transparent;")
        self.active_downloads_layout = QVBoxLayout(self.active_downloads_area)
        self.active_downloads_layout.setContentsMargins(0, 0, 8, 0)
        self.active_downloads_layout.setSpacing(10)

        self.active_section_header = QLabel("🔄 التنزيلات النشطة")
        self.active_section_header.setStyleSheet(
            f"font-weight: 700; font-size: 13px; color: {Colors.PRIMARY}; padding: 6px 0;")
        self.active_downloads_layout.addWidget(self.active_section_header)

        self.waiting_section_header = QLabel("⏳ قائمة الانتظار")
        self.waiting_section_header.setStyleSheet(
            f"font-weight: 700; font-size: 13px; color: {Colors.WARNING_HOVER}; padding: 12px 0 6px 0;")
        self.active_downloads_layout.addWidget(self.waiting_section_header)

        self.active_downloads_layout.addStretch()
        self.active_scroll.setWidget(self.active_downloads_area)
        layout.addWidget(self.active_scroll, 1)

    def on_sequential_checkbox_changed(self, state):
        self.sequential_mode = state == Qt.Checked
        if hasattr(self, 'sequential_btn'):
            self.sequential_btn.setChecked(self.sequential_mode)

    def add_download_widget_only(self, did, url, status, quality, is_audio,
                                  use_cookies, section='active'):
        w = DownloadItemWidget(did, url, self)
        if section == 'waiting':
            idx = self.active_downloads_layout.indexOf(self.waiting_section_header)
            insert = idx + 1 if idx != -1 else max(0, self.active_downloads_layout.count() - 1)
        else:
            idx = self.active_downloads_layout.indexOf(self.waiting_section_header)
            insert = idx if idx != -1 else max(0, self.active_downloads_layout.count() - 1)
        self.active_downloads_layout.insertWidget(insert, w)
        self.download_items[did] = w
        w.update_status(status)
        return w

    def pin_download(self, did, pinned):
        if did not in self.download_items:
            return
        w = self.download_items[did]
        try:
            self.active_downloads_layout.removeWidget(w)
        except Exception:
            pass
        if pinned:
            self.active_downloads_layout.insertWidget(0, w)
        else:
            self.active_downloads_layout.insertWidget(
                max(0, self.active_downloads_layout.count() - 1), w)
        w.show()

    def setup_clipboard_monitor(self):
        self.clipboard = QApplication.clipboard()
        self.clipboard.dataChanged.connect(self.on_clipboard_changed)
        QTimer.singleShot(1500, self.on_clipboard_changed)

    def on_clipboard_changed(self):
        if not hasattr(self, 'clipboard_checkbox') or not self.clipboard_checkbox.isChecked():
            return
        text = self.clipboard.text().strip()
        if text == self.last_clipboard_url:
            return
        self.last_clipboard_url = text
        if text.startswith(("http://", "https://")):
            if QMessageBox.question(self, 'تم كشف رابط',
                                     f'هل تريد تحميله؟\n\n{text[:100]}...',
                                     QMessageBox.Yes | QMessageBox.No,
                                     QMessageBox.No) == QMessageBox.Yes:
                self.url_input.setText(text)
                self.tabs.setCurrentIndex(0)
                self.start_single_download()

    def update_sleep_prevention(self):
        if not SLEEP_PREVENTION_AVAILABLE:
            return
        try:
            state = ES_CONTINUOUS | ES_SYSTEM_REQUIRED if self.active_downloads_count > 0 else ES_CONTINUOUS
            ctypes.windll.kernel32.SetThreadExecutionState(state)
        except Exception:
            pass

    def update_overall_progress(self):
        if not hasattr(self, 'downloads_count_label'):
            return
        active = [w for w in self.download_items.values()
                  if hasattr(w, 'status_badge')
                  and not any(t in w.status_badge.text() for t in
                              ["Terminé", "تم", "Erreur", "خطأ", "❌", "Annulé"])]
        if not active:
            self.downloads_count_label.setText("📥 لا توجد تحميلات")
            self.overall_progress_bar.setValue(0)
            self.overall_status_label.setText("جاهز")
            return
        total = sum(w.progress_bar.value() for w in active if hasattr(w, 'progress_bar'))
        avg = int(total / len(active))
        self.overall_progress_bar.setValue(avg)
        self.downloads_count_label.setText(f"📥 {len(active)} تحميل جارٍ")
        self.overall_status_label.setText(f"التقدم العام: {avg}%")

    def browse_folder(self):
        d = QFileDialog.getExistingDirectory(self, "اختر مجلد الحفظ",
                                              self.path_display.text())
        if d:
            self.path_display.setText(d)
            if self.db_manager:
                self.db_manager.save_preference('save_path', d)

    def start_single_download(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "خطأ", "أدخل رابطاً")
            return
        if not url.startswith(("http://", "https://")):
            QMessageBox.warning(self, "خطأ",
                                "الرابط غير صالح — يجب أن يبدأ بـ http:// أو https://")
            return
        save_path = self.path_display.text()
        quality = self.quality_combo.currentText()
        is_audio = self.audio_checkbox.isChecked()
        use_cookies = self.cookies_checkbox.isChecked()
        did = str(self.next_id)
        self.next_id += 1
        if self.sequential_mode:
            self.add_to_sequential_queue(did, url, save_path, quality,
                                          is_audio, use_cookies)
            self.url_input.clear()
            self.tabs.setCurrentIndex(3)
            return
        self.tabs.setCurrentIndex(3)
        self.add_download(did, url, save_path, quality, is_audio, use_cookies)
        self.url_input.clear()

    def add_to_sequential_queue(self, did, url, save_path, quality, is_audio,
                                 use_cookies, display_name=None):
        qo = len(self.sequential_queue) + 1
        platform = detect_platform(url)
        name = display_name or self.get_queue_display_name(url)
        item = {'download_id': did, 'url': url, 'save_path': save_path,
                'quality': quality, 'is_audio': is_audio, 'use_cookies': use_cookies,
                'queue_order': qo, 'status': 'في الانتظار', 'platform': platform,
                'display_name': name}
        self.sequential_queue.append(item)
        w = self.add_download_widget_only(did, url, f"⏳ #{qo}", quality, is_audio,
                                            use_cookies, section='waiting')
        w.update_title(name)
        w.queue_order = qo
        w.update_status(f"⏳ في الانتظار (#{qo})")
        if self.db_manager:
            start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.db_manager.add_download(did, url, name, quality, is_audio,
                                          start_time, save_path, use_cookies, qo, True, platform)
        if not self.sequential_running:
            QTimer.singleShot(500, self.start_sequential_download)

    def start_sequential_download(self):
        if self.sequential_running or not self.sequential_queue:
            if not self.sequential_queue:
                self.sequential_running = False
            return
        while self.sequential_queue and self.sequential_queue[0]['status'] in ['Terminé', 'Annulé']:
            self.sequential_queue.pop(0)
        if not self.sequential_queue:
            self.sequential_running = False
            return
        item = self.sequential_queue[0]
        did = item['download_id']
        item['status'] = 'En cours'
        self.current_sequential_download = did
        self.sequential_running = True
        if did in self.download_items:
            self.download_items[did].update_status("🔄 جارٍ التحميل...")
        if self.db_manager:
            self.db_manager.update_download(did, "En cours")
        self.add_download(did, item['url'], item['save_path'], item['quality'],
                           item['is_audio'], item['use_cookies'])

    def on_sequential_download_finished(self, did, success, message):
        if did != self.current_sequential_download:
            return
        item = None
        if self.sequential_queue and self.sequential_queue[0]['download_id'] == did:
            item = self.sequential_queue[0]
        if item is not None:
            valid = False
            if success and isinstance(message, str):
                try:
                    if os.path.exists(message) and os.path.getsize(message) > 1024:
                        valid = True
                except Exception:
                    pass
            if valid:
                item['status'] = 'Terminé'
                self.sequential_queue.pop(0)
            else:
                item['status'] = 'Erreur'
        self.current_sequential_download = None
        self.sequential_running = False
        if item and item['status'] == 'Terminé':
            QTimer.singleShot(1000, self.start_sequential_download)

    def add_download(self, did, url, save_path, quality, is_audio, use_cookies=True,
                     resume_file_path=None):
        worker = DownloadWorker(did, url, save_path, quality, is_audio, use_cookies,
                                 resume_file_path=resume_file_path)
        worker.progress_signal.connect(self.update_download_progress, Qt.QueuedConnection)
        worker.status_signal.connect(self.update_download_status, Qt.QueuedConnection)
        worker.finished_signal.connect(self.download_finished, Qt.QueuedConnection)
        worker.title_signal.connect(self.on_title_received, Qt.QueuedConnection)

        if did not in self.download_items:
            w = self.add_download_widget_only(did, url, "🔄 جارٍ التحميل...", quality,
                                                is_audio, use_cookies, section='active')
        else:
            w = self.download_items[did]
            w.update_status("🔄 جارٍ التحميل...")
        w.url = url
        w.url_label.setText(url)
        w.save_path = save_path
        w.quality = quality
        w.is_audio = is_audio
        w.use_cookies = use_cookies
        w.resume_file_path = resume_file_path

        self.downloads[did] = worker
        self.finalized_downloads.discard(did)
        self.active_downloads_count += 1
        if self.db_manager and self.db_manager.conn:
            try:
                cursor = self.db_manager.get_cursor()
                if cursor:
                    cursor.execute('SELECT download_id FROM download_history WHERE download_id=?', (did,))
                    if not cursor.fetchone():
                        platform = detect_platform(url)
                        start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        self.db_manager.add_download(did, url, "Chargement...", quality,
                                                      is_audio, start_time, save_path,
                                                      use_cookies, 0, False, platform)
            except Exception:
                pass
        self.update_sleep_prevention()
        self.update_overall_progress()
        worker.start()

    def retry_download(self, did):
        if did not in self.download_items:
            return
        w = self.download_items[did]
        if w.url:
            self.cancel_scheduled_remove(did)
            self.add_download(did, w.url, w.save_path, w.quality, w.is_audio,
                               w.use_cookies, resume_file_path=w.resume_file_path)
            w.update_status("🔄 إعادة المحاولة...")
            w.progress_bar.setValue(0)
            w.hide_error_actions()

    def change_download_url(self, did, new_url):
        if did not in self.download_items:
            return
        w = self.download_items[did]
        w.url = new_url
        w.url_label.setText(new_url)
        if did in self.downloads and self.downloads[did].isRunning():
            self.cancel_download(did)
        self.cancel_scheduled_remove(did)
        self.add_download(did, new_url, w.save_path, w.quality, w.is_audio, w.use_cookies)

    def open_settings_dialog(self):
        dlg = SettingsDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            self.load_settings()

    def check_scheduler(self):
        try:
            if not self.scheduler_enabled:
                return
            now = datetime.now()
            hh, mm = (self.scheduler_time or '02:00').split(':')
            target = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
            if now >= target:
                today = now.strftime('%Y-%m-%d')
                last = self.db_manager.get_preference('scheduler_last_run', None)
                if last != today:
                    self.db_manager.save_preference('scheduler_last_run', today)
        except Exception:
            pass

    def on_title_received(self, did, title):
        if did in self.download_items:
            self.download_items[did].update_title(title)
        if self.db_manager and self.db_manager.conn:
            self.db_manager.enqueue_update(did, title=title)
            self.schedule_db_flush()

    def update_download_progress(self, value, did, speed):
        if self.db_manager and self.db_manager.conn:
            self.db_manager.enqueue_update(did, progress=value, speed=speed)
            self.schedule_db_flush()
        with self.pending_ui_lock:
            row = self.pending_ui_updates.get(did, {})
            row['progress'] = value
            row['speed'] = speed
            self.pending_ui_updates[did] = row

    def update_download_status(self, did, status):
        if did in self.download_items:
            self.download_items[did].update_status(status)
        if self.db_manager and self.db_manager.conn:
            self.db_manager.enqueue_update(did, status=status)
            self.schedule_db_flush()
        self.update_overall_progress()

    def flush_ui_updates(self):
        with self.pending_ui_lock:
            pending = dict(self.pending_ui_updates)
            self.pending_ui_updates.clear()
        for did, values in pending.items():
            w = self.download_items.get(did)
            if not w:
                continue
            if 'progress' in values:
                w.update_progress(values['progress'])
            if 'speed' in values:
                w.update_speed(values['speed'])

    def download_finished(self, did, success, message):
        current = self.downloads.get(did)
        if current is not None and self.sender() is not None and self.sender() is not current:
            return
        if did in self.finalized_downloads:
            return
        is_seq = (did == self.current_sequential_download or
                  any(i.get('download_id') == did for i in self.sequential_queue))
        if did in self.download_items:
            w = self.download_items[did]
            actual_success = success
            actual_message = message
            if success and message and os.path.exists(message):
                if os.path.getsize(message) < 1024:
                    actual_success = False
                    actual_message = "ملف فارغ أو تالف"
            elif success and not message:
                actual_success = False
                actual_message = "الملف غير موجود"
            if actual_success:
                w.file_path = actual_message
                w.update_status("✅ Terminé")
                w.progress_bar.setValue(100)
                if self.db_manager and self.db_manager.conn:
                    self.db_manager.enqueue_update(did, status="Terminé",
                                                    file_path=actual_message)
                    self.db_manager.flush_updates()
                if hasattr(self, 'history_tab'):
                    self.history_tab.refresh_history()
                if is_seq:
                    QTimer.singleShot(500, lambda: self.on_sequential_download_finished(
                        did, True, actual_message))
                self.schedule_remove_download(did, 3000)
            else:
                w.update_status(f"❌ {actual_message[:50]}")
                try:
                    lm = LogManager()
                    lm.log('error', actual_message, download_id=did, url=w.url)
                except Exception:
                    pass
                if self.db_manager and self.db_manager.conn:
                    self.db_manager.enqueue_update(did, status="Erreur",
                                                    error_message=actual_message)
                    self.db_manager.flush_updates()
                if is_seq:
                    self.finalized_downloads.add(did)
                    QTimer.singleShot(0, lambda: self.on_sequential_download_finished(
                        did, False, actual_message))
                    return
                self.schedule_remove_download(did, 5000)
            self.finalized_downloads.add(did)
            self.active_downloads_count = max(0, self.active_downloads_count - 1)
            self.update_sleep_prevention()
            self.update_overall_progress()

    def remove_download(self, did, delete_history=False):
        self.cancel_scheduled_remove(did)
        if did in self.download_items:
            w = self.download_items[did]
            try:
                w.cleanup()
            except Exception:
                pass
            try:
                self.active_downloads_layout.removeWidget(w)
            except Exception:
                pass
            w.setParent(None)
            w.deleteLater()
            del self.download_items[did]
        if did in self.downloads:
            worker = self.downloads[did]
            if worker.isRunning():
                worker.cancel()
                worker.wait(2000)
            worker.deleteLater()
            del self.downloads[did]
        if delete_history and self.db_manager and self.db_manager.conn:
            self.db_manager.delete_history_item(did)
        self.update_overall_progress()

    def schedule_remove_download(self, did, delay):
        try:
            old = self.pending_remove_timers.get(did)
            if old:
                old.stop()
                old.deleteLater()
            t = QTimer(self)
            t.setSingleShot(True)
            t.timeout.connect(lambda d=did: self._on_remove_timeout(d))
            t.start(delay)
            self.pending_remove_timers[did] = t
        except Exception:
            pass

    def _on_remove_timeout(self, did):
        self.pending_remove_timers.pop(did, None)
        try:
            self.remove_download(did)
        except Exception:
            pass

    def cancel_scheduled_remove(self, did):
        t = self.pending_remove_timers.pop(did, None)
        if t:
            try:
                t.stop()
                t.deleteLater()
            except Exception:
                pass

    def cancel_download(self, did):
        if did in self.downloads:
            self.cancel_scheduled_remove(did)
            self.finalized_downloads.add(did)
            self.downloads[did].cancel()
            self.update_download_status(did, "❌ Annulé")
            if self.db_manager and self.db_manager.conn:
                self.db_manager.enqueue_update(did, status="Annulé")
                self.db_manager.flush_updates()
            self.active_downloads_count = max(0, self.active_downloads_count - 1)
            QTimer.singleShot(2000, lambda: self.remove_download(did))

    def pause_all_downloads(self):
        for w in self.downloads.values():
            w.pause()

    def resume_all_downloads(self):
        for w in self.downloads.values():
            w.resume()

    def cancel_all_downloads(self):
        for did in list(set(self.download_items.keys()) | set(self.downloads.keys())):
            self.cancel_scheduled_remove(did)
            self.remove_download(did, delete_history=True)
        self.pending_ui_updates.clear()
        self.active_downloads_count = 0

    def start_batch_download(self):
        text = self.urls_list.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "خطأ", "القائمة فارغة")
            return
        urls = [u.strip() for u in text.split('\n')
                if u.strip().startswith(('http://', 'https://'))]
        if not urls:
            QMessageBox.warning(self, "خطأ", "لا توجد روابط صالحة")
            return
        save_path = self.path_display.text()
        quality = self.batch_quality.currentText()
        is_audio = self.batch_audio.isChecked()
        use_cookies = self.batch_cookies.isChecked()
        is_seq = self.batch_sequential.isChecked()
        self.batch_table.setRowCount(len(urls))
        for i, url in enumerate(urls):
            did = str(self.next_id)
            self.next_id += 1
            self.batch_table.setItem(i, 0, QTableWidgetItem(url[:60]))
            self.batch_table.setItem(i, 1, QTableWidgetItem(
                "في الانتظار" if is_seq else "En attente"))
            self.batch_table.setItem(i, 2, QTableWidgetItem("0%"))
            self.batch_table.setItem(i, 3, QTableWidgetItem("0 KB/s"))
            self.batch_table.setItem(i, 4, QTableWidgetItem(did))
            if is_seq:
                self.sequential_mode = True
                if hasattr(self, 'sequential_checkbox'):
                    self.sequential_checkbox.setChecked(True)
                self.add_to_sequential_queue(did, url, save_path, quality,
                                              is_audio, use_cookies)
            else:
                self.add_download(did, url, save_path, quality, is_audio, use_cookies)
        if is_seq:
            self.tabs.setCurrentIndex(3)
            if not self.sequential_running:
                QTimer.singleShot(500, self.start_sequential_download)

    def get_active_download_widgets(self):
        return [self.active_downloads_layout.itemAt(i).widget()
                for i in range(self.active_downloads_layout.count())
                if isinstance(self.active_downloads_layout.itemAt(i).widget(),
                              DownloadItemWidget)]

    def clear_sequential_queue(self):
        if not self.sequential_queue:
            return
        if QMessageBox.question(self, 'تأكيد', 'مسح قائمة الانتظار؟',
                                 QMessageBox.Yes | QMessageBox.No,
                                 QMessageBox.No) != QMessageBox.Yes:
            return
        if self.current_sequential_download and self.current_sequential_download in self.downloads:
            self.cancel_download(self.current_sequential_download)
        self.sequential_queue.clear()
        self.current_sequential_download = None
        self.sequential_running = False
        for did in list(self.download_items.keys()):
            w = self.download_items[did]
            if hasattr(w, 'status_badge') and "في الانتظار" in w.status_badge.text():
                self.remove_download(did)

    def reverse_sequential_queue(self):
        if len(self.sequential_queue) <= 1:
            return
        waiting = [i for i in self.sequential_queue
                   if i.get('status') in ('في الانتظار', 'En attente')]
        if len(waiting) <= 1:
            return
        waiting_ids = {i['download_id'] for i in waiting}
        if self.current_sequential_download in waiting_ids:
            return
        waiting.reverse()
        positions = [i for i, item in enumerate(self.sequential_queue)
                     if item.get('status') in ('في الانتظار', 'En attente')]
        for pos, item in zip(positions, waiting):
            self.sequential_queue[pos] = item

    def reorder_sequential_queue(self, did, offset):
        if not self.sequential_queue:
            return
        idx = None
        for i, item in enumerate(self.sequential_queue):
            if item.get('download_id') == did:
                idx = i
                break
        if idx is None or did == self.current_sequential_download:
            return
        if self.sequential_queue[idx].get('status') not in ('في الانتظار', 'En attente'):
            return
        target = idx + offset
        if 0 <= target < len(self.sequential_queue):
            self.sequential_queue[idx], self.sequential_queue[target] = \
                self.sequential_queue[target], self.sequential_queue[idx]

    def check_network(self):
        if getattr(self, 'checker', None) is not None and self.checker.isRunning():
            return
        self.checker = NetworkChecker(self)
        self.checker.connection_status.connect(self.on_network_status, Qt.QueuedConnection)
        self.checker.finished.connect(lambda: setattr(self, 'checker', None))
        self.checker.start()

    def on_network_status(self, connected):
        self._network_connected = connected
        if not connected:
            self.statusBar.showMessage("⚠️ لا يوجد اتصال بالإنترنت")

    def start_local_server(self):
        if self.server_running:
            return
        app = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                return

            def _json(self, obj, code=200):
                self.send_response(code)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(obj).encode())

            def do_GET(self):
                p = urllib.parse.urlparse(self.path)
                q = urllib.parse.parse_qs(p.query)
                if p.path == '/download' and 'url' in q:
                    app.browser_download_signal.emit(q['url'][0])
                    self._json({"status": "success"})
                    return
                self.send_response(404)
                self.end_headers()

            def do_POST(self):
                length = int(self.headers.get('content-length', 0))
                body = self.rfile.read(length) if length > 0 else b''
                try:
                    data = json.loads(body.decode('utf-8')) if body else {}
                except Exception:
                    data = {}
                url = data.get('url')
                if url:
                    app.browser_download_signal.emit(url)
                    self._json({"status": "success"})
                    return
                self._json({"status": "error"}, 400)

        def run_server():
            try:
                server = HTTPServer((self.server_host, self.server_port), Handler)
                self._http_server = server
                self.server_running = True
                server.serve_forever()
            except Exception as e:
                print(f"Serveur: {e}")
                self.server_running = False

        t = threading.Thread(target=run_server, daemon=True)
        t.start()
        self.server_running = True

    def stop_local_server(self):
        if self._http_server:
            try:
                self._http_server.shutdown()
                self._http_server.server_close()
            except Exception:
                pass
        self.server_running = False

    def handle_external_download(self, url):
        if url:
            self.url_input.setText(url)
            self.tabs.setCurrentIndex(0)
            self.activateWindow()
            self.raise_()
            if QMessageBox.question(self, 'رابط خارجي',
                                     f'تحميل؟\n\n{url[:100]}...',
                                     QMessageBox.Yes | QMessageBox.No,
                                     QMessageBox.Yes) == QMessageBox.Yes:
                self.start_single_download()

    def start_download_from_browser(self, url):
        if not url:
            return
        self.url_input.setText(url)
        self.tabs.setCurrentIndex(0)
        self.activateWindow()
        self.raise_()
        self.start_single_download()

    def install_extension_help(self):
        ext_path = Path.home() / "TK_Downloader_Extension"
        ext_path.mkdir(exist_ok=True)
        manifest = {
            "manifest_version": 3,
            "name": "TK Downloader Connector",
            "version": "1.2",
            "description": "Intégration TK Downloader",
            "permissions": ["contextMenus", "notifications", "tabs"],
            "host_permissions": ["http://127.0.0.1:9191/*"],
            "background": {"service_worker": "background.js"},
            "action": {"default_title": "TK Downloader"},
            "icons": {"128": "icon.png"},
        }
        (ext_path / "manifest.json").write_text(
            json.dumps(manifest, indent=4), encoding='utf-8')
        bg = """
const SERVER_URL = 'http://127.0.0.1:9191';
chrome.runtime.onInstalled.addListener(() => {
    chrome.contextMenus.create({
        id: "send_to_tk",
        title: "Télécharger avec TK",
        contexts: ["link", "video", "audio", "page"]
    });
});
chrome.contextMenus.onClicked.addListener((info, tab) => {
    if (info.menuItemId === "send_to_tk") {
        const url = info.linkUrl || info.srcUrl || info.pageUrl || tab.url;
        fetch(`${SERVER_URL}/download?url=${encodeURIComponent(url)}`)
            .then(r => r.json()).then(d => {
                chrome.notifications.create({
                    type: 'basic', iconUrl: 'icon.png',
                    title: 'TK Downloader', message: 'Lien envoye!'
                });
            });
    }
});
"""
        (ext_path / "background.js").write_text(bg, encoding='utf-8')
        icon = ext_path / "icon.png"
        if not icon.exists():
            icon.write_bytes(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
                             b'\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06'
                             b'\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\n'
                             b'IDATx\x9cc\x00\x00\x00\x02\x00\x01\xe2!\xbc3'
                             b'\x00\x00\x00\x00IEND\xaeB`\x82')
        ExtensionDialog(ext_path, self).exec_()

    def load_settings(self):
        if not self.db_manager:
            return
        save_path = self.db_manager.get_preference('save_path')
        if save_path and os.path.exists(save_path):
            self.path_display.setText(save_path)
        try:
            enabled = self.db_manager.get_preference('scheduler_enabled', '0')
            self.scheduler_enabled = str(enabled) in ('1', 'True', 'true')
            self.scheduler_time = self.db_manager.get_preference('scheduler_time', '02:00')
        except Exception:
            pass

    def closeEvent(self, event):
        active = sum(1 for w in self.downloads.values() if w.isRunning())
        active += sum(1 for w in self.torrent_downloads.values() if w.isRunning())
        if active > 0:
            if QMessageBox.question(self, 'خروج',
                                     f'{active} تحميلات جارية. هل تريد الخروج؟',
                                     QMessageBox.Yes | QMessageBox.No,
                                     QMessageBox.No) != QMessageBox.Yes:
                event.ignore()
                return
        for did, w in list(self.downloads.items()):
            if w.isRunning():
                if self.db_manager and self.db_manager.conn:
                    self.db_manager.enqueue_update(did, status="Interrompu")
                w.cancel()
                w.wait(1000)
        if self.db_manager and self.db_manager.conn:
            self.db_manager.flush_updates()
        self.stop_local_server()
        if hasattr(self, 'check_timer'):
            self.check_timer.stop()
        if hasattr(self, 'scheduler_timer'):
            self.scheduler_timer.stop()
        for w in self.torrent_downloads.values():
            try:
                w.cancel()
                w.wait(2000)
            except Exception:
                pass
        if self.db_manager:
            self.db_manager.close()
        event.accept()
'''

# ============================================================================
# GÉNÉRATION
# ============================================================================

def generate_source_files(force=False):
    banner("✂️  Génération des fichiers source")
    if SRC_DIR.exists() and not force:
        LOG.info(f"✅ {SRC_DIR}/ existe déjà")
        return True
    if SRC_DIR.exists():
        LOG.info(f"🧹 Suppression de {SRC_DIR}/")
        shutil.rmtree(SRC_DIR)
    SRC_DIR.mkdir(parents=True, exist_ok=True)
    for rel_path, content in SOURCE_FILES.items():
        file_path = SRC_DIR / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding='utf-8')
        LOG.info(f"  ✅ {rel_path}")
    LOG.info(f"\n✅ {len(SOURCE_FILES)} fichiers générés dans {SRC_DIR}/")
    return True


# ============================================================================
# VÉRIFICATIONS SYSTÈME
# ============================================================================

def check_python():
    banner("🐍 Python système")
    v = sys.version_info
    LOG.info(f"Python: {v.major}.{v.minor}.{v.micro}")
    if v < (3, 8):
        LOG.error("❌ Python 3.8+ requis")
        return False
    LOG.info("✅ Compatible")
    return True


def check_ffmpeg():
    banner("🎬 FFmpeg")
    try:
        r = run(["ffmpeg", "-version"], capture=True, check=False)
        if r.returncode == 0:
            LOG.info(f"✅ {r.stdout.split(chr(10))[0]}")
            return True
    except Exception:
        pass
    LOG.warning("⚠️  FFmpeg non trouvé (MP3 désactivé)")
    return False


def check_aria2c():
    banner("🌀 aria2c")
    if Path("aria2c.exe").exists():
        LOG.info("✅ aria2c.exe présent")
        return True
    try:
        cmd = "where" if platform.system() == "Windows" else "which"
        r = run([cmd, "aria2c"], capture=True, check=False)
        if r.returncode == 0:
            LOG.info("✅ aria2c dans PATH")
            return True
    except Exception:
        pass
    LOG.warning("⚠️  aria2c non trouvé (torrents désactivés)")
    return False


def download_aria2c():
    if platform.system() != "Windows":
        return False
    if Path("aria2c.exe").exists():
        return True
    banner("⬇️  Téléchargement aria2c.exe")
    try:
        temp_zip = Path("aria2_temp.zip")

        def progress(bn, bs, ts):
            if ts > 0:
                pct = min(100, bn * bs * 100 / ts)
                sys.stdout.write(f"\r   {pct:.1f}%")
                sys.stdout.flush()

        urllib.request.urlretrieve(ARIA2_URL_WIN, temp_zip, reporthook=progress)
        print()
        with zipfile.ZipFile(temp_zip, 'r') as zf:
            for m in zf.namelist():
                if m.endswith("aria2c.exe"):
                    with zf.open(m) as s, open("aria2c.exe", 'wb') as d:
                        shutil.copyfileobj(s, d)
                    break
        temp_zip.unlink()
        LOG.info("✅ aria2c.exe téléchargé")
        return True
    except Exception as e:
        LOG.error(f"❌ {e}")
        return False


def install_in_venv(vm, packages):
    banner("📥 Installation des dépendances")
    missing = []
    for pkg, imp in packages.items():
        if vm.check_package(imp):
            LOG.info(f"  ✅ {pkg}")
        else:
            LOG.warning(f"  ❌ {pkg}")
            missing.append(pkg)
    if not missing:
        return True
    failed = []
    for pkg in missing:
        if not vm.install_package(pkg):
            failed.append(pkg)
    if failed:
        LOG.error(f"❌ Échecs: {', '.join(failed)}")
        return False
    return True


# ============================================================================
# LANCEMENT AVEC VÉRIFICATION
# ============================================================================

def verify_and_run(vm, extra=None):
    banner("🔍 Vérification avant lancement")
    if not verify_all_sources():
        LOG.error("❌ Erreurs de syntaxe! Corrigez-les avant de lancer.")
        return False
    if not verify_imports(vm):
        LOG.error("❌ Erreurs d'import! Voir startup_error.log")
        return False
    banner("🚀 Lancement du programme")
    main_path = SRC_DIR / "main.py"
    try:
        if STARTUP_LOG.exists():
            STARTUP_LOG.unlink()
    except Exception:
        pass
    env = vm.get_env()
    args = [str(vm.python_exe), str(main_path)] + (extra or [])
    LOG.info(f"▶️  {' '.join(args)}")
    try:
        result = subprocess.run(args, env=env)
        if STARTUP_LOG.exists():
            content = STARTUP_LOG.read_text(encoding='utf-8')
            if "UNHANDLED" in content or "ERREUR" in content:
                LOG.warning("⚠️  Des erreurs ont été enregistrées dans startup_error.log")
        if result.returncode != 0:
            LOG.error(f"❌ Programme terminé avec code: {result.returncode}")
            LOG.info("💡 Voir startup_error.log")
            return False
        return True
    except KeyboardInterrupt:
        return True
    except Exception as e:
        LOG.error(f"❌ Échec: {e}")
        LOG.error(traceback.format_exc())
        return False


# ============================================================================
# BUILD
# ============================================================================

def build_executable(vm):
    banner("🔨 Build PyInstaller")
    if not (SRC_DIR / "main.py").exists():
        LOG.error("❌ src/main.py introuvable")
        return False
    if not vm.check_package("PyInstaller"):
        LOG.info("📦 Installation PyInstaller...")
        if not vm.install_package("pyinstaller>=6.0.0"):
            return False
    for d in ["build", "dist"]:
        if Path(d).exists():
            shutil.rmtree(d, ignore_errors=True)
    cmd = [str(vm.python_exe), "-m", "PyInstaller",
           "--noconfirm", "--clean", "--windowed",
           "--name", APP_NAME,
           "--add-data", f"src{os.pathsep}src"]
    if Path(ICON_FILE).exists():
        cmd.extend(["--icon", ICON_FILE])
    for f in ["icon.ico", "icon.png", "icon.svg"]:
        if Path(f).exists():
            cmd.extend(["--add-data", f"{f}{os.pathsep}."])
    for imp in ["yt_dlp", "yt_dlp.extractor", "aria2p",
                "PyQt5.QtCore", "PyQt5.QtGui", "PyQt5.QtWidgets"]:
        cmd.extend(["--hidden-import", imp])
    cmd.append(str(SRC_DIR / "main.py"))
    LOG.info(f"▶️  Build...")
    env = vm.get_env()
    r = subprocess.run(cmd, check=False, env=env)
    if r.returncode != 0:
        LOG.error("❌ Build échoué")
        return False
    dist = Path("dist") / APP_NAME
    for f in ["aria2c.exe", "icon.ico", "icon.png", "icon.svg"]:
        if Path(f).exists():
            try:
                shutil.copy2(f, dist)
            except Exception:
                pass
    exe = dist / f"{APP_NAME}.exe"
    if exe.exists():
        LOG.info(f"✅ {exe} ({exe.stat().st_size / (1024 * 1024):.1f} MB)")
        return True
    return False


# ============================================================================
# NETTOYAGE
# ============================================================================

def clean_all(include_venv=False):
    banner("🧹 Nettoyage")
    dirs = ["build", "dist", "build_logs"]
    if include_venv:
        dirs.append(str(VENV_DIR))
    for d in dirs:
        if Path(d).exists():
            LOG.info(f"🗑️  {d}/")
            shutil.rmtree(d, ignore_errors=True)
    for f in ["*.spec", "aria2_temp.zip", "crash_log.txt"]:
        for p in Path(".").glob(f):
            try:
                p.unlink()
            except Exception:
                pass
    for p in Path(".").rglob("__pycache__"):
        shutil.rmtree(p, ignore_errors=True)
    LOG.info("✅ Terminé")


def reset_all():
    banner("♻️  Reset complet")
    for d in [VENV_DIR, SRC_DIR, Path("build"), Path("dist")]:
        if d.exists():
            LOG.info(f"🗑️  {d}/")
            shutil.rmtree(d, ignore_errors=True)
    clean_all(include_venv=False)
    LOG.info("✅ Reset terminé")


# ============================================================================
# ACTIONS
# ============================================================================

def action_venv(force=False):
    if not check_python():
        return False
    return VenvManager().create(force=force)


def action_generate(force=False):
    return generate_source_files(force=force)


def action_check():
    banner(f"🔍 VÉRIFICATION - {APP_NAME}")
    ok_py = check_python()
    vm = VenvManager()
    if vm.exists():
        vm.info()
    else:
        LOG.warning("❌ Aucun venv — lancez: python setup.py venv")
    check_ffmpeg()
    check_aria2c()
    return ok_py and vm.exists()


def action_install():
    banner(f"📥 INSTALLATION - {APP_NAME}")
    if not check_python():
        return False
    vm = VenvManager()
    if not vm.exists():
        LOG.info("🌐 Création venv...")
        if not vm.create():
            return False
    if not install_in_venv(vm, REQUIRED_PACKAGES):
        return False
    if platform.system() == "Windows" and not check_aria2c():
        download_aria2c()
    check_ffmpeg()
    return True


def action_run(extra=None):
    banner(f"🚀 LANCEMENT - {APP_NAME}")
    vm = VenvManager()
    if not vm.exists():
        LOG.info("🌐 Création venv...")
        if not vm.create():
            return False
    if not generate_source_files():
        return False
    missing = [p for p, i in REQUIRED_PACKAGES.items() if not vm.check_package(i)]
    if missing:
        LOG.info(f"📦 Installation: {missing}")
        if not install_in_venv(vm, REQUIRED_PACKAGES):
            return False
    return verify_and_run(vm, extra)


def action_all(extra=None):
    banner(f"🎯 TOUT-EN-UN - {APP_NAME}")
    vm = VenvManager()
    if not vm.exists():
        if not vm.create():
            return False
    else:
        LOG.info("✅ Venv existant")
    if not generate_source_files():
        return False
    if not install_in_venv(vm, REQUIRED_PACKAGES):
        return False
    if platform.system() == "Windows" and not check_aria2c():
        download_aria2c()
    check_ffmpeg()
    return verify_and_run(vm, extra)


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} - Setup complet auto-contenu v{APP_VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python setup.py all         # TOUT faire
  python setup.py venv        # Créer le venv
  python setup.py generate    # Générer les sources
  python setup.py check       # Vérifier
  python setup.py install     # Installer
  python setup.py run         # Lancer (avec vérification)
  python setup.py build       # Créer un .exe
  python setup.py clean       # Nettoyer
  python setup.py reset       # TOUT supprimer
        """
    )
    parser.add_argument('action',
                        choices=['venv', 'generate', 'check', 'install',
                                 'run', 'build', 'all', 'clean', 'reset'],
                        nargs='?', default='all')
    parser.add_argument('-f', '--force', action='store_true',
                        help="Forcer la régénération")
    args, extra = parser.parse_known_args()

    try:
        if args.action == 'venv':
            ok = action_venv(force=args.force)
        elif args.action == 'generate':
            ok = action_generate(force=args.force)
        elif args.action == 'check':
            ok = action_check()
        elif args.action == 'install':
            ok = action_install()
        elif args.action == 'run':
            ok = action_run(extra=extra)
        elif args.action == 'build':
            vm = VenvManager()
            if not vm.exists():
                LOG.error("❌ Lancez d'abord: python setup.py venv")
                sys.exit(1)
            if not generate_source_files():
                sys.exit(1)
            ok = build_executable(vm)
        elif args.action == 'all':
            ok = action_all(extra=extra)
        elif args.action == 'clean':
            clean_all(include_venv=False); ok = True
        elif args.action == 'reset':
            reset_all(); ok = True
        else:
            parser.print_help(); ok = False
        sys.exit(0 if ok else 1)
    except KeyboardInterrupt:
        LOG.info("\n👋 Interrompu")
        sys.exit(130)
    except Exception as e:
        LOG.critical(f"❌ {e}")
        import traceback
        LOG.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()