#!/usr/bin/env python3
"""
Cross-platform build script.

Run this ON each target OS (PyInstaller does not cross-compile):
    python build.py

Produces a standalone app in dist/:
  - macOS   -> dist/Tubeforge.app
  - Windows -> dist/Tubeforge.exe
  - Linux   -> dist/Tubeforge
"""

import platform
import subprocess
import sys

APP_NAME = "Tubeforge"


def main():
    system = platform.system()
    args = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--collect-all", "customtkinter",
        "--collect-all", "yt_dlp",
        "--collect-all", "imageio_ffmpeg",
        "main.py",
    ]

    if system == "Darwin":
        print("Building for macOS...")
    elif system == "Windows":
        print("Building for Windows...")
    elif system == "Linux":
        print("Building for Linux...")
    else:
        print(f"Unrecognized platform: {system}, attempting generic build...")

    subprocess.check_call(args)
    print(f"\nDone. Find your build in the 'dist' folder.")


if __name__ == "__main__":
    main()
