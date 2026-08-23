# Tubeforge — YouTube to MP3/MP4

Cross-platform desktop app (macOS, Windows, Linux) to download YouTube videos
as MP3 (audio, selectable bitrate) or MP4 (video, selectable resolution/codec).

Built with:
- **yt-dlp** — video/audio extraction and downloading
- **ffmpeg** — transcoding/muxing (auto-provided via `imageio-ffmpeg`, no manual install needed)
- **CustomTkinter** — dark, modern cross-platform GUI

## Features

- Paste a URL, fetch title/duration/uploader before downloading
- MP4 mode: choose max resolution (360p → 4K or "best available") and preferred codec
- MP3 mode: choose bitrate (64–320 kbps)
- Live progress bar with download speed / ETA
- Cancel mid-download
- Embedded thumbnail + metadata on MP3 exports
- Runs identically on Mac, Windows, and Linux — ffmpeg is bundled automatically

## Quick start (run from source)

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Building a standalone executable (the thing you send to people)

PyInstaller doesn't cross-compile — a Windows `.exe` must be built on Windows,
a Mac `.app` on Mac. Two ways to get all three:

### Option A — GitHub Actions (recommended, no Windows/Mac machine needed)

1. Push this project to a GitHub repo.
2. It'll build automatically on every push to `main` (see
   `.github/workflows/build.yml`). Go to the **Actions** tab → the latest run
   → download `Tubeforge-Windows`, `Tubeforge-macOS`, `Tubeforge-Linux` from
   **Artifacts**.
3. For a proper downloadable release page (clickable .zip links, no GitHub
   login needed to grab them), tag a version:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
   This creates a GitHub Release with all three zipped builds attached —
   that's the link you'd send people.

### Option B — Build locally on each OS

Run this on each machine you have access to:

```bash
python build.py
```

Output:
- macOS → `dist/Tubeforge.app`
- Windows → `dist/Tubeforge.exe`
- Linux → `dist/Tubeforge`

### Sending it to people

- **Windows**: zip `Tubeforge.exe` and send it. First launch may trigger a
  Windows SmartScreen warning since the exe isn't code-signed — recipients
  click "More info" → "Run anyway". Signing costs money (a cert) and isn't
  necessary for sharing with friends.
- **macOS**: same idea with Gatekeeper — unsigned apps need
  right-click → Open the first time. Zip `Tubeforge.app` before sending, or
  macOS's quarantine flag can get extra fussy with raw .app files over
  chat apps.
- **Linux**: `chmod +x Tubeforge` then run.

## Where downloads are saved

- If the user never picks a folder, files go to `~/Downloads/Tubeforge`
  (created automatically on first run).
- The **Browse** button lets them pick any folder.
- Whatever they last picked is remembered automatically between app restarts
  (stored in a small settings file — `settings.py` handles this, saved to the
  OS-appropriate config location: `%APPDATA%\Tubeforge` on Windows,
  `~/Library/Application Support/Tubeforge` on Mac, `~/.config/Tubeforge` on
  Linux).

## Project structure

```
main.py            Entry point
gui.py              CustomTkinter dark UI
downloader.py       yt-dlp wrapper: format selection, threading, progress events
ffmpeg_utils.py     Cross-platform ffmpeg binary resolution
build.py            PyInstaller packaging script
requirements.txt
```

## Notes / things worth deciding on next

- **Playlists**: `fetch_info` already detects playlists and returns per-entry
  data, but `downloader.run_download` currently forces `noplaylist: True` for
  a simpler single-video flow. Flip that + add a queue UI if you want batch
  playlist downloads.
- **Filename template**: currently `%(title)s.%(ext)s`. Could expose this as
  a settings field (e.g. include uploader, date, resolution).
- **Legal**: downloading YouTube content may violate YouTube's Terms of
  Service depending on the content and your jurisdiction — worth a disclaimer
  in-app if you're distributing this beyond personal use.
