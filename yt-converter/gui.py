"""
Dark-themed CustomTkinter GUI for the YouTube -> MP3/MP4 converter.
"""

from __future__ import annotations

import os
import queue
import threading
import webbrowser
from tkinter import filedialog, messagebox

import customtkinter as ctk

import settings as app_settings
from downloader import (
    DownloadSettings,
    EventType,
    MP3_BITRATES,
    Mode,
    VIDEO_CODECS,
    VIDEO_QUALITIES,
    fetch_info,
    start_download_thread,
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

ACCENT = "#3b82f6"
BG = "#111318"
PANEL = "#181b22"
SUBTLE = "#8a8f98"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Tubeforge — YouTube to MP3/MP4")
        self.geometry("880x640")
        self.minsize(760, 560)
        self.configure(fg_color=BG)

        self.output_dir = ctk.StringVar(value=app_settings.get_output_dir())
        self.mode = ctk.StringVar(value=Mode.MP4.value)
        self.mp3_bitrate = ctk.StringVar(value="192")
        self.video_quality = ctk.StringVar(value="Best available")
        self.video_codec = ctk.StringVar(value="Auto (recommended)")
        self.status_text = ctk.StringVar(value="Paste a YouTube URL to begin.")

        self._current_thread = None
        self._current_queue: "queue.Queue | None" = None
        self._cancel_event: "threading.Event | None" = None

        self._build_layout()

    # ------------------------------------------------------------------ UI
    def _build_layout(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 8))
        ctk.CTkLabel(header, text="Tubeforge", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")
        ctk.CTkLabel(header, text="  YouTube → MP3 / MP4", text_color=SUBTLE,
                     font=ctk.CTkFont(size=14)).pack(side="left")

        # URL row
        url_frame = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10)
        url_frame.grid(row=1, column=0, sticky="ew", padx=24, pady=8)
        url_frame.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(url_frame, placeholder_text="Paste YouTube video or playlist URL...",
                                       height=40, font=ctk.CTkFont(size=13))
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(12, 8), pady=12)
        self.fetch_btn = ctk.CTkButton(url_frame, text="Fetch Info", width=110, height=40,
                                        command=self._on_fetch_info)
        self.fetch_btn.grid(row=0, column=1, padx=(0, 12), pady=12)

        # Options panel
        opts = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10)
        opts.grid(row=2, column=0, sticky="ew", padx=24, pady=8)
        for c in range(4):
            opts.grid_columnconfigure(c, weight=1)

        # Mode switch
        mode_frame = ctk.CTkFrame(opts, fg_color="transparent")
        mode_frame.grid(row=0, column=0, columnspan=4, sticky="ew", padx=12, pady=(14, 6))
        ctk.CTkLabel(mode_frame, text="Output format", text_color=SUBTLE).pack(side="left", padx=(0, 12))
        self.mp4_radio = ctk.CTkRadioButton(mode_frame, text="MP4 (video)", variable=self.mode,
                                             value=Mode.MP4.value, command=self._refresh_option_visibility)
        self.mp4_radio.pack(side="left", padx=8)
        self.mp3_radio = ctk.CTkRadioButton(mode_frame, text="MP3 (audio)", variable=self.mode,
                                             value=Mode.MP3.value, command=self._refresh_option_visibility)
        self.mp3_radio.pack(side="left", padx=8)

        # Video options
        self.video_opts = ctk.CTkFrame(opts, fg_color="transparent")
        self.video_opts.grid(row=1, column=0, columnspan=4, sticky="ew", padx=12, pady=6)
        ctk.CTkLabel(self.video_opts, text="Quality", text_color=SUBTLE, width=90, anchor="w").pack(side="left")
        ctk.CTkOptionMenu(self.video_opts, variable=self.video_quality,
                           values=list(VIDEO_QUALITIES.keys()), width=180).pack(side="left", padx=(0, 20))
        ctk.CTkLabel(self.video_opts, text="Codec", text_color=SUBTLE, width=60, anchor="w").pack(side="left")
        ctk.CTkOptionMenu(self.video_opts, variable=self.video_codec,
                           values=list(VIDEO_CODECS.keys()), width=200).pack(side="left")

        # Audio options
        self.audio_opts = ctk.CTkFrame(opts, fg_color="transparent")
        ctk.CTkLabel(self.audio_opts, text="Bitrate", text_color=SUBTLE, width=90, anchor="w").pack(side="left")
        ctk.CTkOptionMenu(self.audio_opts, variable=self.mp3_bitrate,
                           values=[f"{b} kbps" for b in MP3_BITRATES],
                           command=self._on_bitrate_selected, width=140).pack(side="left")

        # Output dir
        out_frame = ctk.CTkFrame(opts, fg_color="transparent")
        out_frame.grid(row=2, column=0, columnspan=4, sticky="ew", padx=12, pady=(6, 14))
        ctk.CTkLabel(out_frame, text="Save to", text_color=SUBTLE, width=90, anchor="w").pack(side="left")
        self.out_entry = ctk.CTkEntry(out_frame, textvariable=self.output_dir)
        self.out_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(out_frame, text="Browse", width=90, command=self._browse_output_dir).pack(side="left")

        hint_frame = ctk.CTkFrame(opts, fg_color="transparent")
        hint_frame.grid(row=3, column=0, columnspan=4, sticky="ew", padx=12, pady=(0, 10))
        ctk.CTkLabel(
            hint_frame,
            text="If you don't choose a folder, files save to ~/Downloads/Tubeforge automatically. "
                 "Your choice is remembered next time you open the app.",
            text_color=SUBTLE, font=ctk.CTkFont(size=11), anchor="w",
        ).pack(side="left")

        self._refresh_option_visibility()

        # Log / progress area
        body = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10)
        body.grid(row=3, column=0, sticky="nsew", padx=24, pady=8)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)

        self.video_title_label = ctk.CTkLabel(body, text="", font=ctk.CTkFont(size=14, weight="bold"),
                                               anchor="w", justify="left", wraplength=780)
        self.video_title_label.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 4))

        self.log_box = ctk.CTkTextbox(body, fg_color="#0d0f14", font=ctk.CTkFont(size=12, family="Menlo"))
        self.log_box.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 8))
        self.log_box.configure(state="disabled")

        self.progress_bar = ctk.CTkProgressBar(body, progress_color=ACCENT)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 12))

        # Footer / actions
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=4, column=0, sticky="ew", padx=24, pady=(4, 20))
        footer.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(footer, textvariable=self.status_text, text_color=SUBTLE, anchor="w")
        self.status_label.grid(row=0, column=0, sticky="w")

        self.cancel_btn = ctk.CTkButton(footer, text="Cancel", width=100, fg_color="#3a3d45",
                                         hover_color="#4a4d55", command=self._on_cancel, state="disabled")
        self.cancel_btn.grid(row=0, column=1, padx=(0, 8))
        self.download_btn = ctk.CTkButton(footer, text="Download", width=140, height=38,
                                           fg_color=ACCENT, command=self._on_download)
        self.download_btn.grid(row=0, column=2)

    def _refresh_option_visibility(self):
        if self.mode.get() == Mode.MP4.value:
            self.audio_opts.grid_forget()
            self.video_opts.grid(row=1, column=0, columnspan=4, sticky="ew", padx=12, pady=6)
        else:
            self.video_opts.grid_forget()
            self.audio_opts.grid(row=1, column=0, columnspan=4, sticky="ew", padx=12, pady=6)

    def _on_bitrate_selected(self, value: str):
        self.mp3_bitrate.set(value.replace(" kbps", ""))

    def _browse_output_dir(self):
        d = filedialog.askdirectory(initialdir=self.output_dir.get() or os.path.expanduser("~"))
        if d:
            self.output_dir.set(d)
            app_settings.set_output_dir(d)

    def _log(self, message: str):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message.rstrip() + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    # ------------------------------------------------------------ actions
    def _on_fetch_info(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("No URL", "Paste a YouTube URL first.")
            return
        self.fetch_btn.configure(state="disabled", text="Fetching...")
        self.status_text.set("Fetching video info...")

        def worker():
            try:
                info = fetch_info(url)
                self.after(0, lambda: self._show_info(info))
            except Exception as e:  # noqa: BLE001
                self.after(0, lambda: self._show_fetch_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _show_info(self, info: dict):
        self.fetch_btn.configure(state="normal", text="Fetch Info")
        if info.get("is_playlist"):
            self.video_title_label.configure(
                text=f"Playlist: {info['title']}  ({info['count']} videos) — first video will be used for preview")
        else:
            mins = (info.get("duration") or 0) // 60
            secs = (info.get("duration") or 0) % 60
            self.video_title_label.configure(
                text=f"{info['title']}  •  {info.get('uploader', 'Unknown')}  •  {mins}:{secs:02d}")
        self.status_text.set("Ready to download.")

    def _show_fetch_error(self, msg: str):
        self.fetch_btn.configure(state="normal", text="Fetch Info")
        self.status_text.set("Could not fetch info.")
        messagebox.showerror("Fetch failed", msg)

    def _on_download(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("No URL", "Paste a YouTube URL first.")
            return
        out_dir = self.output_dir.get().strip()
        if not out_dir or not os.path.isdir(out_dir):
            messagebox.showwarning("Invalid folder", "Choose a valid output folder.")
            return

        mode = Mode(self.mode.get())
        settings = DownloadSettings(
            url=url,
            mode=mode,
            output_dir=out_dir,
            mp3_bitrate=self.mp3_bitrate.get(),
            max_height=VIDEO_QUALITIES.get(self.video_quality.get()),
            video_codec=VIDEO_CODECS.get(self.video_codec.get()),
        )

        self.download_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.progress_bar.set(0)
        self.status_text.set("Starting download...")
        self._log(f"Starting {mode.value.upper()} download: {url}")

        thread, event_q, cancel_event = start_download_thread(settings)
        self._current_thread = thread
        self._current_queue = event_q
        self._cancel_event = cancel_event
        self.after(100, self._poll_queue)

    def _on_cancel(self):
        if self._cancel_event:
            self._cancel_event.set()
            self.status_text.set("Cancelling...")

    def _poll_queue(self):
        q = self._current_queue
        if q is None:
            return
        try:
            while True:
                event = q.get_nowait()
                self._handle_event(event)
        except queue.Empty:
            pass

        if self._current_thread and self._current_thread.is_alive():
            self.after(100, self._poll_queue)

    def _handle_event(self, event):
        if event.type == EventType.PROGRESS:
            p = event.payload
            if p.get("stage") == "downloading":
                total = p.get("total_bytes") or 0
                done = p.get("downloaded_bytes") or 0
                frac = (done / total) if total else 0
                self.progress_bar.set(frac)
                speed = p.get("speed")
                speed_str = f"{speed / 1024 / 1024:.2f} MB/s" if speed else "..."
                eta = p.get("eta")
                eta_str = f"{eta}s" if eta is not None else "..."
                self.status_text.set(f"Downloading — {frac * 100:.0f}%  •  {speed_str}  •  ETA {eta_str}")
            elif p.get("stage") == "processing":
                self.status_text.set("Processing with ffmpeg...")
                self.progress_bar.set(1.0)
        elif event.type == EventType.LOG:
            self._log(event.payload.get("message", ""))
        elif event.type == EventType.DONE:
            self.status_text.set("Done! Saved to output folder.")
            self.progress_bar.set(1.0)
            self._reset_buttons()
            self._log("✔ Download complete.")
        elif event.type == EventType.ERROR:
            self.status_text.set("Failed.")
            self._reset_buttons()
            self._log(f"✖ Error: {event.payload.get('message')}")
            messagebox.showerror("Download failed", event.payload.get("message", "Unknown error"))

    def _reset_buttons(self):
        self.download_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
