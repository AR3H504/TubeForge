#!/usr/bin/env python3
"""
Cross-platform build script.

Run this ON each target OS (PyInstaller does not cross-compile):
    python build.py

Produces a standalone app FOLDER in dist/ (not a single exe file). This is
deliberate: --onefile bundles self-extract to the system temp directory
(often /tmp) on every launch, which fails outright on VMs/containers that
mount /tmp as noexec (a common hardening default) — ffmpeg silently "isn't
installed" because the OS refuses to execute anything extracted there.
A folder build runs entirely from wherever the user puts it, no temp
extraction, so that whole failure class goes away.

Result:
  - macOS   -> dist/Tubeforge.app        (still a proper double-clickable app)
  - Windows -> dist/Tubeforge/Tubeforge.exe  (run the exe inside the folder)
  - Linux   -> dist/Tubeforge/Tubeforge      (run the binary inside the folder)

To distribute: zip the whole dist/Tubeforge folder (or dist/Tubeforge.app on
Mac) and send that. Recipients unzip and run the executable inside it.
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
        # No --onefile: see module docstring for why (noexec /tmp issue).
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
