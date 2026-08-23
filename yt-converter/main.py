#!/usr/bin/env python3
"""
Tubeforge — YouTube to MP3/MP4 converter.
Cross-platform entry point (macOS, Windows, Linux).
"""

import sys

if __name__ == "__main__":
    if "--check-ffmpeg" in sys.argv:
        # Diagnostic mode: print what ffmpeg path resolution finds and exit,
        # without opening the GUI. Useful for debugging packaged builds.
        from ffmpeg_utils import find_ffmpeg
        try:
            print("FFMPEG_PATH:", find_ffmpeg())
            sys.exit(0)
        except Exception as e:  # noqa: BLE001
            print("FFMPEG_ERROR:", e)
            sys.exit(1)

    from gui import main
    sys.exit(main() or 0)
