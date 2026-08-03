"""
main.py — YT Downloader Kivy App (Android APK)
Faithful replica of the Tkinter desktop UI (app.py).
Entry point for Buildozer and desktop testing.
"""

import os
import sys
import threading
import urllib.request
import webbrowser
import io
import traceback

import yt_dlp
from yt_dlp.utils import DownloadCancelled

from kivy.app import App
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.core.image import Image as CoreImage
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.properties import StringProperty, NumericProperty, BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex

# ── Android detection ───────────────────────────────────────────────────────────
try:
    from android.permissions import Permission, request_permissions
    from android.storage import primary_external_storage_path
    IS_ANDROID = True
    print("Android detected - running on device")
except ImportError:
    IS_ANDROID = False
    print("Running on desktop")

# ── Download logic ───────────────────────────────────────────────────────────────
VIDEO_RESOLUTIONS = ["Best", "4K (2160p)", "1440p", "1080p", "720p", "480p", "360p"]
AUDIO_FORMATS = ["mp3", "m4a", "aac", "opus", "wav"]
AUDIO_QUALITIES = ["320 kbps", "256 kbps", "192 kbps", "128 kbps", "96 kbps", "64 kbps"]

_RES_FORMAT = {
    "Best": "bestvideo+bestaudio/best",
    "4K (2160p)": "bestvideo[height<=2160]+bestaudio/best",
    "1440p": "bestvideo[height<=1440]+bestaudio/best",
    "1080p": "bestvideo[height<=1080]+bestaudio/best",
    "720p": "bestvideo[height<=720]+bestaudio/best",
    "480p": "bestvideo[height<=480]+bestaudio/best",
    "360p": "bestvideo[height<=360]+bestaudio/best",
}


def _is_android_runtime():
    return "ANDROID_ARGUMENT" in os.environ or "P4A_BOOTSTRAP" in os.environ


def _get_ffmpeg_location():
    if _is_android_runtime():
        candidate_paths = [
            "/data/data/org.test.ytdownloader/files/app/_python_bundle/site-packages/ffmpeg",
            "/data/data/org.kivy.android/files/app/ffmpeg",
        ]
        for path in candidate_paths:
            if os.path.exists(path):
                return path
        return None

    ffmpeg_names = ["ffmpeg.exe", "ffmpeg"]
    for search_dir in [os.path.dirname(sys.executable), os.path.dirname(sys.argv[0])]:
        if not search_dir:
            continue
        for name in ffmpeg_names:
            candidate = os.path.join(search_dir, name)
            if os.path.exists(candidate):
                return search_dir

    return None


def download_media(
    url: str,
    media_type: str,
    output_path: str = ".",
    resolution: str = "720p",
    audio_format: str = "mp3",
    audio_quality: str = "192 kbps",
    progress_hook=None,
    cancel_check=None,
):
    ffmpeg_path = _get_ffmpeg_location()
    bitrate = audio_quality.replace(" kbps", "")

    base = {
        "socket_timeout": 30,
        "retries": 10,
        "fragment_retries": 10,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "outtmpl": os.path.join(output_path, "%(title)s.%(ext)s"),
    }

    if ffmpeg_path:
        base["ffmpeg_location"] = ffmpeg_path

    def _progress_wrapper(d):
        if cancel_check and cancel_check():
            raise DownloadCancelled("Download cancelled by user.")
        if progress_hook:
            progress_hook(d)

    if progress_hook:
        base["progress_hooks"] = [_progress_wrapper]

    if media_type == "audio":
        tag = f"{audio_format.upper()} {bitrate}kbps"
        opts = {
            **base,
            "outtmpl": os.path.join(output_path, f"%(title)s [{tag}].%(ext)s"),
            "format": "bestaudio/best",
        }
        if ffmpeg_path:
            opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": audio_format,
                    "preferredquality": bitrate,
                }
            ]
    else:
        opts = {
            **base,
            "outtmpl": os.path.join(output_path, f"%(title)s [{resolution}].%(ext)s"),
            "format": _RES_FORMAT.get(resolution, _RES_FORMAT["720p"]),
            "merge_output_format": "mp4",
        }
        if ffmpeg_path:
            opts["postprocessor_args"] = {
                "merger+ffmpeg_o": ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k"],
            }

    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])


# ── Output path ─────────────────────────────────────────────────────────────────
if IS_ANDROID:
    try:
        OUT_DIR = os.path.join(primary_external_storage_path(), "Download", "YTDownloader")
    except Exception:
        # Fallback for PyDroid3
        OUT_DIR = os.path.join(os.path.expanduser("~"), "storage", "downloads")
else:
    OUT_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
os.makedirs(OUT_DIR, exist_ok=True)
print(f"Output directory: {OUT_DIR}")

# ── Branding ────────────────────────────────────────────────────────────────────
APP_NAME = "YT Downloader"
APP_VERSION = "v2.0.0"
DEV_NAME = "Tony Bbosa"
DEV_ROLE = "Full-Stack Developer"
DEV_CONTACT = "github.com/tonybbosa"

# ── Ad config — swap these to change the ad ─────────────────────────────────────
AD_IMAGE_URL = ""   # e.g. "https://yourcdn.com/banner.png"
AD_CLICK_URL = ""   # e.g. "https://your-sponsor.com"

# ── Colour palette (exact match with app.py) ────────────────────────────────────
BG       = get_color_from_hex("#0d1117")
SURFACE  = get_color_from_hex("#161b22")
SURF2    = get_color_from_hex("#21262d")
BORDER   = get_color_from_hex("#30363d")
ACCENT   = get_color_from_hex("#e94560")
ACCENT_H = get_color_from_hex("#c73652")
TEXT     = get_color_from_hex("#e6edf3")
SUBTEXT  = get_color_from_hex("#8b949e")
MUTED    = get_color_from_hex("#484f58")

# ── KV rules (reusable widget styles) ──────────────────────────────────────────
Builder.load_string("""
#:import dp  kivy.metrics.dp
#:import sp  kivy.metrics.sp
#:import hex kivy.utils.get_color_from_hex
#:import NumericProperty kivy.properties.NumericProperty

<SecLabel@Label>:
    font_size:    sp(10)
    bold:         True
    color:        hex('#8b949e')
    size_hint_y:  None
    height:       dp(26)
    halign:       'left'
    valign:       'bottom'
    text_size:    self.width, None

<DivLine@Widget>:
    size_hint_y: None
    height: dp(1)
    canvas:
        Color:
            rgba: hex('#30363d')
        Rectangle:
            pos:  self.pos
            size: self.size

<StyledBar@Widget>:
    value:          NumericProperty(0)
    max:            NumericProperty(100)
    size_hint_y:    None
    height:         dp(10)
    canvas:
        Color:
            rgba: hex('#21262d')
        RoundedRectangle:
            pos:    self.pos
            size:   self.size
            radius: [dp(5)]
        Color:
            rgba: hex('#e94560')
        RoundedRectangle:
            pos:    self.pos
            size:   self.width * (self.value / self.max if self.max else 0), self.height
            radius: [dp(5)]
""")


# ═══════════════════════════════════════════════════════════════════════════════
#  Widget helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _attach_bg(widget, color, radius=0):
    """Attach a live background rect (or rounded rect) to any widget."""
    with widget.canvas.before:
        clr = Color(*color)
        if radius:
            rect = RoundedRectangle(
                pos=widget.pos, size=widget.size, radius=[dp(radius)]
            )
        else:
            rect = Rectangle(pos=widget.pos, size=widget.size)
    widget.bind(
        pos=lambda *_: setattr(rect, "pos", widget.pos),
        size=lambda *_: setattr(rect, "size", widget.size),
    )
    return clr, rect


def _swap_bg(widget, color, radius=8):
    """Clear and re-attach a rounded background (for button state changes)."""
    widget.canvas.before.clear()
    _attach_bg(widget, color, radius)


def make_label(text, font_size=14, color=None, bold=False, height=None, halign="left"):
    lbl = Label(
        text=text,
        font_size=sp(font_size),
        bold=bold,
        color=color or TEXT,
        size_hint_y=None if height else 1,
        height=dp(height) if height else 0,
        halign=halign,
    )
    lbl.bind(size=lambda *_: setattr(lbl, "text_size", (lbl.width, None)))
    return lbl


def make_input(hint=""):
    return TextInput(
        hint_text=hint,
        hint_text_color=MUTED,
        background_color=SURF2,
        foreground_color=TEXT,
        cursor_color=ACCENT,
        font_size=sp(14),
        padding=[dp(12), dp(10)],
        size_hint_y=None,
        height=dp(48),
        multiline=False,
    )


def make_button(text, bg=SURF2, fg=SUBTEXT, height=48, font_size=12, bold=True, radius=8):
    btn = Button(
        text=text,
        color=fg,
        font_size=sp(font_size),
        bold=bold,
        background_color=(0, 0, 0, 0),
        background_normal="",
        size_hint_y=None,
        height=dp(height),
    )
    _attach_bg(btn, bg, radius)

    def _on_state(inst, val):
        _swap_bg(inst, ACCENT_H if val == "down" else bg, radius)

    btn.bind(state=_on_state)
    return btn


def make_accent_btn(text, height=54, font_size=14):
    return make_button(
        text, bg=ACCENT, fg=TEXT, height=height, font_size=font_size, bold=True
    )


def make_spinner(values, default, height=46):
    spn = Spinner(
        text=default,
        values=values,
        background_color=(0, 0, 0, 0),
        background_normal="",
        color=TEXT,
        font_size=sp(13),
        size_hint_y=None,
        height=dp(height),
    )
    _attach_bg(spn, SURF2, radius=8)
    return spn


def make_seg_button(text, group, height=46):
    """Segmented-control button (like the Tkinter toggle pair)."""
    tb = ToggleButton(
        text=text,
        group=group,
        background_color=(0, 0, 0, 0),
        background_normal="",
        background_down="",
        color=TEXT,
        font_size=sp(12),
        bold=True,
        size_hint_y=None,
        height=dp(height),
    )
    _attach_bg(tb, SURF2, radius=8)

    def _on_state(inst, val):
        _swap_bg(inst, ACCENT if val == "down" else SURF2, radius=8)

    tb.bind(state=_on_state)
    return tb


def fmt_bytes(n):
    """Format bytes to human-readable string."""
    if not n:
        return "?"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.2f} TB"


# ═══════════════════════════════════════════════════════════════════════════════
#  Popup helper (replaces messagebox from Tkinter)
# ═══════════════════════════════════════════════════════════════════════════════


def show_popup(title, message):
    """Show a Kivy popup dialog (info, warning, or error)."""
    box = BoxLayout(
        orientation="vertical",
        padding=[dp(20), dp(16)],
        spacing=dp(12),
        size_hint=(None, None),
        size=(dp(320), dp(180)),
    )
    _attach_bg(box, SURFACE, radius=12)

    lbl = Label(
        text=str(message),
        font_size=sp(13),
        color=TEXT,
        halign="center",
        valign="middle",
        size_hint_y=None,
        height=dp(80),
    )
    lbl.bind(size=lambda *_: setattr(lbl, "text_size", (lbl.width, None)))
    box.add_widget(lbl)

    ok_btn = make_accent_btn("OK", height=44, font_size=13)
    popup = Popup(
        title=title,
        title_size=sp(15),
        title_color=TEXT,
        separator_color=ACCENT,
        content=box,
        size_hint=(None, None),
        size=(dp(340), dp(200)),
        auto_dismiss=True,
        background_color=(0, 0, 0, 0),
    )

    def dismiss(*_):
        popup.dismiss()

    ok_btn.bind(on_release=dismiss)
    box.add_widget(ok_btn)
    popup.open()


# ═══════════════════════════════════════════════════════════════════════════════
#  Main layout — faithful replica of the Tkinter app.py UI
# ═══════════════════════════════════════════════════════════════════════════════


class YTDownloaderLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        _attach_bg(self, BG)
        self._media_type = "video"
        self._cancel_flag = threading.Event()
        self._current_thread = None

        # Request Android permissions
        if IS_ANDROID:
            try:
                request_permissions(
                    [
                        Permission.INTERNET,
                        Permission.WRITE_EXTERNAL_STORAGE,
                        Permission.READ_EXTERNAL_STORAGE,
                    ]
                )
                print("Android permissions requested")
            except Exception as e:
                print(f"Permission request failed: {e}")

        print("Building UI...")
        self._build()
        print("UI built successfully")

    # ══════════════════════════════════════════════════════════════════════════
    #  Build
    # ══════════════════════════════════════════════════════════════════════════

    def _build(self):
        self._build_header()
        self._build_body()
        self._build_ad_banner()
        self._build_footer()

    # ══════════════════════════════════════════════════════════════════════════
    #  Header — Red accent bar with icon, title, subtitle, version badge
    # ══════════════════════════════════════════════════════════════════════════

    def _build_header(self):
        hdr = BoxLayout(
            size_hint_y=None, height=dp(60), padding=[dp(18), 0], spacing=dp(10)
        )
        _attach_bg(hdr, ACCENT)

        # Left side — icon + title + subtitle
        left = BoxLayout(orientation="horizontal", spacing=dp(10))
        left.size_hint_x = None
        left.width = dp(200)

        icon = make_label("▶", font_size=22, color=TEXT, bold=True, height=60)
        icon.size_hint_x = None
        icon.width = dp(32)
        left.add_widget(icon)

        info = BoxLayout(orientation="vertical", padding=[0, dp(8), 0, dp(10)])
        info.add_widget(
            make_label(APP_NAME, font_size=15, color=TEXT, bold=True, height=24)
        )
        info.add_widget(
            make_label(
                "Fast  •  Simple  •  Reliable",
                font_size=9,
                color=(1, 1, 1, 0.6),
                height=16,
            )
        )
        left.add_widget(info)
        hdr.add_widget(left)

        # Right side — version badge (dark red pill)
        badge = BoxLayout(
            size_hint_x=None,
            size_hint_y=None,
            width=dp(50),
            height=dp(28),
            padding=[dp(10), dp(4)],
        )
        _attach_bg(badge, ACCENT_H, radius=4)
        badge_text = Label(
            text=APP_VERSION,
            font_size=sp(8),
            bold=True,
            color=TEXT,
            halign="center",
            valign="middle",
        )
        badge.add_widget(badge_text)

        # Right-align wrapper
        right = BoxLayout(size_hint_x=None, width=dp(70))
        right.add_widget(Widget())  # spacer
        right.add_widget(badge)
        hdr.add_widget(right)

        self.add_widget(hdr)

    # ══════════════════════════════════════════════════════════════════════════
    #  Body — scrollable content area
    # ══════════════════════════════════════════════════════════════════════════

    def _build_body(self):
        scroll = ScrollView(do_scroll_x=False)
        _attach_bg(scroll, SURFACE)

        self._box = BoxLayout(
            orientation="vertical",
            padding=[dp(20), dp(16)],
            spacing=dp(10),
            size_hint_y=None,
        )
        self._box.bind(minimum_height=self._box.setter("height"))
        _attach_bg(self._box, SURFACE)

        self._sec_url()
        self._sec_type()
        self._sec_options()

        # Divider line
        divider = Widget(size_hint_y=None, height=dp(1))
        with divider.canvas.before:
            Color(*BORDER)
            r = Rectangle(pos=divider.pos, size=divider.size)
        divider.bind(
            pos=lambda *_: setattr(r, "pos", divider.pos),
            size=lambda *_: setattr(r, "size", divider.size),
        )
        self._box.add_widget(divider)

        self._sec_save()
        self._sec_download()
        self._sec_progress()

        scroll.add_widget(self._box)
        self.add_widget(scroll)

    def _add(self, w):
        self._box.add_widget(w)

    # ══════════════════════════════════════════════════════════════════════════
    #  VIDEO URL
    # ══════════════════════════════════════════════════════════════════════════

    def _sec_url(self):
        self._add(
            make_label("VIDEO URL", font_size=10, color=SUBTEXT, bold=True, height=26)
        )
        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        self._url_in = make_input("https://youtube.com/watch?v=...")
        paste = make_button("PASTE", height=48, font_size=10)
        paste.size_hint_x = None
        paste.width = dp(80)
        paste.bind(on_release=self._paste)
        row.add_widget(self._url_in)
        row.add_widget(paste)
        self._add(row)

    # ══════════════════════════════════════════════════════════════════════════
    #  DOWNLOAD TYPE — segmented toggle
    # ══════════════════════════════════════════════════════════════════════════

    def _sec_type(self):
        self._add(
            make_label(
                "DOWNLOAD TYPE", font_size=10, color=SUBTEXT, bold=True, height=26
            )
        )
        row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        self._tb_video = make_seg_button("🎬  Video  (MP4)", group="dltype")
        self._tb_audio = make_seg_button("🎵  Audio Only", group="dltype")

        # Video is selected by default — set active state
        self._tb_video.state = "down"

        self._tb_video.bind(
            state=lambda _, s: self._set_type("video") if s == "down" else None
        )
        self._tb_audio.bind(
            state=lambda _, s: self._set_type("audio") if s == "down" else None
        )

        row.add_widget(self._tb_video)
        row.add_widget(self._tb_audio)
        self._add(row)

    # ══════════════════════════════════════════════════════════════════════════
    #  OPTIONS — switches between video / audio options
    # ══════════════════════════════════════════════════════════════════════════

    def _sec_options(self):
        self._add(
            make_label("OPTIONS", font_size=10, color=SUBTEXT, bold=True, height=26)
        )
        self._opts = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))

        self._res_spn = make_spinner(VIDEO_RESOLUTIONS, "720p")
        self._afmt_spn = make_spinner(AUDIO_FORMATS, "mp3")
        self._aqual_spn = make_spinner(AUDIO_QUALITIES, "192 kbps")

        # Default: show video resolution spinner
        self._opts.add_widget(self._res_spn)
        self._add(self._opts)

    # ══════════════════════════════════════════════════════════════════════════
    #  SAVE TO — path display (no browse on Android)
    # ══════════════════════════════════════════════════════════════════════════

    def _sec_save(self):
        self._add(
            make_label("SAVE TO", font_size=10, color=SUBTEXT, bold=True, height=26)
        )

        save_row = BoxLayout(
            size_hint_y=None, height=dp(48), spacing=dp(8)
        )
        short = OUT_DIR if len(OUT_DIR) < 40 else "…" + OUT_DIR[-38:]
        self._path_lbl = Label(
            text=short,
            font_size=sp(11),
            color=MUTED,
            halign="left",
            valign="middle",
            size_hint_y=None,
            height=dp(48),
        )
        self._path_lbl.bind(
            size=lambda *_: setattr(self._path_lbl, "text_size", (self._path_lbl.width, None))
        )
        save_row.add_widget(self._path_lbl)

        # BROWSE button only on desktop
        if not IS_ANDROID:
            browse = make_button("BROWSE", height=48, font_size=10)
            browse.size_hint_x = None
            browse.width = dp(80)
            browse.bind(on_release=self._browse)
            save_row.add_widget(browse)

        self._add(save_row)

    # ══════════════════════════════════════════════════════════════════════════
    #  DOWNLOAD + CANCEL buttons
    # ══════════════════════════════════════════════════════════════════════════

    def _sec_download(self):
        # Download button row with cancel
        dl_row = BoxLayout(size_hint_y=None, height=dp(54), spacing=dp(8))
        
        self._dl_btn = make_accent_btn("⬇   DOWNLOAD", height=54, font_size=14)
        self._dl_btn.bind(on_release=self._start)
        dl_row.add_widget(self._dl_btn)
        
        # Cancel button (hidden initially, shows during download)
        self._cancel_btn = make_button(
            "✕   CANCEL", 
            bg=ACCENT_H, 
            fg=TEXT, 
            height=54, 
            font_size=12,
            bold=True,
            radius=8
        )
        self._cancel_btn.size_hint_x = None
        self._cancel_btn.width = dp(100)
        self._cancel_btn.opacity = 0
        self._cancel_btn.disabled = True
        self._cancel_btn.bind(on_release=self._cancel_download)
        dl_row.add_widget(self._cancel_btn)
        
        self._add(dl_row)

    # ══════════════════════════════════════════════════════════════════════════
    #  Progress bar + info + status
    # ══════════════════════════════════════════════════════════════════════════

    def _sec_progress(self):
        # Custom styled progress bar
        self._bar = Builder.load_string("StyledBar:\n    value: 0\n    max: 100\n")
        self._add(self._bar)

        # Info line (size · speed · ETA) — accent colored
        self._info_lbl = make_label("", font_size=11, color=ACCENT, height=24)
        self._add(self._info_lbl)

        # Status line — subtext colored
        self._status_lbl = make_label("Ready", font_size=11, color=SUBTEXT, height=24)
        self._add(self._status_lbl)

    # ══════════════════════════════════════════════════════════════════════════
    #  Ad banner
    # ══════════════════════════════════════════════════════════════════════════

    def _build_ad_banner(self):
        """Ad banner with AD badge, placeholder text, and click-through."""
        # Thin top border
        border_line = Widget(size_hint_y=None, height=dp(1))
        with border_line.canvas.before:
            Color(*BORDER)
            r = Rectangle(pos=border_line.pos, size=border_line.size)
        border_line.bind(
            pos=lambda *_: setattr(r, "pos", border_line.pos),
            size=lambda *_: setattr(r, "size", border_line.size),
        )
        self.add_widget(border_line)

        self._ad_frame = BoxLayout(
            size_hint_y=None, height=dp(80), padding=[dp(10), 0]
        )
        _attach_bg(self._ad_frame, SURF2)

        # "AD" badge (top-right)
        ad_badge = Label(
            text="AD",
            font_size=sp(7),
            bold=True,
            color=SUBTEXT,
            size_hint_x=None,
            size_hint_y=None,
            width=dp(24),
            height=dp(16),
            halign="center",
            valign="middle",
        )
        _attach_bg(ad_badge, MUTED, radius=2)

        # Stack: ad content + badge overlay
        ad_stack = BoxLayout(size_hint_y=None, height=dp(80))
        _attach_bg(ad_stack, SURF2)

        self._ad_content = Label(
            text="📊  Advertise here  —  contact: tonybbosa@gmail.com",
            font_size=sp(9),
            color=MUTED,
            halign="center",
            valign="middle",
        )
        self._ad_content.bind(
            size=lambda *_: setattr(self._ad_content, "text_size",
                                    (self._ad_content.width, None))
        )
        ad_stack.add_widget(self._ad_content)

        # Click handler
        ad_stack.bind(on_touch_down=self._ad_touched)
        self._ad_stack = ad_stack

        # Overlay the AD badge on top-right of ad_stack
        ad_stack.add_widget(ad_badge)

        self.add_widget(self._ad_frame)

        # Load real banner image in background if URL is provided
        if AD_IMAGE_URL:
            threading.Thread(target=self._fetch_ad_image, daemon=True).start()

    def _fetch_ad_image(self):
        """Download banner image and display it (background thread)."""
        try:
            req = urllib.request.Request(
                AD_IMAGE_URL,
                headers={"User-Agent": "YTDownloader-AdClient/1.0"},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = resp.read()

            img = CoreImage(io.BytesIO(data), ext="png")
            Clock.schedule_once(lambda dt: self._show_ad_image(img))
        except Exception:
            pass  # Network issue / bad URL — placeholder stays

    def _show_ad_image(self, core_img):
        """Replace placeholder text with the loaded banner image."""
        try:
            texture = core_img.texture
            texture.wrap = "repeat"
            self._ad_content.canvas.before.clear()
            with self._ad_content.canvas.before:
                Color(1, 1, 1, 1)
                Rectangle(pos=self._ad_content.pos, size=self._ad_content.size,
                          texture=texture)
            self._ad_content.bind(
                pos=lambda *_: self._update_ad_texture_pos(),
                size=lambda *_: self._update_ad_texture_size(texture),
            )
            self._ad_text_ref = self._ad_content
            self._update_ad_texture_size(texture)
            self._update_ad_texture_pos()
        except Exception:
            pass

    def _update_ad_texture_pos(self):
        if hasattr(self, "_ad_text_ref"):
            for instr in self._ad_text_ref.canvas.before.children:
                if isinstance(instr, Rectangle):
                    instr.pos = self._ad_text_ref.pos
                    break

    def _update_ad_texture_size(self, texture):
        if hasattr(self, "_ad_text_ref"):
            for instr in self._ad_text_ref.canvas.before.children:
                if isinstance(instr, Rectangle):
                    instr.size = self._ad_text_ref.size
                    instr.texture = texture
                    break

    def _ad_touched(self, instance, touch):
        if AD_CLICK_URL and self._ad_stack.collide_point(*touch.pos):
            if not IS_ANDROID:
                webbrowser.open(AD_CLICK_URL)
            else:
                try:
                    from jnius import autoclass
                    Intent = autoclass('android.content.Intent')
                    Uri = autoclass('android.net.Uri')
                    PythonActivity = autoclass('org.kivy.android.PythonActivity')
                    currentActivity = PythonActivity.mActivity
                    intent = Intent(Intent.ACTION_VIEW)
                    intent.setData(Uri.parse(AD_CLICK_URL))
                    currentActivity.startActivity(intent)
                except Exception:
                    webbrowser.open(AD_CLICK_URL)

    # ══════════════════════════════════════════════════════════════════════════
    #  Footer — credits bar with accent top border
    # ══════════════════════════════════════════════════════════════════════════

    def _build_footer(self):
        foot = BoxLayout(size_hint_y=None, height=dp(44))
        _attach_bg(foot, SURF2)

        # Accent top border
        with foot.canvas.before:
            Color(*ACCENT)
            line = Rectangle(pos=foot.pos, size=(foot.width, dp(2)))
        foot.bind(
            pos=lambda *_: setattr(line, "pos", foot.pos),
            size=lambda *_: setattr(line, "size", (foot.width, dp(2))),
        )

        footer_text = f"{DEV_NAME}   ·   {DEV_ROLE}   ·   {DEV_CONTACT}   ·   {APP_VERSION}"
        lbl = make_label(
            footer_text,
            font_size=9,
            color=SUBTEXT,
            height=44,
            halign="center",
        )
        foot.add_widget(lbl)
        self.add_widget(foot)

    # ══════════════════════════════════════════════════════════════════════════
    #  Type switch
    # ══════════════════════════════════════════════════════════════════════════

    def _set_type(self, t):
        self._media_type = t
        self._opts.clear_widgets()
        if t == "video":
            self._opts.add_widget(self._res_spn)
        else:
            self._opts.add_widget(self._afmt_spn)
            self._opts.add_widget(self._aqual_spn)

    # ══════════════════════════════════════════════════════════════════════════
    #  Actions
    # ══════════════════════════════════════════════════════════════════════════

    def _paste(self, *_):
        try:
            self._url_in.text = Clipboard.paste()
        except Exception:
            pass

    def _browse(self, *_):
        """Open a folder picker dialog (desktop only)."""
        try:
            from plyer import filechooser
            result = filechooser.choose_dir(title="Select download folder")
            if result:
                global OUT_DIR
                selected = result[0]
                OUT_DIR = selected
                os.makedirs(OUT_DIR, exist_ok=True)
                short = OUT_DIR if len(OUT_DIR) < 40 else "…" + OUT_DIR[-38:]
                self._path_lbl.text = short
        except Exception:
            pass

    def _cancel_download(self, *_):
        """Cancel the ongoing download"""
        self._cancel_flag.set()
        self._cancel_btn.disabled = True
        self._set_status("Cancelling...")

    def _start(self, *_):
        url = self._url_in.text.strip()
        if not url:
            show_popup("No URL", "Please enter a YouTube URL.")
            return
        
        # Show cancel button, disable download button
        self._dl_btn.disabled = True
        self._dl_btn.opacity = 0.3
        self._cancel_btn.opacity = 1
        self._cancel_btn.disabled = False
        
        self._bar.value = 0
        self._info_lbl.text = ""
        self._set_status("Starting…")
        
        self._current_thread = threading.Thread(
            target=self._worker, 
            args=(url,), 
            daemon=True
        )
        self._current_thread.start()

    # ══════════════════════════════════════════════════════════════════════════
    #  Download worker
    # ══════════════════════════════════════════════════════════════════════════

    def _worker(self, url):
        def hook(d):
            if self._cancel_flag.is_set():
                raise DownloadCancelled("Download cancelled by user")

            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                done = d.get("downloaded_bytes", 0)
                speed = d.get("_speed_str", "").strip()
                eta = d.get("_eta_str", "").strip()

                size_str = (
                    f"{fmt_bytes(done)} / {fmt_bytes(total)}"
                    if total
                    else fmt_bytes(done)
                )
                parts = [size_str]
                if speed:
                    parts.append(speed)
                if eta:
                    parts.append(f"ETA {eta}")
                info = "   •   ".join(parts)

                if total:
                    pct = done / total * 100
                    Clock.schedule_once(
                        lambda dt, v=pct: setattr(self._bar, "value", v)
                    )
                    Clock.schedule_once(
                        lambda dt, v=pct: self._set_status(
                            f"Downloading…  {v:.1f}%"
                        )
                    )
                else:
                    Clock.schedule_once(
                        lambda dt: self._set_status("Downloading…")
                    )

                Clock.schedule_once(
                    lambda dt, s=info: setattr(self._info_lbl, "text", s)
                )

            elif d["status"] == "finished":
                Clock.schedule_once(lambda dt: setattr(self._bar, "value", 100))
                Clock.schedule_once(lambda dt: self._set_status("Finalising…"))
                Clock.schedule_once(
                    lambda dt: setattr(self._info_lbl, "text", "")
                )

        try:
            download_media(
                url=url,
                media_type=self._media_type,
                output_path=OUT_DIR,
                resolution=self._res_spn.text,
                audio_format=self._afmt_spn.text,
                audio_quality=self._aqual_spn.text,
                progress_hook=hook,
                cancel_check=self._cancel_flag.is_set,
            )
            if not self._cancel_flag.is_set():
                Clock.schedule_once(lambda dt: self._on_success())
            else:
                Clock.schedule_once(lambda dt: self._on_cancel())
        except DownloadCancelled:
            Clock.schedule_once(lambda dt: self._on_cancel())
        except Exception as e:
            Clock.schedule_once(lambda dt, m=str(e): self._on_error(m))

    def _set_status(self, text):
        Clock.schedule_once(
            lambda dt, t=text: setattr(self._status_lbl, "text", t)
        )

    def _on_success(self):
        self._current_thread = None
        self._cancel_flag.clear()
        self._bar.value = 100
        self._status_lbl.text = "✔   Download complete!"
        self._dl_btn.disabled = False
        self._dl_btn.opacity = 1
        self._cancel_btn.opacity = 0
        self._cancel_btn.disabled = True
        show_popup("Done", "Your file has been saved successfully.")

    def _on_cancel(self):
        """Handle successful cancellation"""
        self._current_thread = None
        self._bar.value = 0
        self._info_lbl.text = ""
        self._status_lbl.text = "✕   Download cancelled"
        self._dl_btn.disabled = False
        self._dl_btn.opacity = 1
        self._cancel_btn.opacity = 0
        self._cancel_btn.disabled = True
        self._cancel_flag.clear()

    def _on_error(self, msg):
        self._current_thread = None
        self._cancel_flag.clear()
        self._status_lbl.text = f"✖   {msg[:90]}"
        self._info_lbl.text = ""
        self._dl_btn.disabled = False
        self._dl_btn.opacity = 1
        self._cancel_btn.opacity = 0
        self._cancel_btn.disabled = True
        show_popup("Download Failed", msg[:200])


# ═══════════════════════════════════════════════════════════════════════════════
#  App entry point
# ═══════════════════════════════════════════════════════════════════════════════


class YTDownloaderApp(App):
    def build(self):
        print("Starting YT Downloader App...")
        self.title = APP_NAME

        # Set app icon
        try:
            self.icon = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "icon.png"
            )
        except Exception as e:
            print(f"Could not load icon: {e}")

        # Dark status bar on Android
        if IS_ANDROID:
            try:
                from android import activity
                activity.window.setStatusBarColor(0xFF0D1117)
                print("Status bar color set")
            except Exception as e:
                print(f"Could not set status bar: {e}")

        return YTDownloaderLayout()


if __name__ == "__main__":
    try:
        print("Initializing app...")
        YTDownloaderApp().run()
    except Exception as e:
        print(f"Fatal error: {e}")
        traceback.print_exc()