"""
Cross-platform ffmpeg location helper.

Resolution order:
1. A user-configured path (settings.json), if valid.
2. A system-installed ffmpeg found on PATH.
3. The ffmpeg binary bundled by the `imageio-ffmpeg` package (auto-downloaded
   on first run for the current OS/arch). This means users on Mac, Windows,
   and Linux never have to manually install ffmpeg.
"""

import os
import shutil
import sys


def _bundled_ffmpeg_path() -> str | None:
    try:
        import imageio_ffmpeg
        path = imageio_ffmpeg.get_ffmpeg_exe()
        if path and os.path.exists(path):
            return path
    except Exception:
        pass
    return None


def find_ffmpeg(user_configured_path: str | None = None) -> str:
    """Return a usable path/command for ffmpeg, or raise RuntimeError."""
    # 1. User override
    if user_configured_path and os.path.exists(user_configured_path):
        return user_configured_path

    # 2. System PATH
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    # 3. Bundled binary (works identically on macOS / Windows / Linux)
    bundled = _bundled_ffmpeg_path()
    if bundled:
        return bundled

    raise RuntimeError(
        "Could not locate ffmpeg. Install it system-wide, or ensure the "
        "'imageio-ffmpeg' package is installed (pip install imageio-ffmpeg)."
    )


def ffmpeg_dir(user_configured_path: str | None = None) -> str:
    """yt-dlp wants the *directory* containing the ffmpeg binary."""
    return os.path.dirname(find_ffmpeg(user_configured_path))


if __name__ == "__main__":
    try:
        p = find_ffmpeg()
        print(f"ffmpeg found at: {p}")
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
