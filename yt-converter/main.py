#!/usr/bin/env python3
"""
Tubeforge — YouTube to MP3/MP4 converter.
Cross-platform entry point (macOS, Windows, Linux).
"""

import sys

from gui import main

if __name__ == "__main__":
    sys.exit(main() or 0)
