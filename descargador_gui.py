"""Descargador MP3/MP4 con Tkinter. Ejecutar con iniciar_descargador.bat."""

from __future__ import annotations

import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit


APP_DIR = Path(__file__).resolve().parent
APP_VERSION = "1.0.0"
AUDIO_QUALITY = ("192 kbps", "128 kbps", "256 kbps", "320 kbps")
VIDEO_QUALITY = ("1080p", "720p", "480p", "360p", "Mejor disponible")


def parse_urls(text: str, playlist: bool) -> list[str]:
    urls = list(dict.fromkeys(line.strip() for line in text.splitlines() if line.strip()))
    if not urls:
        raise ValueError("Pega al menos un enlace, uno por línea.")
    for url in urls:
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise ValueError(f"El enlace debe comenzar por https:// o http://:\n{url}")
        host = parts.hostname.lower().removeprefix("www.").removeprefix("m.")
        if not playlist and host in ("youtube.com", "music.youtube.com"):
            if parts.path.rstrip("/") == "/playlist":
                raise ValueError("Este enlace es una playlist. Selecciona «Playlist completa / rango».")
    return urls


def validate_items(items: str) -> str:
    items = items.replace(" ", "")
    if items and not re.fullmatch(r"[1-9]\d*(?:-[1-9]\d*)?(?:,[1-9]\d*(?:-[1-9]\d*)?)*", items):
        raise ValueError("El rango debe tener este formato: 1-10 o 1,3,5-8.")
    for item in items.split(",") if items else []:
        if "-" in item:
            start, end = map(int, item.split("-"))
            if start > end:
                raise ValueError("El inicio del rango no puede ser mayor que el final.")
    return items


def find_ffmpeg() -> str | None:
    local = APP_DIR / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    return str(local) if local.is_file() else shutil.which("ffmpeg")


def build_options(config: dict) -> dict:
    """Opciones compartidas por el proceso de descarga y las pruebas."""
    opts = {
        "outtmpl": str(Path(config["destination"]) / "%(title).150B [%(id)s].%(ext)s"),
        "ffmpeg_location": config["ffmpeg"],
        "noplaylist": not config["playlist"],
        "ignoreerrors": True,
        "continuedl": True,
        "overwrites": False,
        "final_ext": config["format"].lower(),
        "windowsfilenames": True,
        "quiet": True,
        "noprogress": True,
        "nocolor": True,
        "socket_timeout": 20,
        "retries": 3,
        "fragment_retries": 3,
        "js_runtimes": {name: {} for name in ("deno", "node") if shutil.which(name)},
    }
    if config["playlist"]:
        opts["outtmpl"] = str(
            Path(config["destination"]) / "%(playlist_title|Sin playlist).100B"
            / "%(playlist_index|0)03d - %(title).140B [%(id)s].%(ext)s"
        )
        if config.get("items"):
            opts["playlist_items"] = validate_items(config["items"])
    if config.get("cookies"):
        opts["cookiefile"] = config["cookies"]
    if config["format"] == "MP3":
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio", "preferredcodec": "mp3",
            "preferredquality": config["quality"].split()[0],
        }]
    else:
        height = config["quality"].removesuffix("p")
        cap = "" if height == "Mejor disponible" else f"[height<=?{int(height)}]"
        opts["format"] = f"bestvideo[ext=mp4]{cap}+bestaudio[ext=m4a]/best[ext=mp4]{cap}"
        opts["merge_output_format"] = "mp4"
        opts["postprocessors"] = [{"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"}]
    return opts


def run_worker(config: dict) -> int:
    """Solo este proceso importa yt-dlp. La GUI recibe eventos JSON por stdout."""
    def emit(event: str, **values):
        print(json.dumps({"event": event, **values}, ensure_ascii=True), flush=True)

    try:
        import yt_dlp
    except ImportError:
        emit("log", level="error", text="Falta yt-dlp. Ejecuta iniciar_descargador.bat para instalarlo.")
        return 1

    completed = 0
    errors = 0
    last_progress = 0.0

    class Logger:
        def __init__(self):
            self.warnings = set()

        def debug(self, message):
            if not message.startswith("[debug]"):
                emit("log", level="info", text=message)

        def warning(self, message):
            if message not in self.warnings:
                self.warnings.add(message)
                emit("log", level="warning", text=message)

        def error(self, message):
            nonlocal errors
            # yt-dlp también envía avisos de obsolescencia a logger.error.
            if message.startswith("Deprecated Feature:"):
                self.warning(message)
                return
            errors += 1
            emit("log", level="error", text=message)

    def progress(data):
        nonlocal last_progress
        now = time.monotonic()
        if data["status"] == "downloading" and now - last_progress < 0.15:
            return
        last_progress = now
        info = data.get("info_dict") or {}
        emit("progress", status=data["status"], title=info.get("title", "Descargando…"),
             downloaded=data.get("downloaded_bytes", 0),
             total=data.get("total_bytes") or data.get("total_bytes_estimate"),
             speed=data.get("speed"), eta=data.get("eta"),
             index=info.get("playlist_index"), count=info.get("n_entries") or info.get("playlist_count"))

    def postprocess(data):
        if data["status"] == "started":
            emit("processing", text="Convirtiendo / uniendo audio y video…")

    def ready(filename):
        nonlocal completed
        completed += 1
        emit("ready", filename=filename, completed=completed)

    try:
        options = build_options(config)
        options.update(logger=Logger(), progress_hooks=[progress],
                       postprocessor_hooks=[postprocess], post_hooks=[ready])
        with yt_dlp.YoutubeDL(options) as downloader:
            for index, url in enumerate(config["urls"], 1):
                emit("link", index=index, count=len(config["urls"]))
                downloader.download([url])
    except Exception as exc:
        errors += 1
        emit("log", level="error", text=str(exc))
    emit("summary", completed=completed, errors=errors)
    return 1 if errors else 0


def stop_process(process: subprocess.Popen):
    """Detiene únicamente el trabajador y sus conversores hijos."""
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       creationflags=subprocess.CREATE_NO_WINDOW, check=False)
    else:
        import signal
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass


def human_bytes(value) -> str:
    value = float(value or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}"
        value /= 1024


def launch_gui():
    from interfaz import DownloaderApp

    return DownloaderApp()

if __name__ == "__main__":
    if "--player-worker" in sys.argv:
        from reproductor_video import run_player

        sys.exit(run_player(json.loads(sys.stdin.readline())))
    elif "--songs-worker" in sys.argv:
        from canciones import run_import_worker

        sys.exit(run_import_worker(json.loads(sys.stdin.readline())))
    elif "--worker" in sys.argv:
        try:
            worker_config = json.loads(sys.stdin.readline())
            sys.exit(run_worker(worker_config))
        except (ValueError, KeyError) as exc:
            print(json.dumps(dict(event="log", level="error", text=f"Configuración inválida: {exc}")), flush=True)
            sys.exit(1)
    else:
        launch_gui().mainloop()
