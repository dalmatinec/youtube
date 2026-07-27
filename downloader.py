import os
import re
import time

import yt_dlp

import config

os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)

PLATFORM_PATTERNS = {
    "youtube": r"(youtube\.com|youtu\.be)",
    "tiktok": r"tiktok\.com",
    "instagram": r"instagram\.com",
}


def detect_platform(url: str) -> str:
    for name, pattern in PLATFORM_PATTERNS.items():
        if re.search(pattern, url):
            return name
    return "unknown"


def _outtmpl() -> str:
    # уникальное имя на каждый вызов, чтобы не путать файлы разных юзеров
    return os.path.join(config.DOWNLOAD_DIR, f"%(id)s_{int(time.time()*1000)}.%(ext)s")


def _base_opts() -> dict:
    return {
        "outtmpl": _outtmpl(),
        "quiet": True,
        "no_warnings": True,
        "noplaylist": False,  # альбомы/карусели Instagram и слайд-шоу TikTok — это "плейлисты" из фото
        # если для приватных Instagram-постов нужна авторизация — положи файл cookies.txt
        # (экспортированный из браузера) рядом со скриптом и раскомментируй строку ниже:
        # "cookiefile": "cookies.txt",
    }


def probe(url: str) -> dict:
    """Метаданные без скачивания — нужно для списка качеств YouTube."""
    opts = _base_opts()
    opts["skip_download"] = True
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def list_video_qualities(info: dict) -> list[dict]:
    """Уникальные высоты видео с их format_id, отсортированные по убыванию качества."""
    formats = info.get("formats") or []
    seen = set()
    result = []
    for f in formats:
        height = f.get("height")
        if not height or f.get("vcodec") in (None, "none"):
            continue
        if height in seen:
            continue
        seen.add(height)
        result.append(
            {
                "format_id": f["format_id"],
                "height": height,
                "filesize": f.get("filesize") or f.get("filesize_approx"),
            }
        )
    return sorted(result, key=lambda x: x["height"], reverse=True)


def download(url: str, format_selector: str | None = None, audio_only: bool = False) -> list[dict]:
    """
    Скачивает видео / фото-альбом / аудио.
    Возвращает список: [{"path": "...", "type": "video"|"photo"|"audio"}, ...]
    """
    opts = _base_opts()
    opts["skip_download"] = False

    if audio_only:
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
        ]
    elif format_selector:
        opts["format"] = f"{format_selector}+bestaudio/best"
        opts["merge_output_format"] = "mp4"
    else:
        opts["format"] = "best"

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)

        entries = info.get("entries") if info.get("_type") == "playlist" else [info]
        files = []
        for entry in entries:
            if not entry:
                continue
            path = ydl.prepare_filename(entry)
            if audio_only:
                path = os.path.splitext(path)[0] + ".mp3"
            if not os.path.exists(path):
                continue
            ext = os.path.splitext(path)[1].lower()
            if ext in (".jpg", ".jpeg", ".png", ".webp"):
                ftype = "photo"
            elif ext in (".mp3", ".m4a", ".opus"):
                ftype = "audio"
            else:
                ftype = "video"
            files.append({"path": path, "type": ftype})
        return files
