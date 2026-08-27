"""
Core download/convert engine.

Wraps yt-dlp to fetch video info and perform MP3/MP4 extraction with
user-selectable bitrate (audio) or resolution/quality (video). Designed to
run on a background thread; progress is pushed onto a thread-safe Queue so
a GUI can poll it with .after() without blocking the event loop.
"""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import yt_dlp

from ffmpeg_utils import find_ffmpeg

# ---------------------------------------------------------------------------
# Options

MP3_BITRATES = ["320", "256", "192", "128", "96", "64"]  # kbps

VIDEO_QUALITIES = {
    "Best available": None,
    "2160p (4K)": 2160,
    "1440p (2K)": 1440,
    "1080p (Full HD)": 1080,
    "720p (HD)": 720,
    "480p (SD)": 480,
    "360p": 360,
}

VIDEO_CODECS = {
    "Auto (recommended)": None,
    "H.264 (most compatible)": "avc1",
    "VP9": "vp9",
    "AV1": "av01",
}


class Mode(str, Enum):
    MP3 = "mp3"
    MP4 = "mp4"


class EventType(str, Enum):
    INFO = "info"
    PROGRESS = "progress"
    LOG = "log"
    DONE = "done"
    ERROR = "error"


@dataclass
class ProgressEvent:
    type: EventType
    payload: dict = field(default_factory=dict)


@dataclass
class DownloadSettings:
    url: str
    mode: Mode
    output_dir: str
    # audio
    mp3_bitrate: str = "192"
    # video
    max_height: Optional[int] = None
    video_codec: Optional[str] = None
    # misc
    filename_template: str = "%(title)s.%(ext)s"
    embed_thumbnail: bool = True
    ffmpeg_location: Optional[str] = None


def fetch_info(url: str, ffmpeg_location: Optional[str] = None) -> dict:
    """Fetch metadata (title, duration, thumbnail, available heights) without downloading."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": False,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    # Normalize: could be a single video or a playlist
    if "entries" in info:
        entries = [e for e in info["entries"] if e]
        heights = sorted(
            {f.get("height") for e in entries for f in e.get("formats", []) if f.get("height")},
            reverse=True,
        )
        return {
            "is_playlist": True,
            "title": info.get("title", "Playlist"),
            "count": len(entries),
            "entries": [{"title": e.get("title"), "duration": e.get("duration")} for e in entries],
            "available_heights": heights,
        }
    else:
        heights = sorted(
            {f.get("height") for f in info.get("formats", []) if f.get("height")}, reverse=True
        )
        return {
            "is_playlist": False,
            "title": info.get("title", "Unknown title"),
            "uploader": info.get("uploader"),
            "duration": info.get("duration"),
            "thumbnail": info.get("thumbnail"),
            "available_heights": heights,
        }


def _build_format_selector(max_height: Optional[int], codec: Optional[str]) -> str:
    height_filter = f"[height<={max_height}]" if max_height else ""
    codec_filter = f"[vcodec^={codec}]" if codec else ""
    primary = f"bestvideo{height_filter}{codec_filter}+bestaudio/best{height_filter}{codec_filter}"
    # Fallback without codec constraint in case the exact codec isn't available
    fallback = f"bestvideo{height_filter}+bestaudio/best{height_filter}"
    return f"{primary}/{fallback}/best"


def _build_ydl_opts(settings: DownloadSettings, event_q: "queue.Queue[ProgressEvent]") -> dict:
    import os

    outtmpl = os.path.join(settings.output_dir, settings.filename_template)

    def progress_hook(d):
        if d.get("status") == "downloading":
            event_q.put(ProgressEvent(EventType.PROGRESS, {
                "stage": "downloading",
                "filename": d.get("filename"),
                "downloaded_bytes": d.get("downloaded_bytes", 0),
                "total_bytes": d.get("total_bytes") or d.get("total_bytes_estimate") or 0,
                "speed": d.get("speed"),
                "eta": d.get("eta"),
            }))
        elif d.get("status") == "finished":
            event_q.put(ProgressEvent(EventType.PROGRESS, {
                "stage": "processing",
                "filename": d.get("filename"),
            }))

    def postprocessor_hook(d):
        event_q.put(ProgressEvent(EventType.LOG, {
            "message": f"{d.get('postprocessor')}: {d.get('status')}"
        }))

    common = {
        "outtmpl": outtmpl,
        "ffmpeg_location": settings.ffmpeg_location or find_ffmpeg(),
        "progress_hooks": [progress_hook],
        "postprocessor_hooks": [postprocessor_hook],
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "logger": _YdlLogger(event_q),
    }

    if settings.mode == Mode.MP3:
        common.update({
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": settings.mp3_bitrate,
                },
            ],
        })
        if settings.embed_thumbnail:
            common["postprocessors"].append({"key": "EmbedThumbnail"})
            common["postprocessors"].append({"key": "FFmpegMetadata"})
            common["writethumbnail"] = True
    else:
        common.update({
            "format": _build_format_selector(settings.max_height, settings.video_codec),
            "merge_output_format": "mp4",
            "postprocessors": [
                {"key": "FFmpegVideoConvertor", "preferedformat": "mp4"},
                {"key": "FFmpegMetadata"},
            ],
            "postprocessor_args": {
                "default": ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k"],
            },
        })

    return common


class _YdlLogger:
    """Routes yt-dlp's internal logging into our event queue instead of stdout."""

    def __init__(self, event_q: "queue.Queue[ProgressEvent]"):
        self.event_q = event_q

    def debug(self, msg):
        if msg.startswith("[debug]"):
            return
        self.event_q.put(ProgressEvent(EventType.LOG, {"message": msg}))

    def info(self, msg):
        self.event_q.put(ProgressEvent(EventType.LOG, {"message": msg}))

    def warning(self, msg):
        self.event_q.put(ProgressEvent(EventType.LOG, {"message": f"WARNING: {msg}"}))

    def error(self, msg):
        self.event_q.put(ProgressEvent(EventType.LOG, {"message": f"ERROR: {msg}"}))


def run_download(settings: DownloadSettings, event_q: "queue.Queue[ProgressEvent]", cancel_event: threading.Event):
    """Blocking call — run this in a background thread."""
    try:
        ydl_opts = _build_ydl_opts(settings, event_q)

        class _CancelCheckYDL(yt_dlp.YoutubeDL):
            def process_info(self, info_dict):
                if cancel_event.is_set():
                    raise yt_dlp.utils.DownloadCancelled("Cancelled by user")
                return super().process_info(info_dict)

        with _CancelCheckYDL(ydl_opts) as ydl:
            ydl.download([settings.url])

        event_q.put(ProgressEvent(EventType.DONE, {"url": settings.url}))
    except yt_dlp.utils.DownloadCancelled:
        event_q.put(ProgressEvent(EventType.ERROR, {"message": "Cancelled by user"}))
    except Exception as e:  # noqa: BLE001
        event_q.put(ProgressEvent(EventType.ERROR, {"message": str(e)}))


def start_download_thread(settings: DownloadSettings) -> tuple[threading.Thread, "queue.Queue[ProgressEvent]", threading.Event]:
    event_q: "queue.Queue[ProgressEvent]" = queue.Queue()
    cancel_event = threading.Event()
    t = threading.Thread(target=run_download, args=(settings, event_q, cancel_event), daemon=True)
    t.start()
    return t, event_q, cancel_event
