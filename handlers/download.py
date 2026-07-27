import logging
import os
import re
import time

import requests
import yt_dlp

import config

log = logging.getLogger("downloader")

os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)

PLATFORM_PATTERNS = {
    "youtube": r"(youtube\.com|youtu\.be)",
    "tiktok": r"tiktok\.com",
    "instagram": r"instagram\.com",
}

TIKWM_API = "https://www.tikwm.com/api/"


def detect_platform(url: str) -> str:
    for name, pattern in PLATFORM_PATTERNS.items():
        if re.search(pattern, url):
            return name
    return "unknown"


def _outtmpl() -> str:
    return os.path.join(config.DOWNLOAD_DIR, f"%(id)s_{int(time.time()*1000)}.%(ext)s")


def _base_opts() -> dict:
    return {
        "outtmpl": _outtmpl(),
        "quiet": True,
        "no_warnings": True,
        "noplaylist": False,
        # для приватных Instagram-постов положи cookies.txt рядом со скриптом и раскомментируй:
        # "cookiefile": "cookies.txt",
    }


def probe(url: str) -> dict:
    """Метаданные без скачивания — нужно для списка качеств YouTube."""
    opts = _base_opts()
    opts["skip_download"] = True
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def list_video_qualities(info: dict) -> list[dict]:
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


def _ytdlp_download(url: str, format_selector: str | None, audio_only: bool) -> list[dict]:
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


def _save_remote_file(url: str, ext: str) -> str:
    path = os.path.join(config.DOWNLOAD_DIR, f"tikwm_{int(time.time()*1000)}.{ext}")
    r = requests.get(url, timeout=60, stream=True, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    with open(path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    return path


def _tikwm_download(url: str) -> list[dict]:
    """Резервный способ для TikTok через tikwm.com — без браузера, просто HTTP."""
    resp = requests.post(TIKWM_API, data={"url": url}, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"tikwm: {data.get('msg', 'неизвестная ошибка')}")

    d = data["data"]
    files: list[dict] = []

    if d.get("images"):
        # фото-слайдшоу
        for img_url in d["images"]:
            files.append({"path": _save_remote_file(img_url, "jpg"), "type": "photo"})
        if d.get("music"):
            files.append({"path": _save_remote_file(d["music"], "mp3"), "type": "audio"})
    else:
        video_url = d.get("hdplay") or d.get("play")
        if not video_url:
            raise RuntimeError("tikwm: не нашёл ссылку на видео в ответе")
        files.append({"path": _save_remote_file(video_url, "mp4"), "type": "video"})

    return files


def download(url: str, format_selector: str | None = None, audio_only: bool = False) -> list[dict]:
    """
    Скачивает видео / фото-альбом / аудио.
    Возвращает список: [{"path": "...", "type": "video"|"photo"|"audio"}, ...]
    Для TikTok: если yt-dlp падает (частая проблема из-за смены разметки TikTok),
    автоматически пробует резервный способ через tikwm.com.
    """
    platform = detect_platform(url)

    if platform == "tiktok":
        try:
            return _ytdlp_download(url, format_selector, audio_only)
        except Exception as e:
            log.warning("yt-dlp не смог скачать TikTok (%s), пробую tikwm...", e)
            return _tikwm_download(url)

    return _ytdlp_download(url, format_selector, audio_only)
