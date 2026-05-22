import tkinter as tk
from tkinter import ttk, scrolledtext, simpledialog, messagebox
import threading
import time
import random
import json
import os
import pyautogui
import keyboard
import base64
try:
    from pynput import mouse as _pynput_mouse
    _PYNPUT_OK = True
except ImportError:
    _PYNPUT_OK = False
from io import BytesIO

import sys as _sys
if getattr(_sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(_sys.executable)
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "paste_config.json")

MAX_HISTORY = 50

EASY_WORDS = {
    "a","an","the","and","or","but","is","it","in","on","at","to","of","for",
    "as","by","do","go","he","me","my","no","so","up","we","be","if","ok","hi",
    "i","im","us","was","are","has","had","did","not","can","its","all","you",
    "get","got","let","now","new","out","his","her","our","day","one","two",
    "see","way","may","say","use","own","old","big","try","put","run","set",
    "few","how","why","who","yes","yet","age","ago","add",
}

NEIGHBORS = {
    'a':'sqwz','b':'vghn','c':'xdfv','d':'serfcx','e':'wrsdf',
    'f':'drtgvc','g':'ftyhbv','h':'gyujnb','i':'uojkl','j':'huikmn',
    'k':'jiolm','l':'kop','m':'njk','n':'bhjm','o':'iklp',
    'p':'ol','q':'wa','r':'edft','s':'awedxz','t':'rfgy',
    'u':'yhij','v':'cfgb','w':'qase','x':'zsdc','y':'tghu','z':'asx',
}

BG      = "#0a0a0a"
BG2     = "#111111"
BG3     = "#181818"
SIDEBAR = "#0d0d0d"
BORDER  = "#1f1f1f"
GREEN   = "#00ff88"
GREEN2  = "#00cc66"
GREEN_BRIGHT = "#55ffaa"
RED     = "#ff3333"
YELLOW  = "#ffaa00"
DIM     = "#444444"
DIM2    = "#2a2a2a"
TEXT    = "#cccccc"
ACCENT  = "#00ff88"
STAR    = "#ffaa00"
MATRIX  = "#003300"

VERSION = 20

DEFAULT_SETTINGS = {
    "speed": 50, "intensity": 25, "fix_delay": 0.4,
    "start_key": "F6", "stop_key": "F7",
    "typo_neighbor": True, "typo_skip": True, "typo_double": True,
    "typo_space": True, "typo_transpose": True,
    "hide_key": "F8",
    "finish_sound": "ding",
}

# config
def _default_config():
    return {
        "settings":        dict(DEFAULT_SETTINGS),
        "current_profile": None,
        "profiles":        {},
        "history":         [],
        "saves":           [],
    }

def load_config():
    cfg = _default_config()
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "settings" in data:
                cfg["settings"].update(data["settings"])
            cfg["current_profile"] = data.get("current_profile", None)
            cfg["profiles"]        = data.get("profiles", {})
            cfg["history"]         = data.get("history", [])
            cfg["saves"]           = data.get("saves", [])
    except Exception:
        pass
    return cfg

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def load_history(cfg):
    return list(cfg.get("history", []))

def save_history(cfg, entries):
    cfg["history"] = entries[:MAX_HISTORY]
    save_config(cfg)

def get_typo_neighbor(char):
    c = char.lower()
    return random.choice(NEIGHBORS[c]) if c in NEIGHBORS else char


class GreenSlider(tk.Canvas):
    """A clean circle-on-line slider in green."""
    def __init__(self, parent, from_=0, to=100, default=50, step=1,
                 is_float=False, width=260, on_change=None, **kwargs):
        super().__init__(parent, bg=BG2, highlightthickness=0,
                         width=width, height=24, **kwargs)
        self.from_     = from_
        self.to        = to
        self.step      = step
        self.is_float  = is_float
        self.on_change = on_change
        self._width    = width
        self._value    = float(default)
        self._padding  = 10

        self.bind("<Configure>",       self._redraw)
        self.bind("<Button-1>",        self._click)
        self.bind("<B1-Motion>",       self._drag)
        self.bind("<ButtonRelease-1>", self._release)

        self._draw()

    def _x_for_value(self, val):
        ratio = (val - self.from_) / (self.to - self.from_)
        return self._padding + ratio * (self._width - 2 * self._padding)

    def _value_for_x(self, x):
        ratio = (x - self._padding) / (self._width - 2 * self._padding)
        ratio = max(0.0, min(1.0, ratio))
        raw = self.from_ + ratio * (self.to - self.from_)
        # snap to step
        snapped = round(raw / self.step) * self.step
        snapped = max(self.from_, min(self.to, snapped))
        if self.is_float:
            return round(snapped, 3)
        return int(snapped)

    def _draw(self):
        self.delete("all")
        w = self._width
        cy = 12

        # track line dim
        self.create_line(self._padding, cy, w - self._padding, cy,
                         fill="#2a2a2a", width=2)

        # filled portion (green)
        cx = self._x_for_value(self._value)
        self.create_line(self._padding, cy, cx, cy,
                         fill=GREEN2, width=2)

        # circle handle
        r = 7
        self.create_oval(cx - r, cy - r, cx + r, cy + r,
                         fill=GREEN, outline=GREEN, tags="handle")
        # inner dark dot
        self.create_oval(cx - 3, cy - 3, cx + 3, cy + 3,
                         fill=BG, outline="", tags="handle_inner")

    def _redraw(self, e=None):
        self._width = self.winfo_width() or self._width
        self._draw()

    def _click(self, e):
        self._value = self._value_for_x(e.x)
        self._draw()
        if self.on_change:
            self.on_change()

    def _drag(self, e):
        self._value = self._value_for_x(e.x)
        self._draw()
        if self.on_change:
            self.on_change()

    def _release(self, e):
        if self.on_change:
            self.on_change()

    def get(self):
        return self._value

    def set(self, v):
        self._value = float(v)
        self._draw()


class LabeledSlider(tk.Frame):
    def __init__(self, parent, label, from_, to, default, step=1,
                 is_float=False, width=240, on_change=None, **kwargs):
        super().__init__(parent, bg=BG2, **kwargs)
        self.is_float  = is_float
        self.on_change = on_change
        self.var = tk.DoubleVar(value=default) if is_float else tk.IntVar(value=default)

        if label:
            tk.Label(self, text=label, font=("Courier New", 8), fg=DIM, bg=BG2,
                     width=16, anchor="w").pack(side="left")

        self.slider = GreenSlider(
            self, from_=from_, to=to, default=default, step=step,
            is_float=is_float, width=width,
            on_change=self._slider_changed
        )
        self.slider.pack(side="left", padx=(4, 6))

        vcmd = (parent.register(self._validate), '%P')
        self.entry = tk.Entry(
            self, textvariable=self.var, width=6,
            font=("Courier New", 9), bg=BG3, fg=GREEN,
            insertbackground=GREEN, relief="flat",
            highlightbackground=BORDER, highlightthickness=1,
            validate="key", validatecommand=vcmd
        )
        self.entry.pack(side="left")
        self.entry.bind("<FocusOut>", self._entry_changed)
        self.entry.bind("<Return>",   self._entry_changed)

    def _slider_changed(self):
        val = self.slider.get()
        if self.is_float:
            self.var.set(round(val, 2))
        else:
            self.var.set(int(val))
        if self.on_change:
            self.on_change()

    def _entry_changed(self, *_):
        try:
            val = float(self.var.get())
            self.slider.set(val)
        except Exception:
            pass
        if self.on_change:
            self.on_change()

    def _validate(self, val):
        if val in ("", "-"):
            return True
        try:
            float(val); return True
        except ValueError:
            return False

    def get(self):
        return self.slider.get()

    def set(self, v):
        self.slider.set(v)
        if self.is_float:
            self.var.set(round(float(v), 2))
        else:
            self.var.set(int(v))


# main app
class PasteTyperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PasteTyper v20")
        self.root.configure(bg=BG)
        self.root.geometry("860x720")
        self.root.resizable(True, True)
        self.root.minsize(700, 560)
        self.root.attributes("-topmost", True)
        # remove title bar but keep taskbar via hidden parent
        self.root.overrideredirect(True)

        # set icon on this toplevel
        _icon_path = os.path.join(SCRIPT_DIR, "logo.png")
        if os.path.exists(_icon_path):
            try:
                from PIL import Image, ImageTk
                _img = Image.open(_icon_path).resize((64, 64), Image.LANCZOS)
                self._taskbar_icon = ImageTk.PhotoImage(_img)
                self.root.iconphoto(True, self._taskbar_icon)
            except Exception:
                pass
        _ico_path = os.path.join(SCRIPT_DIR, "icon.ico")
        if not os.path.exists(_ico_path):
            _ico_path = os.path.join(SCRIPT_DIR, "logo.ico")
        if os.path.exists(_ico_path):
            try:
                self.root.iconbitmap(_ico_path)
            except Exception:
                pass

        # drag support for frameless window
        self._drag_x = 0
        self._drag_y = 0

        self.stop_flag  = False
        self.is_running = False

        self._full_text    = ""
        self._resume_index = 0
        self._can_resume   = False
        self._word_spans   = []
        self._current_word = -1

        self._cfg = load_config()
        s = self._cfg["settings"]

        self.start_key = tk.StringVar(value=s["start_key"])
        self.stop_key  = tk.StringVar(value=s["stop_key"])
        self.hide_key  = tk.StringVar(value=s.get("hide_key", "F8"))
        self._registered_start = None
        self._registered_stop  = None
        self._registered_hide  = None
        self._mouse_start_ids  = []
        self._mouse_stop_ids   = []
        self._mouse_hide_ids   = []
        self._binding_active   = False
        self._mouse_bind_ids   = []
        self._is_hidden = False
        self._pynput_listener  = None

        self.finish_sound = tk.StringVar(value=s.get("finish_sound", "ding"))

        self.typo_neighbor  = tk.BooleanVar(value=s["typo_neighbor"])
        self.typo_skip      = tk.BooleanVar(value=s["typo_skip"])
        self.typo_double    = tk.BooleanVar(value=s["typo_double"])
        self.typo_space     = tk.BooleanVar(value=s["typo_space"])
        self.typo_transpose = tk.BooleanVar(value=s["typo_transpose"])

        for var in (self.typo_neighbor, self.typo_skip, self.typo_double,
                    self.typo_space, self.typo_transpose):
            var.trace_add("write", lambda *_: self._autosave())

        self._history = load_history(self._cfg)
        self._saves   = list(self._cfg.get("saves", []))

        self._active_tab = 0
        self._title_anim_step = 0
        self._title_anim_phase = "typing"
        self._title_target = 1

        # slide animation state
        self._slide_anim_id = None


        self._build_ui()

        self.speed_slider.set(s["speed"])
        self.intensity_slider.set(s["intensity"])
        self.fix_delay_slider.set(s["fix_delay"])

        self._register_hotkeys()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.root.after(800, self._animate_title)

    # config helpers
    def _collect_settings(self):
        return {
            "speed":          self.speed_slider.get(),
            "intensity":      self.intensity_slider.get(),
            "fix_delay":      self.fix_delay_slider.get(),
            "start_key":      self.start_key.get(),
            "stop_key":       self.stop_key.get(),
            "hide_key":       self.hide_key.get(),
            "typo_neighbor":  self.typo_neighbor.get(),
            "typo_skip":      self.typo_skip.get(),
            "typo_double":    self.typo_double.get(),
            "typo_space":     self.typo_space.get(),
            "typo_transpose": self.typo_transpose.get(),
            "finish_sound":   self.finish_sound.get(),
        }

    def _autosave(self, *_):
        self._cfg["settings"] = self._collect_settings()
        self._cfg["history"]  = self._history
        self._cfg["saves"]    = self._saves
        save_config(self._cfg)

    def _on_close(self):
        self._autosave()
        if hasattr(self, '_pynput_listener') and self._pynput_listener:
            try: self._pynput_listener.stop()
            except Exception: pass
        self.root.destroy()

    # title animation
    def _animate_title(self):
        """Type each char of vX.0... at 250ms, delete at 250ms.
           At vVERSION: hand off to rainbow canvas loop."""
        if not hasattr(self, 'title_lbl'):
            return

        CHAR_MS    = 250
        is_final   = (self._title_target >= VERSION)
        target_text = f"v{self._title_target}.0..."
        fg_color    = GREEN2  # plain green while typing; rainbow takes over at v20

        if self._title_anim_phase == "typing":
            step = self._title_anim_step
            if step <= len(target_text):
                self.title_lbl.config(text=target_text[:step] + "|", fg=fg_color)
                self._title_anim_step += 1
                self.root.after(CHAR_MS, self._animate_title)
            else:
                # fully typed for v20 hand off immediately to rainbow loop
                if is_final:
                    self.title_lbl.config(text=target_text, fg=GREEN2)
                    # short pause so the last typed char is visible, then rainbow
                    self.root.after(120, self._blink_cursor_loop)
                else:
                    self.title_lbl.config(text=target_text + "|", fg=fg_color)
                    self._title_anim_phase = "deleting"
                    self._title_anim_step  = len(target_text)
                    self.root.after(CHAR_MS, self._animate_title)

        elif self._title_anim_phase == "deleting":
            step = self._title_anim_step
            if step > 0:
                remaining = target_text[:step - 1]
                self.title_lbl.config(text=remaining + "|", fg=fg_color)
                self._title_anim_step -= 1
                self.root.after(CHAR_MS, self._animate_title)
            else:
                self.title_lbl.config(text="")
                self._title_target    += 1
                self._title_anim_step  = 0
                self._title_anim_phase = "typing"
                self.root.after(200, self._animate_title)

    def _blink_cursor_loop(self):
        """Flowing left-to-right rainbow wave on vVERSION.0... — 45s then disappears."""
        if not hasattr(self, 'title_lbl'):
            return
        import math, colorsys

        TARGET_TEXT = f"v{VERSION}.0..."
        HOLD_MS     = 45_000    # 45 seconds
        FRAME_MS    = 40        # ~25 fps
        FADE_FRAMES = 18        # frames to ramp from dimfull (≈0.72s)

        # bootstrap state on first call
        if not hasattr(self, '_rbw_offset'):
            self._rbw_offset     = 0.0
            self._rbw_start_ms   = int(time.time() * 1000)
            self._rbw_cursor_on  = True
            self._rbw_last_blink = int(time.time() * 1000)
            self._rbw_frame      = 0   # counts up for fade-in ramp

        now_ms   = int(time.time() * 1000)
        elapsed  = now_ms - self._rbw_start_ms

        if elapsed >= HOLD_MS:
            # 45 s expired clear canvas and restart the v1v20 cycle
            self.title_lbl.config(text="")
            if hasattr(self, '_rbw_canvas'):
                try: self._rbw_canvas.destroy()
                except Exception: pass
                del self._rbw_canvas
            # clean up state attrs
            for attr in ('_rbw_offset', '_rbw_start_ms', '_rbw_cursor_on',
                         '_rbw_last_blink', '_rbw_frame'):
                try: delattr(self, attr)
                except Exception: pass
            # restart from v1
            self._title_target     = 1
            self._title_anim_step  = 0
            self._title_anim_phase = "typing"
            self.root.after(400, self._animate_title)
            return

        # advance wave offset controls scroll speed
        self._rbw_offset = (self._rbw_offset + 0.055) % (2 * math.pi)
        self._rbw_frame  = min(self._rbw_frame + 1, FADE_FRAMES)

        # fade-in multiplier: 0.15 1.0 over fade_frames frames (smooth ease)
        t = self._rbw_frame / FADE_FRAMES
        brightness = 0.15 + 0.85 * (t * t * (3 - 2 * t))  # smoothstep

        # toggle blinking cursor every 500 ms (but only after fade-in)
        if self._rbw_frame >= FADE_FRAMES:
            if now_ms - self._rbw_last_blink >= 500:
                self._rbw_cursor_on  = not self._rbw_cursor_on
                self._rbw_last_blink = now_ms
        else:
            self._rbw_cursor_on = True  # keep cursor solid during fade

        display = TARGET_TEXT + ("|" if self._rbw_cursor_on else " ")

        # build per-character coloured text using a tk.canvas
        if not hasattr(self, '_rbw_canvas'):
            self.title_lbl.config(text="")
            parent = self.title_lbl.master
            CW = len(display) * 11 + 6
            self._rbw_canvas = tk.Canvas(parent, bg=BG,
                                         highlightthickness=0,
                                         width=CW, height=28)
            self._rbw_canvas.pack(side="left", pady=8)

        canvas = self._rbw_canvas
        canvas.delete("all")
        cx = len(display) * 11 + 6
        if canvas.winfo_width() != cx:
            canvas.config(width=cx)
        cy = canvas.winfo_height() // 2 or 14
        CHAR_W = 11
        FONT   = ("Courier New", 9)

        for idx, ch in enumerate(display):
            hue = (idx / max(len(display) - 1, 1) + self._rbw_offset / (2 * math.pi)) % 1.0
            r, g, b = colorsys.hsv_to_rgb(hue, 1.0, brightness)
            color = "#{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(b*255))
            x = 3 + idx * CHAR_W + CHAR_W // 2
            canvas.create_text(x, cy, text=ch, font=FONT,
                               fill=color, anchor="center")

        self.root.after(FRAME_MS, self._blink_cursor_loop)

    # history
    def _push_history(self, text):
        import datetime
        entry = {"ts": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "text": text}
        self._history = [h for h in self._history if h["text"] != text]
        self._history.insert(0, entry)
        self._history = self._history[:MAX_HISTORY]
        save_history(self._cfg, self._history)
        self._refresh_history_list()

    # ui build
    def _build_ui(self):
        # thin green line at very top
        tk.Frame(self.root, bg=GREEN2, height=2).pack(fill="x")

        # top bar (custom, no os title bar)
        top = tk.Frame(self.root, bg=BG, height=58)
        top.pack(fill="x", padx=0, pady=0)
        top.pack_propagate(False)

        # drag bindings on top bar
        top.bind("<Button-1>",   self._start_drag)
        top.bind("<B1-Motion>",  self._do_drag)

        # logo image (top-left)
        logo_path = os.path.join(SCRIPT_DIR, "logo.png")
        self._logo_img = None
        if os.path.exists(logo_path):
            try:
                from PIL import Image, ImageTk
                img = Image.open(logo_path).resize((66, 66), Image.LANCZOS)
                self._logo_img = ImageTk.PhotoImage(img)
                logo_lbl = tk.Label(top, image=self._logo_img, bg=BG, cursor="")
                logo_lbl.pack(side="left", padx=(10, 6), pady=6)
                logo_lbl.bind("<Button-1>",  self._start_drag)
                logo_lbl.bind("<B1-Motion>", self._do_drag)
            except Exception:
                pass

        tk.Label(top, text="[ PASTE_TYPER ]", font=("Courier New", 14, "bold"),
                 fg=GREEN, bg=BG).pack(side="left", padx=(4, 6), pady=8)

        self.title_lbl = tk.Label(top, text="", font=("Courier New", 9),
                                   fg=GREEN2, bg=BG)
        self.title_lbl.pack(side="left", pady=8)

        # arrow close button (top right)
        close_arrow = tk.Label(top, text="➡", font=("Segoe UI Emoji", 16),
                               fg=DIM, bg=BG, cursor="hand2")
        close_arrow.pack(side="right", padx=(0, 12), pady=8)
        close_arrow.bind("<Button-1>", lambda e: self._force_close())
        close_arrow.bind("<Enter>", lambda e: close_arrow.config(fg=RED))
        close_arrow.bind("<Leave>", lambda e: close_arrow.config(fg=DIM))

        # status pill (right side)
        self.status_pill = tk.Label(top, text="● STOPPED",
                                     font=("Courier New", 8, "bold"), fg=RED, bg=BG)
        self.status_pill.pack(side="right", padx=(0, 8))

        self.countdown_label = tk.Label(top, text="", font=("Courier New", 9), fg=GREEN, bg=BG)
        self.countdown_label.pack(side="right", padx=(0, 8))

        # separator
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")

        # main body: sidebar + content
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True)

        # sidebar
        self.sidebar = tk.Frame(body, bg=SIDEBAR, width=92)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # thin border line between sidebar and content
        tk.Frame(body, bg=BORDER, width=1).pack(side="left", fill="y")

        # content area wrapper (for slide animation)
        self._content_wrapper = tk.Frame(body, bg=BG2)
        self._content_wrapper.pack(side="left", fill="both", expand=True)

        # content area this is what we'll slide
        self.content_area = tk.Frame(self._content_wrapper, bg=BG2)
        self.content_area.place(x=0, y=0, relwidth=1, relheight=1)

        # build tab pages (hidden until selected)
        self.pages = {}
        self._build_all_pages()

        # build sidebar buttons
        self._build_sidebar()

        # show first tab
        self._active_tab = 0
        self._show_page_direct(0)

        # bottom bar
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")

        bot = tk.Frame(self.root, bg=BG, height=52)
        bot.pack(fill="x")
        bot.pack_propagate(False)

        fb = ("Courier New", 10, "bold")

        self.run_btn = tk.Button(
            bot, text="▶  RUN", font=fb, bg=GREEN, fg=BG,
            activebackground=GREEN2, activeforeground=BG,
            relief="flat", cursor="hand2", width=11, pady=6,
            command=self._start_sequence)
        self.run_btn.pack(side="left", padx=(12, 0), pady=8)

        self.resume_btn = tk.Button(
            bot, text="⟳  RESUME", font=fb, bg=BG3, fg=DIM,
            activebackground=BORDER, activeforeground=YELLOW,
            relief="flat", cursor="hand2", width=11, pady=6,
            state="disabled", command=self._resume_sequence)
        self.resume_btn.pack(side="left", padx=(6, 0), pady=8)

        self.stop_btn = tk.Button(
            bot, text="■  STOP", font=fb, bg=BG3, fg=DIM,
            activebackground=BORDER, activeforeground=RED,
            relief="flat", cursor="hand2", width=11, pady=6,
            state="disabled", command=self._stop_typing)
        self.stop_btn.pack(side="left", padx=(6, 0), pady=8)



        self.word_pill = tk.Label(bot, text="", font=("Courier New", 8), fg=DIM, bg=BG)
        self.word_pill.pack(side="right", padx=(0, 12))

        # status bar
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")
        status_bar = tk.Frame(self.root, bg=BG, height=22)
        status_bar.pack(fill="x")
        status_bar.pack_propagate(False)

        self.status_var = tk.StringVar(value="ready.")
        tk.Label(status_bar, textvariable=self.status_var,
                 font=("Courier New", 8), fg=DIM, bg=BG, anchor="w"
                 ).pack(fill="x", padx=14, pady=3)

        # floating close arrow at very bottom-left of screen
        self.root.after(150, self._place_close_btn)

    def _force_close(self):
        """Force close the app and kill the script process."""
        try:
            self._autosave()
        except Exception:
            pass
        os._exit(0)

    def _place_close_btn(self):
        """Floating ➡ arrow pinned to the very bottom-left corner of the screen."""
        screen_h = self.root.winfo_screenheight()

        self._close_win = tk.Toplevel(self.root)
        self._close_win.overrideredirect(True)
        self._close_win.attributes("-topmost", True)
        self._close_win.configure(bg=BG)

        # apply icon if available
        ico_path = os.path.join(SCRIPT_DIR, "icon.ico")
        if os.path.exists(ico_path):
            try:
                self._close_win.iconbitmap(ico_path)
            except Exception:
                pass

        arrow = tk.Label(
            self._close_win,
            text="➡",
            font=("Segoe UI Emoji", 13),
            fg="#2a2a2a",
            bg=BG,
            cursor="hand2",
            padx=4, pady=2,
        )
        arrow.pack()
        arrow.bind("<Button-1>", lambda e: self._force_close())
        arrow.bind("<Enter>",    lambda e: arrow.config(fg=RED))
        arrow.bind("<Leave>",    lambda e: arrow.config(fg="#2a2a2a"))

        self._close_win.update_idletasks()
        btn_h = self._close_win.winfo_reqheight()
        # sit right at the very bottom of the screen, left edge
        self._close_win.geometry(f"+2+{screen_h - btn_h - 2}")

    # drag for frameless window
    def _start_drag(self, e):
        self._drag_x = e.x_root - self.root.winfo_x()
        self._drag_y = e.y_root - self.root.winfo_y()

    def _do_drag(self, e):
        x = e.x_root - self._drag_x
        y = e.y_root - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    # sidebar
    def _build_sidebar(self):
        tabs = [
            ("☁",  "TYPER",    0),
            ("⌨",  "CONFIG",   1),
            ("👤", "PROFILES", 2),
            ("💾", "SAVES",    3),
            ("🔀", "COMPARE",  4),
        ]

        self._sidebar_btns = []
        self._sidebar_indicator_y = None      # current y of green pill
        self._sidebar_indicator_target_y = None
        self._sidebar_indicator_anim_id = None

        # canvas for the sidebar (enables absolute positioning of indicator)
        self._sidebar_canvas = tk.Canvas(
            self.sidebar, bg=SIDEBAR, highlightthickness=0,
            width=92
        )
        self._sidebar_canvas.pack(fill="both", expand=True)

        # spacer at top
        top_pad = 28
        tab_height = 80   # each tab slot height in pixels
        self._tab_y_centers = []

        for idx, (icon, name, _) in enumerate(tabs):
            y_center = top_pad + idx * (tab_height + 8) + tab_height // 2

            # frame sits inside the canvas via a window item
            frame = tk.Frame(self._sidebar_canvas, bg=SIDEBAR, cursor="hand2", width=80)
            frame_y = top_pad + idx * (tab_height + 8)
            self._sidebar_canvas.create_window(
                46, frame_y + tab_height // 2,
                window=frame, anchor="center", width=80, height=tab_height
            )
            self._tab_y_centers.append(frame_y + tab_height // 2)

            icon_lbl = tk.Label(
                frame, text=icon,
                font=("Segoe UI Emoji", 28),
                fg=DIM, bg=SIDEBAR,
                cursor="hand2"
            )
            icon_lbl.pack(pady=(6, 2))

            name_lbl = tk.Label(
                frame, text=name,
                font=("Courier New", 6, "bold"),
                fg=DIM, bg=SIDEBAR,
                cursor="hand2"
            )
            name_lbl.pack(pady=(0, 6))

            for w in (frame, icon_lbl, name_lbl):
                w.bind("<Button-1>", lambda e, i=idx: self._switch_tab(i))
                w.bind("<Enter>",    lambda e, f=frame, il=icon_lbl, nl=name_lbl: self._sidebar_hover(f, il, nl, True))
                w.bind("<Leave>",    lambda e, f=frame, il=icon_lbl, nl=name_lbl, i=idx: self._sidebar_hover(f, il, nl, False, i))

            self._sidebar_btns.append((frame, icon_lbl, name_lbl))

        # draw green left-edge pill indicator (drawn last so on top)
        self._indicator_rect = self._sidebar_canvas.create_rectangle(
            0, 0, 3, 1, fill=GREEN, outline="", tags="indicator"
        )
        # position it at first tab after layout
        self.sidebar.after(50, lambda: self._sidebar_snap_indicator(0))

        # separator
        # (not packed canvas fills sidebar)

    def _sidebar_hover(self, frame, icon_lbl, name_lbl, entering, tab_idx=None):
        if entering:
            frame.config(bg="#1a1a1a")
            icon_lbl.config(bg="#1a1a1a", fg=GREEN)
            name_lbl.config(bg="#1a1a1a", fg=GREEN)
        else:
            active = (tab_idx == self._active_tab)
            bg_col  = BG3 if active else SIDEBAR
            fg_col  = GREEN if active else DIM
            frame.config(bg=bg_col)
            icon_lbl.config(bg=bg_col, fg=fg_col)
            name_lbl.config(bg=bg_col, fg=fg_col)

    def _sidebar_snap_indicator(self, idx):
        """Snap indicator to tab idx immediately."""
        if idx < len(self._tab_y_centers):
            y = self._tab_y_centers[idx]
            self._sidebar_indicator_y = float(y)
            self._sidebar_indicator_target_y = float(y)
            self._draw_sidebar_indicator(y)

    def _sidebar_slide_indicator(self, to_idx):
        """Animate indicator sliding to to_idx."""
        if to_idx >= len(self._tab_y_centers):
            return
        target = float(self._tab_y_centers[to_idx])
        self._sidebar_indicator_target_y = target
        if self._sidebar_indicator_y is None:
            self._sidebar_indicator_y = target
        if self._sidebar_indicator_anim_id:
            self.sidebar.after_cancel(self._sidebar_indicator_anim_id)
        self._animate_indicator()

    def _animate_indicator(self):
        if self._sidebar_indicator_y is None or self._sidebar_indicator_target_y is None:
            return
        cur = self._sidebar_indicator_y
        tgt = self._sidebar_indicator_target_y
        diff = tgt - cur
        if abs(diff) < 1.5:
            self._sidebar_indicator_y = tgt
            self._draw_sidebar_indicator(tgt)
            return
        # ease: move 30% of remaining distance each frame
        self._sidebar_indicator_y = cur + diff * 0.35
        self._draw_sidebar_indicator(self._sidebar_indicator_y)
        self._sidebar_indicator_anim_id = self.sidebar.after(
            14, self._animate_indicator)

    def _draw_sidebar_indicator(self, y):
        """Draw a green left-edge pill at y position."""
        h = 36
        self._sidebar_canvas.coords(
            self._indicator_rect,
            0, y - h // 2, 3, y + h // 2
        )
        self._sidebar_canvas.tag_raise("indicator")

    def _show_page_direct(self, idx):
        """Show a page without animation."""
        for page in self.pages.values():
            page.place_forget()
        self.pages[idx].place(x=0, y=0, relwidth=1, relheight=1)

    def _switch_tab(self, idx):
        if idx == self._active_tab:
            return
        if self._slide_anim_id:
            self.root.after_cancel(self._slide_anim_id)
            self._slide_anim_id = None

        prev_idx = self._active_tab
        self._active_tab = idx

        # update sidebar highlight immediately
        for i, (frame, icon_lbl, name_lbl) in enumerate(self._sidebar_btns):
            if i == idx:
                frame.config(bg=BG3)
                icon_lbl.config(bg=BG3, fg=GREEN)
                name_lbl.config(bg=BG3, fg=GREEN)
            else:
                frame.config(bg=SIDEBAR)
                icon_lbl.config(bg=SIDEBAR, fg=DIM)
                name_lbl.config(bg=SIDEBAR, fg=DIM)

        # slide sidebar indicator
        self._sidebar_slide_indicator(idx)

        # slide animation
        self._slide_animate(prev_idx, idx)

    def _slide_animate(self, from_idx, to_idx):
        """Smooth slide: new page slides in from right/left."""
        wrapper_w = self._content_wrapper.winfo_width()
        if wrapper_w <= 1:
            wrapper_w = 760

        direction = 1 if to_idx > from_idx else -1

        old_page = self.pages[from_idx]
        new_page = self.pages[to_idx]

        # position new page off-screen
        start_x = direction * wrapper_w
        new_page.place(x=start_x, y=0, relwidth=1, relheight=1)
        old_page.place(x=0, y=0, relwidth=1, relheight=1)
        old_page.lift()
        new_page.lift()

        steps = 8
        step_size = wrapper_w // steps

        def step(current_x):
            if self._active_tab != to_idx:
                return
            new_x = current_x - direction * step_size
            # clamp to 0
            if direction == 1:
                new_x = max(0, new_x)
            else:
                new_x = min(0, new_x)

            old_x = new_x - direction * wrapper_w

            new_page.place(x=new_x, y=0, relwidth=1, relheight=1)
            old_page.place(x=old_x, y=0, relwidth=1, relheight=1)

            done = (new_x == 0)
            if not done:
                self._slide_anim_id = self.root.after(14, lambda: step(new_x))
            else:
                old_page.place_forget()
                self._slide_anim_id = None

        self._slide_anim_id = self.root.after(14, lambda: step(start_x))

    # build all pages
    def _build_all_pages(self):
        for i in range(5):
            page = tk.Frame(self.content_area, bg=BG2)
            self.pages[i] = page

        self._build_typer_page()
        self._build_config_page()
        self._build_profiles_page()
        self._build_saves_page()
        self._build_compare_page()

    # page 0 typer
    def _build_typer_page(self):
        p = self.pages[0]

        hdr = tk.Frame(p, bg=BG2)
        hdr.pack(fill="x", padx=20, pady=(16, 6))
        tk.Label(hdr, text="☁  TYPER", font=("Courier New", 12, "bold"),
                 fg=GREEN, bg=BG2).pack(side="left")
        tk.Label(hdr, text="paste text, set speed, run",
                 font=("Courier New", 8), fg=DIM, bg=BG2).pack(side="left", padx=14)

        tk.Frame(p, bg=BORDER, height=1).pack(fill="x", padx=20, pady=(0, 10))

        txt_wrap = tk.Frame(p, bg="#0d0d0d",
                            highlightbackground=GREEN2, highlightthickness=1)
        txt_wrap.pack(padx=20, pady=(0, 4), fill="both", expand=True)

        self.text_box = tk.Text(
            txt_wrap, font=("Courier New", 10),
            bg="#0d0d0d", fg=TEXT, insertbackground=GREEN,
            selectbackground="#003322", relief="flat", wrap="word",
            padx=12, pady=10, bd=0, undo=True
        )
        self.text_box.pack(fill="both", expand=True)

        self.text_box.tag_configure(
            "current_word",
            background="#003322", foreground=GREEN,
            font=("Courier New", 10, "bold"))
        self.text_box.tag_configure("done_word", foreground="#1a5c3a")
        self.text_box.bind("<Button-3>", self._right_click_resume)
        self.text_box.bind("<KeyRelease>", self._on_key)

        hint_row = tk.Frame(p, bg=BG2)
        hint_row.pack(fill="x", padx=20, pady=(3, 0))
        tk.Label(hint_row, text="right-click → set resume point",
                 font=("Courier New", 7), fg=DIM, bg=BG2).pack(side="left")
        self.char_label = tk.Label(hint_row, text="0 chars,  0 words",
                                    font=("Courier New", 8), fg=DIM, bg=BG2)
        self.char_label.pack(side="right")

        tk.Frame(p, bg=BORDER, height=1).pack(fill="x", padx=20, pady=(10, 8))

        # speed slider row clean
        spd_row = tk.Frame(p, bg=BG2)
        spd_row.pack(fill="x", padx=20, pady=(0, 4))
        tk.Label(spd_row, text="TYPING SPEED", font=("Courier New", 8, "bold"),
                 fg=GREEN, bg=BG2, width=16, anchor="w").pack(side="left")
        self.speed_slider = LabeledSlider(
            spd_row, "", from_=1, to=100, default=50, step=1, width=280,
            on_change=self._autosave)
        self.speed_slider.pack(side="left")

        tk.Frame(p, bg=BORDER, height=1).pack(fill="x", padx=20, pady=(8, 6))
        stat_row = tk.Frame(p, bg=BG2)
        stat_row.pack(fill="x", padx=20, pady=(0, 10))
        tk.Label(stat_row, text="STATUS", font=("Courier New", 8, "bold"),
                 fg=DIM, bg=BG2).pack(side="left")
        self.status_var = tk.StringVar(value="ready.")
        self._inline_status = tk.Label(stat_row, textvariable=self.status_var,
                                        font=("Courier New", 8), fg=GREEN2, bg=BG2)
        self._inline_status.pack(side="left", padx=12)

    # page 1 config
    def _build_config_page(self):
        p = self.pages[1]

        hdr = tk.Frame(p, bg=BG2)
        hdr.pack(fill="x", padx=20, pady=(16, 6))
        tk.Label(hdr, text="⌨  CONFIG", font=("Courier New", 12, "bold"),
                 fg=GREEN, bg=BG2).pack(side="left")
        tk.Label(hdr, text="typo settings & keybinds",
                 font=("Courier New", 8), fg=DIM, bg=BG2).pack(side="left", padx=14)
        tk.Frame(p, bg=BORDER, height=1).pack(fill="x", padx=20, pady=(0, 6))

        # scrollable via mouse drag
        canvas = tk.Canvas(p, bg=BG2, highlightthickness=0)
        canvas.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(canvas, bg=BG2)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_resize(e):
            canvas.itemconfig(win_id, width=e.width)
        canvas.bind("<Configure>", _on_resize)
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # mouse drag to scroll (no scrollbar)
        self._scroll_drag_y = [0]
        def _scroll_start(e):
            self._scroll_drag_y[0] = e.y_root
        def _scroll_move(e):
            dy = self._scroll_drag_y[0] - e.y_root
            self._scroll_drag_y[0] = e.y_root
            canvas.yview_scroll(int(dy / 3), "units")

        canvas.bind("<Button-1>",  _scroll_start)
        canvas.bind("<B1-Motion>", _scroll_move)
        inner.bind("<Button-1>",   _scroll_start)
        inner.bind("<B1-Motion>",  _scroll_move)

        # mouse wheel bind to canvas and propagate to all children
        def _wheel(e):
            canvas.yview_scroll(-1*(e.delta//120), "units")
            return "break"

        canvas.bind("<MouseWheel>", _wheel)

        # store canvas so we can bind children after they're created
        self._config_canvas = canvas
        self._config_scroll_fn = _wheel

        fs = ("Courier New", 8)

        tk.Frame(inner, bg=BORDER, height=1).pack(fill="x", padx=14, pady=(8, 8))
        tk.Label(inner, text="INTENSITY", font=("Courier New", 9, "bold"),
                 fg=GREEN, bg=BG2).pack(anchor="w", padx=14)
        tk.Label(inner, text="how often typos happen",
                 font=fs, fg=DIM, bg=BG2).pack(anchor="w", padx=14, pady=(0, 4))
        self.intensity_slider = LabeledSlider(
            inner, "INTENSITY", from_=0, to=100, default=25, step=1, width=260,
            on_change=self._autosave)
        self.intensity_slider.pack(anchor="w", padx=14, pady=(0, 10))

        tk.Frame(inner, bg=BORDER, height=1).pack(fill="x", padx=14, pady=(0, 8))
        tk.Label(inner, text="FIX DELAY", font=("Courier New", 9, "bold"),
                 fg=GREEN, bg=BG2).pack(anchor="w", padx=14)
        tk.Label(inner, text="seconds before backspacing a typo",
                 font=fs, fg=DIM, bg=BG2).pack(anchor="w", padx=14, pady=(0, 4))
        self.fix_delay_slider = LabeledSlider(
            inner, "FIX DELAY (s)", from_=0.05, to=2.0, default=0.4,
            step=0.05, is_float=True, width=240, on_change=self._autosave)
        self.fix_delay_slider.pack(anchor="w", padx=14, pady=(0, 10))

        tk.Frame(inner, bg=BORDER, height=1).pack(fill="x", padx=14, pady=(0, 8))
        tk.Label(inner, text="TYPO TYPES", font=("Courier New", 9, "bold"),
                 fg=GREEN, bg=BG2).pack(anchor="w", padx=14)
        tk.Label(inner, text="which kinds of typos can occur",
                 font=fs, fg=DIM, bg=BG2).pack(anchor="w", padx=14, pady=(0, 8))

        checks = [
            (self.typo_neighbor,  "NEIGHBOR KEY",   "hits a key next to the intended one"),
            (self.typo_skip,      "SKIP LETTER",    "accidentally skips a character"),
            (self.typo_double,    "DOUBLE LETTER",  "types a letter twice"),
            (self.typo_transpose, "TRANSPOSE",      "swaps two adjacent letters"),
            (self.typo_space,     "MISSING SPACE",  "forgets the space between words"),
        ]
        for var, name, desc in checks:
            row = tk.Frame(inner, bg=BG2)
            row.pack(anchor="w", padx=14, pady=3)
            cb = tk.Checkbutton(row, variable=var, text=name,
                                font=("Courier New", 9, "bold"),
                                fg=TEXT, bg=BG2, selectcolor=BG,
                                activebackground=BG2, activeforeground=GREEN,
                                cursor="hand2")
            cb.pack(side="left")
            tk.Label(row, text=f"  — {desc}", font=fs, fg=DIM, bg=BG2).pack(side="left")

        tk.Frame(inner, bg=BORDER, height=1).pack(fill="x", padx=14, pady=(14, 8))
        tk.Label(inner, text="GLOBAL HOTKEYS", font=("Courier New", 9, "bold"),
                 fg=GREEN, bg=BG2).pack(anchor="w", padx=14)
        tk.Label(inner, text="work even when this window is not focused",
                 font=fs, fg=DIM, bg=BG2).pack(anchor="w", padx=14, pady=(0, 10))

        for label, var, is_start, is_hide, hint in [
            ("START / RESUME", self.start_key, True,  False, ""),
            ("STOP",           self.stop_key,  False, False, ""),
            ("HIDE / SHOW",    self.hide_key,  False, True,  "toggle script visible/hidden"),
        ]:
            row = tk.Frame(inner, bg=BG2)
            row.pack(anchor="w", padx=14, pady=8, fill="x")

            tk.Label(row, text=label, font=("Courier New", 9, "bold"),
                     fg=TEXT, bg=BG2, width=16, anchor="w").pack(side="left")

            key_lbl = tk.Label(row, textvariable=var,
                               font=("Courier New", 11, "bold"),
                               fg=GREEN, bg=BG3, width=10,
                               highlightbackground=BORDER, highlightthickness=1,
                               pady=4, relief="flat")
            key_lbl.pack(side="left", padx=(0, 6))

            tk.Button(row, text="BIND", font=fs, bg=BG3, fg=DIM,
                      activebackground=BORDER, activeforeground=GREEN,
                      relief="flat", cursor="hand2", pady=4, padx=8,
                      command=lambda s=is_start, h=is_hide, lbl=key_lbl: self._start_binding(s, lbl, h)
                      ).pack(side="left", padx=(0, 4))

            tk.Button(row, text="✕", font=("Courier New", 9, "bold"),
                      bg=BG3, fg=RED, activebackground=BORDER, activeforeground=RED,
                      relief="flat", cursor="hand2", pady=4, padx=6,
                      command=lambda s=is_start, h=is_hide, lbl=key_lbl: self._clear_keybind(s, lbl, h)
                      ).pack(side="left")

            if hint:
                tk.Label(row, text=f"  {hint}", font=fs, fg=DIM, bg=BG2).pack(side="left", padx=8)

        self.bind_status = tk.Label(inner, text="", font=("Courier New", 9, "bold"),
                                     fg=GREEN, bg=BG2)
        self.bind_status.pack(anchor="w", padx=14, pady=(4, 10))

        # finish sound
        tk.Frame(inner, bg=BORDER, height=1).pack(fill="x", padx=14, pady=(4, 8))
        tk.Label(inner, text="FINISH SOUND", font=("Courier New", 9, "bold"),
                 fg=GREEN, bg=BG2).pack(anchor="w", padx=14)
        tk.Label(inner, text="plays once when typing finishes",
                 font=fs, fg=DIM, bg=BG2).pack(anchor="w", padx=14, pady=(0, 8))

        for val, label in [("ding","Ding 🔔"), ("tada","Tada 🎉"), ("chime","Chime 🎵"), ("ping","Ping 📡"), ("yeah","Yeah 🤙"), ("none","None ✕")]:
            row = tk.Frame(inner, bg=BG2)
            row.pack(anchor="w", padx=14, pady=3)
            tk.Radiobutton(row, text=label, variable=self.finish_sound, value=val,
                           font=("Courier New", 9, "bold"),
                           fg=TEXT, bg=BG2, selectcolor=BG,
                           activebackground=BG2, activeforeground=GREEN,
                           cursor="hand2", command=self._autosave).pack(side="left")
            tk.Button(row, text="TEST ▶", font=fs, bg=BG3, fg=DIM,
                      activebackground=BORDER, activeforeground=GREEN,
                      relief="flat", cursor="hand2", pady=2, padx=6,
                      command=lambda v=val: self._play_finish_sound(v)
                      ).pack(side="left", padx=(10, 0))

        tk.Frame(inner, bg=BORDER, height=1).pack(fill="x", padx=14, pady=(14, 8))



        # bind mousewheel to every child widget inside inner so scrolling
        # works regardless of which child the cursor is over
        def _bind_wheel_recursive(widget):
            widget.bind("<MouseWheel>", self._config_scroll_fn, add="+")
            for child in widget.winfo_children():
                _bind_wheel_recursive(child)

        # schedule after inner is fully populated
        inner.after(100, lambda: _bind_wheel_recursive(inner))

    # page 2 profiles
    def _build_profiles_page(self):
        p = self.pages[2]
        fs = ("Courier New", 8)

        hdr = tk.Frame(p, bg=BG2)
        hdr.pack(fill="x", padx=20, pady=(16, 6))
        tk.Label(hdr, text="👤  PROFILES", font=("Courier New", 12, "bold"),
                 fg=GREEN, bg=BG2).pack(side="left")
        tk.Label(hdr, text="save & load configurations",
                 font=("Courier New", 8), fg=DIM, bg=BG2).pack(side="left", padx=14)
        tk.Frame(p, bg=BORDER, height=1).pack(fill="x", padx=20, pady=(0, 6))

        tk.Label(p, text="★ favorites pinned to top  •  right-click to favorite",
                 font=fs, fg=DIM, bg=BG2).pack(anchor="w", padx=20, pady=(0, 6))

        lf = tk.Frame(p, bg=BG2)
        lf.pack(fill="both", expand=True, padx=20, pady=(0, 6))
        self.prof_listbox = tk.Listbox(
            lf, font=("Courier New", 10), bg="#0d0d0d", fg=TEXT,
            selectbackground="#003322", selectforeground=GREEN,
            activestyle="none", relief="flat", bd=0,
            highlightthickness=1, highlightbackground=BORDER)
        self.prof_listbox.pack(fill="both", expand=True)
        self.prof_listbox.bind("<Double-Button-1>", self._load_profile)
        self.prof_listbox.bind("<Button-3>",         self._toggle_favorite)
        self.prof_listbox.bind("<<ListboxSelect>>",  self._preview_profile)
        self.prof_listbox.bind("<MouseWheel>", lambda e: self.prof_listbox.yview_scroll(-1*(e.delta//120), "units"))

        tk.Label(p, text="PROFILE PREVIEW", font=fs, fg=DIM, bg=BG2
                 ).pack(anchor="w", padx=20)
        pw = tk.Frame(p, bg="#0d0d0d", highlightbackground=BORDER, highlightthickness=1)
        pw.pack(fill="x", padx=20, pady=(2, 8))
        self.prof_preview = tk.Text(
            pw, font=("Courier New", 8), bg="#0d0d0d", fg=GREEN2,
            relief="flat", bd=0, height=4, wrap="word",
            padx=8, pady=6, state="disabled")
        self.prof_preview.pack(fill="x")

        btn_row = tk.Frame(p, bg=BG2)
        btn_row.pack(fill="x", padx=20, pady=(0, 12))
        bs = dict(font=fs, relief="flat", cursor="hand2", pady=6, padx=10)
        tk.Button(btn_row, text="SAVE CURRENT →", bg=GREEN, fg=BG,
                  activebackground=GREEN2, activeforeground=BG,
                  command=self._save_profile, **bs).pack(side="left", padx=(0, 6))
        tk.Button(btn_row, text="LOAD", bg=BG3, fg=DIM,
                  activebackground=BORDER, activeforeground=GREEN,
                  command=self._load_profile, **bs).pack(side="left", padx=(0, 6))
        tk.Button(btn_row, text="RENAME", bg=BG3, fg=DIM,
                  activebackground=BORDER, activeforeground=YELLOW,
                  command=self._rename_profile, **bs).pack(side="left", padx=(0, 6))
        tk.Button(btn_row, text="DELETE", bg=BG3, fg=DIM,
                  activebackground=BORDER, activeforeground=RED,
                  command=self._delete_profile, **bs).pack(side="left")

        self.prof_status = tk.Label(p, text="", font=fs, fg=GREEN, bg=BG2)
        self.prof_status.pack(anchor="w", padx=20)
        self._refresh_profiles_list()

    # page 3 saves & history
    def _build_saves_page(self):
        p = self.pages[3]
        fs = ("Courier New", 8)

        hdr = tk.Frame(p, bg=BG2)
        hdr.pack(fill="x", padx=20, pady=(16, 6))
        tk.Label(hdr, text="💾  SAVES & HISTORY", font=("Courier New", 12, "bold"),
                 fg=GREEN, bg=BG2).pack(side="left")

        sub_bar = tk.Frame(p, bg=BG2)
        sub_bar.pack(fill="x", padx=20, pady=(0, 8))

        self._saves_subpage = tk.IntVar(value=0)

        self._saves_frame   = tk.Frame(p, bg=BG2)
        self._history_frame = tk.Frame(p, bg=BG2)

        def show_saves():
            self._saves_subpage.set(0)
            self._history_frame.pack_forget()
            self._saves_frame.pack(fill="both", expand=True)
            saves_btn.config(fg=GREEN, bg=BG3)
            hist_btn.config(fg=DIM, bg=BG2)

        def show_history():
            self._saves_subpage.set(1)
            self._saves_frame.pack_forget()
            self._history_frame.pack(fill="both", expand=True)
            hist_btn.config(fg=GREEN, bg=BG3)
            saves_btn.config(fg=DIM, bg=BG2)

        saves_btn = tk.Button(sub_bar, text="[ SAVES ]",
                               font=("Courier New", 9, "bold"), fg=GREEN, bg=BG3,
                               activebackground=BORDER, activeforeground=GREEN,
                               relief="flat", cursor="hand2", padx=10, pady=4,
                               command=show_saves)
        saves_btn.pack(side="left")

        hist_btn = tk.Button(sub_bar, text="[ HISTORY ]",
                              font=("Courier New", 9, "bold"), fg=DIM, bg=BG2,
                              activebackground=BORDER, activeforeground=GREEN,
                              relief="flat", cursor="hand2", padx=10, pady=4,
                              command=show_history)
        hist_btn.pack(side="left", padx=(4, 0))

        sf = self._saves_frame

        tk.Label(sf, text="TITLE", font=("Courier New", 8, "bold"),
                 fg=DIM, bg=BG2).pack(anchor="w", padx=20)
        self.save_title_var = tk.StringVar()
        title_entry = tk.Entry(
            sf, textvariable=self.save_title_var, font=("Courier New", 10),
            bg=BG3, fg=GREEN, insertbackground=GREEN, relief="flat",
            highlightbackground=BORDER, highlightthickness=1)
        title_entry.pack(fill="x", padx=20, pady=(2, 6), ipady=5)

        tk.Label(sf, text="CONTENT", font=("Courier New", 8, "bold"),
                 fg=DIM, bg=BG2).pack(anchor="w", padx=20)
        tw = tk.Frame(sf, bg=BG3, highlightbackground=BORDER, highlightthickness=1)
        tw.pack(fill="x", padx=20, pady=(2, 6))
        self.save_input = tk.Text(
            tw, font=("Courier New", 10), bg=BG3, fg=TEXT,
            insertbackground=GREEN, relief="flat", wrap="word",
            padx=8, pady=6, bd=0, height=4)
        self.save_input.pack(fill="both", expand=True)

        add_row = tk.Frame(sf, bg=BG2)
        add_row.pack(fill="x", padx=20, pady=(0, 8))
        tk.Button(add_row, text="+ SAVE", font=("Courier New", 9, "bold"),
                  bg=GREEN, fg=BG, activebackground=GREEN2, activeforeground=BG,
                  relief="flat", cursor="hand2", pady=5, padx=14,
                  command=self._add_save).pack(side="left")

        tk.Frame(sf, bg=BORDER, height=1).pack(fill="x", padx=20, pady=(0, 6))
        tk.Label(sf, text="SAVED  —  double-click to load  •  right-click to delete",
                 font=fs, fg=DIM, bg=BG2).pack(anchor="w", padx=20, pady=(0, 4))

        lf2 = tk.Frame(sf, bg=BG2)
        lf2.pack(fill="both", expand=True, padx=20, pady=(0, 4))
        self.saves_listbox = tk.Listbox(
            lf2, font=("Courier New", 9), bg="#0d0d0d", fg=TEXT,
            selectbackground="#003322", selectforeground=GREEN,
            activestyle="none", relief="flat", bd=0,
            highlightthickness=1, highlightbackground=BORDER)
        self.saves_listbox.pack(fill="both", expand=True)
        self.saves_listbox.bind("<Double-Button-1>", self._load_save_to_main)
        self.saves_listbox.bind("<Button-3>",         self._delete_save_rclick)
        self.saves_listbox.bind("<<ListboxSelect>>",  self._preview_save)
        self.saves_listbox.bind("<MouseWheel>", lambda e: self.saves_listbox.yview_scroll(-1*(e.delta//120), "units"))

        pw2 = tk.Frame(sf, bg="#0d0d0d", highlightbackground=BORDER, highlightthickness=1)
        pw2.pack(fill="x", padx=20, pady=(2, 4))
        self.saves_preview = tk.Text(
            pw2, font=("Courier New", 9), bg="#0d0d0d", fg=GREEN2,
            relief="flat", bd=0, height=3, wrap="word",
            padx=8, pady=6, state="disabled")
        self.saves_preview.pack(fill="x")

        bot = tk.Frame(sf, bg=BG2)
        bot.pack(fill="x", padx=20, pady=(4, 10))
        for txt, fg_c, cmd in [
            ("COPY",   GREEN,  self._copy_save),
            ("LOAD",   YELLOW, self._load_save_to_main),
            ("DELETE", RED,    self._delete_save_btn),
        ]:
            tk.Button(bot, text=txt, font=fs, bg=BG3, fg=DIM,
                      activebackground=BORDER, activeforeground=fg_c,
                      relief="flat", cursor="hand2", pady=4, padx=10,
                      command=cmd).pack(side="left", padx=(0, 4))

        self._refresh_saves_list()

        hf = self._history_frame

        tk.Label(hf, text=f"PASTE HISTORY  —  last {MAX_HISTORY} entries",
                 font=("Courier New", 8, "bold"), fg=GREEN, bg=BG2
                 ).pack(anchor="w", padx=20, pady=(0, 4))
        tk.Label(hf, text="double-click to load into typer",
                 font=fs, fg=DIM, bg=BG2).pack(anchor="w", padx=20, pady=(0, 6))

        lf3 = tk.Frame(hf, bg=BG2)
        lf3.pack(fill="both", expand=True, padx=20, pady=(0, 6))
        self.hist_listbox = tk.Listbox(
            lf3, font=("Courier New", 9), bg="#0d0d0d", fg=TEXT,
            selectbackground="#003322", selectforeground=GREEN,
            activestyle="none", relief="flat", bd=0,
            highlightthickness=1, highlightbackground=BORDER)
        self.hist_listbox.pack(fill="both", expand=True)
        self.hist_listbox.bind("<Double-Button-1>", self._load_history_entry)
        self.hist_listbox.bind("<<ListboxSelect>>",  self._preview_history)
        self.hist_listbox.bind("<MouseWheel>", lambda e: self.hist_listbox.yview_scroll(-1*(e.delta//120), "units"))

        ph = tk.Frame(hf, bg="#0d0d0d", highlightbackground=BORDER, highlightthickness=1)
        ph.pack(fill="x", padx=20, pady=(2, 6))
        self.hist_preview = tk.Text(
            ph, font=("Courier New", 9), bg="#0d0d0d", fg=GREEN2,
            relief="flat", bd=0, height=4, wrap="word",
            padx=8, pady=6, state="disabled")
        self.hist_preview.pack(fill="x")

        hbot = tk.Frame(hf, bg=BG2)
        hbot.pack(fill="x", padx=20, pady=(0, 10))
        tk.Button(hbot, text="DELETE SELECTED", font=fs, bg=BG3, fg=DIM,
                  activebackground=BORDER, activeforeground=RED,
                  relief="flat", cursor="hand2", pady=4,
                  command=self._delete_history_entry).pack(side="left")

        self._refresh_history_list()
        show_saves()

    # profiles logic
    def _refresh_profiles_list(self):
        self.prof_listbox.delete(0, "end")
        profiles = self._cfg.get("profiles", {})
        if not profiles: return
        favs   = sorted(n for n, d in profiles.items() if d.get("favorited"))
        others = sorted(n for n, d in profiles.items() if not d.get("favorited"))
        row = 0
        for name in favs:
            self.prof_listbox.insert("end", f"  ★  {name}")
            self.prof_listbox.itemconfig(row, fg=STAR)
            if self._cfg.get("current_profile") == name:
                self.prof_listbox.itemconfig(row, fg=GREEN)
            row += 1
        if favs and others:
            self.prof_listbox.insert("end", "")
            self.prof_listbox.itemconfig(row, fg=BG2, selectbackground="#0d0d0d",
                                          selectforeground=BG2)
            row += 1
        for name in others:
            self.prof_listbox.insert("end", f"     {name}")
            if self._cfg.get("current_profile") == name:
                self.prof_listbox.itemconfig(row, fg=GREEN)
            row += 1

    def _selected_profile_name(self):
        sel = self.prof_listbox.curselection()
        if not sel: return None
        raw = self.prof_listbox.get(sel[0]).strip().lstrip("★").strip()
        return raw if raw else None

    def _preview_profile(self, event=None):
        name = self._selected_profile_name()
        if not name: return
        profiles = self._cfg.get("profiles", {})
        if name not in profiles: return
        s = profiles[name].get("settings", {})
        lines = [
            f"Speed:      {s.get('speed','?')}    Intensity: {s.get('intensity','?')}    Fix Delay: {s.get('fix_delay','?')}s",
            f"Start Key:  {s.get('start_key','?')}    Stop Key:  {s.get('stop_key','?')}",
            f"Neighbor: {s.get('typo_neighbor','?')}  Skip: {s.get('typo_skip','?')}  "
            f"Double: {s.get('typo_double','?')}  Space: {s.get('typo_space','?')}  "
            f"Transpose: {s.get('typo_transpose','?')}",
        ]
        self.prof_preview.config(state="normal")
        self.prof_preview.delete("1.0", "end")
        self.prof_preview.insert("1.0", "\n".join(lines))
        self.prof_preview.config(state="disabled")

    def _save_profile(self):
        name = simpledialog.askstring("Save Profile", "Profile name:", parent=self.root)
        if not name: return
        name = name.strip()
        if not name: return
        profiles = self._cfg.setdefault("profiles", {})
        fav = profiles.get(name, {}).get("favorited", False)
        profiles[name] = {"settings": self._collect_settings(), "favorited": fav}
        self._cfg["current_profile"] = name
        save_config(self._cfg)
        self._refresh_profiles_list()
        self.prof_status.config(text=f"saved  '{name}'  ✓", fg=GREEN)

    def _load_profile(self, event=None):
        name = self._selected_profile_name()
        if not name:
            self.prof_status.config(text="select a profile first.", fg=DIM); return
        profiles = self._cfg.get("profiles", {})
        if name not in profiles: return
        s = profiles[name].get("settings", {})
        self.speed_slider.set(s.get("speed", 50))
        self.intensity_slider.set(s.get("intensity", 25))
        self.fix_delay_slider.set(s.get("fix_delay", 0.4))
        self.start_key.set(s.get("start_key", "F6"))
        self.stop_key.set(s.get("stop_key", "F7"))
        self.typo_neighbor.set(s.get("typo_neighbor", True))
        self.typo_skip.set(s.get("typo_skip", True))
        self.typo_double.set(s.get("typo_double", True))
        self.typo_space.set(s.get("typo_space", True))
        self.typo_transpose.set(s.get("typo_transpose", True))
        self._cfg["current_profile"] = name
        self._cfg["settings"] = self._collect_settings()
        save_config(self._cfg)
        self._register_hotkeys()
        self._refresh_profiles_list()
        self.prof_status.config(text=f"loaded  '{name}'  ✓", fg=GREEN)

    def _toggle_favorite(self, event):
        self.prof_listbox.selection_clear(0, "end")
        idx = self.prof_listbox.nearest(event.y)
        self.prof_listbox.selection_set(idx)
        name = self._selected_profile_name()
        if not name: return
        profiles = self._cfg.get("profiles", {})
        if name not in profiles: return
        cur = profiles[name].get("favorited", False)
        profiles[name]["favorited"] = not cur
        save_config(self._cfg)
        self._refresh_profiles_list()
        state = "★ favorited" if not cur else "unfavorited"
        self.prof_status.config(text=f"{state}  '{name}'", fg=YELLOW if not cur else DIM)

    def _rename_profile(self):
        name = self._selected_profile_name()
        if not name:
            self.prof_status.config(text="select a profile first.", fg=DIM); return
        new_name = simpledialog.askstring(
            "Rename Profile", f"Rename '{name}' to:",
            initialvalue=name, parent=self.root)
        if not new_name: return
        new_name = new_name.strip()
        if not new_name or new_name == name: return
        profiles = self._cfg["profiles"]
        profiles[new_name] = profiles.pop(name)
        if self._cfg.get("current_profile") == name:
            self._cfg["current_profile"] = new_name
        save_config(self._cfg)
        self._refresh_profiles_list()
        self.prof_status.config(text=f"renamed  '{name}'  →  '{new_name}'  ✓", fg=GREEN)

    def _delete_profile(self):
        name = self._selected_profile_name()
        if not name:
            self.prof_status.config(text="select a profile first.", fg=DIM); return
        if not messagebox.askyesno("Delete Profile",
                                   f"Delete profile  '{name}'?", parent=self.root): return
        self._cfg["profiles"].pop(name, None)
        if self._cfg.get("current_profile") == name:
            self._cfg["current_profile"] = None
        save_config(self._cfg)
        self._refresh_profiles_list()
        self.prof_preview.config(state="normal")
        self.prof_preview.delete("1.0", "end")
        self.prof_preview.config(state="disabled")
        self.prof_status.config(text=f"deleted  '{name}'  ✓", fg=RED)

    # saves logic
    def _add_save(self):
        title   = self.save_title_var.get().strip()
        content = self.save_input.get("1.0", "end-1c").strip()
        if not content: return
        if not title:
            title = content[:40].replace("\n", " ") + ("..." if len(content) > 40 else "")
        entry = {"title": title, "text": content}
        self._saves = [s for s in self._saves if s["text"] != content]
        self._saves.insert(0, entry)
        self._cfg["saves"] = self._saves
        save_config(self._cfg)
        self.save_title_var.set("")
        self.save_input.delete("1.0", "end")
        self._refresh_saves_list()

    def _refresh_saves_list(self):
        self.saves_listbox.delete(0, "end")
        for s in self._saves:
            self.saves_listbox.insert("end", f"  {s['title']}")

    def _preview_save(self, event=None):
        sel = self.saves_listbox.curselection()
        if not sel: return
        idx = sel[0]
        if idx >= len(self._saves): return
        text = self._saves[idx].get("text", "")
        self.saves_preview.config(state="normal")
        self.saves_preview.delete("1.0", "end")
        self.saves_preview.insert("1.0", text[:300])
        self.saves_preview.config(state="disabled")

    def _load_save_to_main(self, event=None):
        sel = self.saves_listbox.curselection()
        if not sel: return
        idx = sel[0]
        if idx >= len(self._saves): return
        text = self._saves[idx].get("text", "")
        self.text_box.delete("1.0", "end")
        self.text_box.insert("1.0", text)
        self._switch_tab(0)

    def _copy_save(self):
        sel = self.saves_listbox.curselection()
        if not sel: return
        idx = sel[0]
        if idx >= len(self._saves): return
        self.root.clipboard_clear()
        self.root.clipboard_append(self._saves[idx].get("text", ""))

    def _delete_save_rclick(self, event):
        self.saves_listbox.selection_clear(0, "end")
        idx = self.saves_listbox.nearest(event.y)
        self.saves_listbox.selection_set(idx)
        self._delete_save_btn()

    def _delete_save_btn(self):
        sel = self.saves_listbox.curselection()
        if not sel: return
        idx = sel[0]
        if idx >= len(self._saves): return
        self._saves.pop(idx)
        self._cfg["saves"] = self._saves
        save_config(self._cfg)
        self._refresh_saves_list()

    # history logic
    def _refresh_history_list(self):
        self.hist_listbox.delete(0, "end")
        for h in self._history:
            ts   = h.get("ts", "")
            text = h.get("text", "")
            preview = text[:50].replace("\n", " ")
            self.hist_listbox.insert("end", f"  {ts}  —  {preview}")

    def _preview_history(self, event=None):
        sel = self.hist_listbox.curselection()
        if not sel: return
        idx = sel[0]
        if idx >= len(self._history): return
        text = self._history[idx].get("text", "")
        self.hist_preview.config(state="normal")
        self.hist_preview.delete("1.0", "end")
        self.hist_preview.insert("1.0", text[:300])
        self.hist_preview.config(state="disabled")

    def _load_history_entry(self, event=None):
        sel = self.hist_listbox.curselection()
        if not sel: return
        idx = sel[0]
        if idx >= len(self._history): return
        text = self._history[idx].get("text", "")
        self.text_box.delete("1.0", "end")
        self.text_box.insert("1.0", text)
        self._switch_tab(0)

    def _delete_history_entry(self):
        sel = self.hist_listbox.curselection()
        if not sel: return
        idx = sel[0]
        if idx >= len(self._history): return
        self._history.pop(idx)
        save_history(self._cfg, self._history)
        self._refresh_history_list()
        self.hist_preview.config(state="normal")
        self.hist_preview.delete("1.0", "end")
        self.hist_preview.config(state="disabled")

    # keybinds
    # mouse button name constants (what we store in the stringvar)
    _MOUSE_BTN_NAMES = {
        "MOUSE4": "side button back",
        "MOUSE5": "side button forward",
        "MOUSE_SCROLL_UP":   "scroll up",
        "MOUSE_SCROLL_DOWN": "scroll down",
        "MOUSE_MIDDLE":      "middle click",
    }

    def _start_binding(self, is_start, lbl, is_hide=False):
        self.bind_status.config(text="press a key  OR  click a mouse button...", fg=YELLOW)
        self._binding_target = (is_start, is_hide)
        self._binding_active = True
        # listen for keyboard via thread
        threading.Thread(target=self._capture_key,
                         args=(is_start, lbl, is_hide), daemon=True).start()
        # listen for mouse via tkinter bindings on root
        self._mouse_bind_ids = []
        for seq, name in [
            ("<Button-4>",        "MOUSE4"),
            ("<Button-5>",        "MOUSE5"),
            ("<Button-2>",        "MOUSE_MIDDLE"),
        ]:
            bid = self.root.bind(seq,
                lambda e, n=name, s=is_start, l=lbl, h=is_hide:
                    self._capture_mouse(n, s, l, h), add="+")
            self._mouse_bind_ids.append((seq, bid))

    def _capture_key(self, is_start, lbl, is_hide=False):
        try:
            event = keyboard.read_event(suppress=True)
            if not self._binding_active:
                return
            if event.event_type == keyboard.KEY_DOWN:
                self._binding_active = False
                key = event.name
                self._apply_bind(key, is_start, lbl, is_hide)
        except Exception as ex:
            self.bind_status.config(text=f"error: {ex}", fg=RED)

    def _capture_mouse(self, btn_name, is_start, lbl, is_hide):
        if not self._binding_active:
            return
        self._binding_active = False
        # unbind mouse listeners
        self._unbind_mouse_listeners()
        self._apply_bind(btn_name, is_start, lbl, is_hide)

    def _unbind_mouse_listeners(self):
        for seq, bid in getattr(self, '_mouse_bind_ids', []):
            try: self.root.unbind(seq, bid)
            except Exception: pass
        self._mouse_bind_ids = []

    def _apply_bind(self, key, is_start, lbl, is_hide):
        if is_hide:
            self.hide_key.set(key)
        elif is_start:
            self.start_key.set(key)
        else:
            self.stop_key.set(key)
        self._register_hotkeys()
        self._autosave()
        display = self._MOUSE_BTN_NAMES.get(key, key)
        self.root.after(0, lambda: self.bind_status.config(
            text=f"bound to  [{display}]  ✓", fg=GREEN))

    def _clear_keybind(self, is_start, lbl, is_hide=False):
        if is_hide:
            self.hide_key.set("—")
        elif is_start:
            self.start_key.set("—")
        else:
            self.stop_key.set("—")
        self._register_hotkeys()
        self._autosave()
        self.bind_status.config(text="keybind cleared", fg=DIM)

    def _is_mouse_bind(self, key):
        return key.upper() in self._MOUSE_BTN_NAMES

    def _register_hotkeys(self):
        # unregister old keyboard hotkeys
        for attr in ('_registered_start', '_registered_stop', '_registered_hide'):
            try:
                hk = getattr(self, attr, None)
                if hk:
                    keyboard.remove_hotkey(hk)
            except Exception: pass
        self._registered_start = None
        self._registered_stop  = None
        self._registered_hide  = None

        # unregister old tkinter mouse listeners
        for attr in ('_mouse_start_ids', '_mouse_stop_ids', '_mouse_hide_ids'):
            for seq, bid in getattr(self, attr, []):
                try: self.root.unbind(seq, bid)
                except Exception: pass
            setattr(self, attr, [])

        # stop any existing pynput global mouse listener
        if hasattr(self, '_pynput_listener') and self._pynput_listener is not None:
            try:
                self._pynput_listener.stop()
            except Exception: pass
            self._pynput_listener = None

        def _reg_kb(key, callback, attr):
            try:
                k = key.lower()
                if k and k != "—" and not self._is_mouse_bind(k):
                    setattr(self, attr, keyboard.add_hotkey(k, callback, suppress=False))
            except Exception: pass

        # map of which mouse-bound key goes to which callback
        # we use pynput for all mouse binds so they work globally (even when hidden)
        _mouse_callbacks = {}  # pynput_button_name -> callback

        _PYNPUT_BTN_MAP = {
            "MOUSE4":       "x1",    # pynput Button.x1
            "MOUSE5":       "x2",    # pynput Button.x2
            "MOUSE_MIDDLE": "middle",
        }

        def _reg_mouse_global(key, callback):
            key_up = key.upper()
            if key_up in _PYNPUT_BTN_MAP:
                btn_name = _PYNPUT_BTN_MAP[key_up]
                _mouse_callbacks[btn_name] = callback
            elif key_up in ("MOUSE_SCROLL_UP", "MOUSE_SCROLL_DOWN"):
                _mouse_callbacks[key_up] = callback

        def _reg_mouse_tkinter(key, callback, attr):
            """Fallback tkinter binding (used only when pynput unavailable)."""
            key_up = key.upper()
            ids = []
            seq_map = {
                "MOUSE4":            "<Button-4>",
                "MOUSE5":            "<Button-5>",
                "MOUSE_MIDDLE":      "<Button-2>",
                "MOUSE_SCROLL_UP":   "<MouseWheel>",
                "MOUSE_SCROLL_DOWN": "<MouseWheel>",
            }
            if key_up in seq_map:
                seq = seq_map[key_up]
                if key_up in ("MOUSE_SCROLL_UP", "MOUSE_SCROLL_DOWN"):
                    def _mw(e, k=key_up, cb=callback):
                        if (k == "MOUSE_SCROLL_UP" and e.delta > 0) or \
                           (k == "MOUSE_SCROLL_DOWN" and e.delta < 0):
                            cb()
                    bid = self.root.bind(seq, _mw, add="+")
                else:
                    bid = self.root.bind(seq, lambda e, cb=callback: cb(), add="+")
                ids.append((seq, bid))
            setattr(self, attr, ids)

        for key_var, cb, kb_attr, ms_attr in [
            (self.start_key, self._hotkey_start, "_registered_start", "_mouse_start_ids"),
            (self.stop_key,  self._hotkey_stop,  "_registered_stop",  "_mouse_stop_ids"),
            (self.hide_key,  self._hotkey_hide,  "_registered_hide",  "_mouse_hide_ids"),
        ]:
            key = key_var.get()
            if not key or key == "—":
                continue
            if self._is_mouse_bind(key):
                if _PYNPUT_OK:
                    _reg_mouse_global(key, cb)
                else:
                    _reg_mouse_tkinter(key, cb, ms_attr)
            else:
                _reg_kb(key, cb, kb_attr)

        # start a single pynput listener covering all registered mouse binds
        if _PYNPUT_OK and _mouse_callbacks:
            scroll_up_cb   = _mouse_callbacks.get("MOUSE_SCROLL_UP")
            scroll_down_cb = _mouse_callbacks.get("MOUSE_SCROLL_DOWN")
            btn_map = {k: v for k, v in _mouse_callbacks.items()
                       if k not in ("MOUSE_SCROLL_UP", "MOUSE_SCROLL_DOWN")}

            def _on_click(x, y, button, pressed):
                if not pressed:
                    return
                bname = button.name  # 'x1', 'x2', 'middle', etc.
                cb = btn_map.get(bname)
                if cb:
                    self.root.after(0, cb)

            def _on_scroll(x, y, dx, dy):
                if dy > 0 and scroll_up_cb:
                    self.root.after(0, scroll_up_cb)
                elif dy < 0 and scroll_down_cb:
                    self.root.after(0, scroll_down_cb)

            listener = _pynput_mouse.Listener(
                on_click=_on_click,
                on_scroll=_on_scroll if (scroll_up_cb or scroll_down_cb) else None,
            )
            listener.daemon = True
            listener.start()
            self._pynput_listener = listener
        else:
            self._pynput_listener = None

    def _hotkey_start(self):
        if not self.is_running:
            self.root.after(0, self._start_sequence)

    def _hotkey_stop(self):
        if self.is_running:
            self.root.after(0, self._stop_typing)

    def _hotkey_hide(self):
        self.root.after(0, self._toggle_visibility)

    def _toggle_visibility(self):
        if self._is_hidden:
            self.root.deiconify()
            self._is_hidden = False
        else:
            self.root.withdraw()
            self._is_hidden = True

    # text helpers
    # page 4 text compare
    def _build_compare_page(self):
        p = self.pages[4]

        hdr = tk.Frame(p, bg=BG2)
        hdr.pack(fill="x", padx=20, pady=(16, 6))
        tk.Label(hdr, text="🔀  TEXT COMPARE", font=("Courier New", 12, "bold"),
                 fg=GREEN, bg=BG2).pack(side="left")
        tk.Label(hdr, text="keep what's the same, swap what's different",
                 font=("Courier New", 8), fg=DIM, bg=BG2).pack(side="left", padx=14)

        tk.Frame(p, bg=BORDER, height=1).pack(fill="x", padx=20, pady=(0, 10))

        # two input boxes side by side
        cols = tk.Frame(p, bg=BG2)
        cols.pack(fill="both", expand=True, padx=20, pady=(0, 6))
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)

        # left original text
        tk.Label(cols, text="ORIGINAL TEXT", font=("Courier New", 8, "bold"),
                 fg=DIM, bg=BG2).grid(row=0, column=0, sticky="w", pady=(0, 4))
        lf = tk.Frame(cols, bg=BG3, highlightbackground=BORDER, highlightthickness=1)
        lf.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        cols.rowconfigure(1, weight=1)
        lsb = tk.Scrollbar(lf, bg=BG3, troughcolor=BG3, activebackground=BORDER,
                           relief="flat", command=None)
        lsb.pack(side="right", fill="y")
        self.cmp_original = tk.Text(
            lf, font=("Courier New", 9), bg=BG3, fg=TEXT,
            insertbackground=GREEN, relief="flat", wrap="word",
            padx=8, pady=6, bd=0, undo=True,
            yscrollcommand=lsb.set)
        self.cmp_original.pack(side="left", fill="both", expand=True)
        lsb.config(command=self.cmp_original.yview)

        # right new text
        tk.Label(cols, text="NEW TEXT", font=("Courier New", 8, "bold"),
                 fg=DIM, bg=BG2).grid(row=0, column=1, sticky="w", pady=(0, 4))
        rf = tk.Frame(cols, bg=BG3, highlightbackground=BORDER, highlightthickness=1)
        rf.grid(row=1, column=1, sticky="nsew", padx=(6, 0))
        rsb = tk.Scrollbar(rf, bg=BG3, troughcolor=BG3, activebackground=BORDER,
                           relief="flat", command=None)
        rsb.pack(side="right", fill="y")
        self.cmp_new = tk.Text(
            rf, font=("Courier New", 9), bg=BG3, fg=TEXT,
            insertbackground=GREEN, relief="flat", wrap="word",
            padx=8, pady=6, bd=0, undo=True,
            yscrollcommand=rsb.set)
        self.cmp_new.pack(side="left", fill="both", expand=True)
        rsb.config(command=self.cmp_new.yview)

        # compare button
        tk.Frame(p, bg=BORDER, height=1).pack(fill="x", padx=20, pady=(4, 6))
        btn_row = tk.Frame(p, bg=BG2)
        btn_row.pack(fill="x", padx=20, pady=(0, 6))

        tk.Button(btn_row, text="🔀  COMPARE", font=("Courier New", 10, "bold"),
                  bg=GREEN, fg=BG, activebackground=GREEN2, activeforeground=BG,
                  relief="flat", cursor="hand2", pady=6, padx=16,
                  command=self._run_compare).pack(side="left")

        tk.Button(btn_row, text="LOAD RESULT → TYPER", font=("Courier New", 9, "bold"),
                  bg=BG3, fg=DIM, activebackground=BORDER, activeforeground=GREEN,
                  relief="flat", cursor="hand2", pady=6, padx=12,
                  command=self._load_compare_to_typer).pack(side="left", padx=(8, 0))

        tk.Button(btn_row, text="CLEAR ALL", font=("Courier New", 9, "bold"),
                  bg=BG3, fg=DIM, activebackground=BORDER, activeforeground=RED,
                  relief="flat", cursor="hand2", pady=6, padx=12,
                  command=self._clear_compare).pack(side="left", padx=(8, 0))

        self.cmp_stat = tk.Label(btn_row, text="", font=("Courier New", 8),
                                  fg=DIM, bg=BG2)
        self.cmp_stat.pack(side="right")

        # result box
        tk.Label(p, text="RESULT  —  green = kept from original  •  yellow = changed to new",
                 font=("Courier New", 7), fg=DIM, bg=BG2).pack(anchor="w", padx=20)

        res_wrap = tk.Frame(p, bg="#0d0d0d",
                            highlightbackground=BORDER, highlightthickness=1)
        res_wrap.pack(fill="x", padx=20, pady=(4, 12))
        res_sb = tk.Scrollbar(res_wrap, bg=BG3, troughcolor=BG3,
                              activebackground=BORDER, relief="flat")
        res_sb.pack(side="right", fill="y")
        self.cmp_result = tk.Text(
            res_wrap, font=("Courier New", 9), bg="#0d0d0d", fg=TEXT,
            relief="flat", bd=0, height=7, wrap="word",
            padx=10, pady=8, state="disabled",
            yscrollcommand=res_sb.set)
        self.cmp_result.pack(side="left", fill="both", expand=True)
        res_sb.config(command=self.cmp_result.yview)

        # colour tags for result box
        self.cmp_result.tag_configure("kept",    foreground=GREEN)
        self.cmp_result.tag_configure("changed", foreground=YELLOW)

    # compare logic
    def _run_compare(self):
        orig = self.cmp_original.get("1.0", "end-1c")
        new  = self.cmp_new.get("1.0", "end-1c")

        if not orig.strip() or not new.strip():
            self.cmp_stat.config(text="paste text into both boxes first", fg=RED)
            return

        import difflib

        # work word-by-word so matching is intuitive
        orig_words = orig.split()
        new_words  = new.split()

        matcher = difflib.SequenceMatcher(None, orig_words, new_words, autojunk=False)
        opcodes = matcher.get_opcodes()

        self.cmp_result.config(state="normal")
        self.cmp_result.delete("1.0", "end")

        kept_count    = 0
        changed_count = 0

        for tag, i1, i2, j1, j2 in opcodes:
            if tag == "equal":
                # words are identical keep from original, show green
                chunk = " ".join(orig_words[i1:i2])
                self.cmp_result.insert("end", chunk + " ", "kept")
                kept_count += i2 - i1
            elif tag in ("replace", "insert"):
                # words changed use the new version, show yellow
                chunk = " ".join(new_words[j1:j2])
                self.cmp_result.insert("end", chunk + " ", "changed")
                changed_count += j2 - j1
            # "delete" words only in original, not in new drop them silently

        self.cmp_result.config(state="disabled")

        total = kept_count + changed_count
        pct   = int(kept_count / max(total, 1) * 100)
        self.cmp_stat.config(
            text=f"{kept_count} words kept ({pct}%)  •  {changed_count} words changed",
            fg=GREEN)

    def _load_compare_to_typer(self):
        content = self.cmp_result.get("1.0", "end-1c").strip()
        if not content:
            self.cmp_stat.config(text="run compare first", fg=RED)
            return
        self.text_box.delete("1.0", "end")
        self.text_box.insert("1.0", content)
        self._on_key()
        self._switch_tab(0)
        self._set_status("compare result loaded into typer ✓")

    def _clear_compare(self):
        self.cmp_original.delete("1.0", "end")
        self.cmp_new.delete("1.0", "end")
        self.cmp_result.config(state="normal")
        self.cmp_result.delete("1.0", "end")
        self.cmp_result.config(state="disabled")
        self.cmp_stat.config(text="", fg=DIM)

    def _on_key(self, event=None):
        text = self.text_box.get("1.0", "end-1c")
        chars = len(text)
        words = len(text.split()) if text.strip() else 0
        self.char_label.config(text=f"{chars} chars,  {words} words")

    def _right_click_resume(self, event):
        idx = self.text_box.index(f"@{event.x},{event.y}")
        try:
            char_offset = int(self.text_box.count("1.0", idx, "chars")[0])
        except Exception:
            return
        self._resume_index = char_offset
        self._can_resume   = True
        self.resume_btn.config(state="normal", fg=YELLOW)
        self._set_status(f"resume point set at char {char_offset}")

    def _build_word_spans(self, text):
        spans = []
        i = 0
        while i < len(text):
            if not text[i].isspace():
                j = i
                while j < len(text) and not text[j].isspace():
                    j += 1
                spans.append((i, j))
                i = j
            else:
                i += 1
        return spans

    def _update_highlight_for_char(self, char_idx):
        for wi, (start, end) in enumerate(self._word_spans):
            if start <= char_idx < end:
                if wi != self._current_word:
                    self._current_word = wi
                    self.root.after(0, lambda s=start, e=end, w=wi: self._do_highlight(s, e, w))
                break

    def _do_highlight(self, start, end, wi):
        self.text_box.tag_remove("current_word", "1.0", "end")
        if wi > 0:
            ps, pe = self._word_spans[wi - 1]
            s_idx = f"1.0+{ps}c"
            e_idx = f"1.0+{pe}c"
            self.text_box.tag_add("done_word", s_idx, e_idx)
        s_idx = f"1.0+{start}c"
        e_idx = f"1.0+{end}c"
        self.text_box.tag_add("current_word", s_idx, e_idx)
        self.text_box.see(s_idx)
        word = self.text_box.get(s_idx, e_idx)
        self.word_pill.config(text=f"  {word}  ")

    def _clear_highlights(self):
        self.text_box.tag_remove("current_word", "1.0", "end")
        self.text_box.tag_remove("done_word",    "1.0", "end")

    # run / stop / resume
    def _start_sequence(self):
        text = self.text_box.get("1.0", "end-1c").strip()
        if not text:
            self._set_status("nothing to type..."); return
        if self.is_running: return
        self._push_history(text)
        self._full_text    = text
        self._word_spans   = self._build_word_spans(text)
        self._current_word = -1
        self._resume_index = 0
        self._can_resume   = False
        self._clear_highlights()
        self._launch(text, start_index=0)

    def _resume_sequence(self):
        if self.is_running or not self._can_resume: return
        remaining = self._full_text[self._resume_index:]
        if not remaining:
            self._set_status("nothing left to resume."); return
        self._can_resume = False
        self.resume_btn.config(state="disabled", fg=DIM)
        self._launch(self._full_text, start_index=self._resume_index)

    def _launch(self, text, start_index=0):
        self.is_running = True
        self.stop_flag  = False
        self.run_btn.config(state="disabled")
        self.resume_btn.config(state="disabled", fg=DIM)
        self.stop_btn.config(state="normal", fg=RED)
        self._set_status("click your target window now...")
        self.status_pill.config(text="● STARTING", fg=YELLOW)
        threading.Thread(target=self._countdown_then_type,
                         args=(text, start_index), daemon=True).start()

    def _countdown_then_type(self, text, start_index):
        for i in (3, 2, 1):
            if self.stop_flag:
                self._reset_ui(stopped=True); return
            self.root.after(0, lambda n=i: self.countdown_label.config(
                text=f"typing in {n}..."))
            time.sleep(1)
        self.root.after(0, lambda: self.countdown_label.config(text=""))
        self.root.after(0, lambda: self.status_pill.config(text="● RUNNING", fg=GREEN))
        self._set_status("typing...")
        self._type_text(text, start_index)

    # core typing engine
    def _type_text(self, text, start_index=0):
        speed     = self.speed_slider.get() / 100
        intensity = self.intensity_slider.get() / 100
        fix_delay = self.fix_delay_slider.get()

        do_neighbor  = self.typo_neighbor.get()
        do_skip      = self.typo_skip.get()
        do_double    = self.typo_double.get()
        do_space     = self.typo_space.get()
        do_transpose = self.typo_transpose.get()

        base_lo, base_hi = 0.02, 0.08

        easy_mask = [False] * len(text)
        j = 0
        while j < len(text):
            if text[j].isalpha():
                end = j
                while end < len(text) and text[end].isalpha():
                    end += 1
                word = text[j:end].lower()
                is_easy = word in EASY_WORDS or len(word) <= 3
                for k in range(j, end):
                    easy_mask[k] = is_easy
                j = end
            else:
                j += 1

        def char_delay(fast=False):
            if fast:
                lo = base_lo * (0.45 + random.random() * 0.25)
                hi = base_hi * (0.45 + random.random() * 0.25)
            else:
                lo, hi = base_lo, base_hi
            time.sleep(max(0.01, random.uniform(lo, hi) * (1.5 - speed)))

        def fix_pause():
            time.sleep(max(0.08, fix_delay * random.uniform(0.7, 1.3) * (1.5 - speed)))

        def press_bs(n=1):
            for _ in range(n):
                pyautogui.press('backspace')
                time.sleep(0.03)

        def write_char(c):
            if c == '\n':   pyautogui.press('enter')
            elif c == '\t': pyautogui.press('tab')
            else:           pyautogui.write(c, interval=0)

        i = start_index
        while i < len(text):
            if self.stop_flag:
                self._resume_index = i
                break

            char = text[i]
            fast = easy_mask[i] if i < len(easy_mask) else False
            self._update_highlight_for_char(i)

            if (do_space and char == ' '
                    and i + 1 < len(text) and text[i+1].isalpha()
                    and random.random() < intensity * 0.5):
                nc = text[i + 1]
                write_char(nc); char_delay(fast=fast); fix_pause()
                if self.stop_flag: self._resume_index = i; break
                press_bs(1); write_char(' '); time.sleep(0.03)
                write_char(nc); char_delay(fast=fast)
                i += 2; continue

            if (do_transpose and char.isalpha()
                    and i + 1 < len(text) and text[i+1].isalpha()
                    and random.random() < intensity * 0.4):
                nc = text[i + 1]
                write_char(nc); char_delay(fast=fast)
                write_char(char); char_delay(fast=fast)
                fix_pause()
                if self.stop_flag: self._resume_index = i; break
                press_bs(2); write_char(char); time.sleep(0.03)
                write_char(nc); char_delay(fast=fast)
                i += 2; continue

            if char.isalpha():
                pool = ([("neighbor")] * do_neighbor +
                        [("double")]   * do_double +
                        [("skip")]     * do_skip)
                if pool and random.random() < intensity * 0.55:
                    typo_type = random.choice(pool)
                    if typo_type == "neighbor":
                        write_char(get_typo_neighbor(char)); fix_pause()
                        if self.stop_flag: self._resume_index = i; break
                        press_bs(1)
                    elif typo_type == "double":
                        write_char(char); time.sleep(random.uniform(0.02, 0.05))
                        write_char(char); fix_pause()
                        if self.stop_flag: self._resume_index = i; break
                        press_bs(1); char_delay(fast=fast); i += 1; continue
                    elif typo_type == "skip":
                        if i + 1 < len(text) and text[i+1].isalpha():
                            write_char(text[i+1]); fix_pause()
                            if self.stop_flag: self._resume_index = i; break
                            press_bs(1)

            write_char(char)
            char_delay(fast=fast)
            if char == ' ' and random.random() < (0.05 if fast else 0.10):
                time.sleep(random.uniform(0.1, 0.35) * (1.5 - speed))
            i += 1

        finished = not self.stop_flag
        self._reset_ui(stopped=not finished)
        if finished:
            self._set_status("done ✓")
            self._can_resume = False
            self._clear_highlights()
            self.word_pill.config(text="")
            self.root.after(0, lambda: self.status_pill.config(text="● STOPPED", fg=RED))
        else:
            pct = int(self._resume_index / max(len(text), 1) * 100)
            self._set_status(f"stopped at {pct}%  —  right-click a word or click RESUME")
            self._can_resume = True
            self.root.after(0, lambda: self.status_pill.config(text="● STOPPED", fg=RED))
            self.root.after(0, lambda: self.resume_btn.config(state="normal", fg=YELLOW))

    def _play_finish_sound(self, sound_name=None):
        """Play finish sound using winsound.Beep() — works on all Windows versions."""
        if sound_name is None:
            sound_name = self.finish_sound.get()
        if sound_name == "none":
            return

        import winsound, threading

        # each sound is a list of (frequency_hz, duration_ms) tuples
        SOUNDS = {
            "ding":  [(1050, 80), (1400, 180)],
            "tada":  [(523, 80), (659, 80), (784, 80), (1047, 200)],
            "chime": [(880, 120), (1100, 120), (1320, 120), (1760, 200)],
            "ping":  [(1800, 60), (1600, 40), (2000, 120)],
            "yeah":  [(300, 60), (500, 60), (700, 80), (900, 60), (1100, 150)],
        }

        notes = SOUNDS.get(sound_name, [])
        if not notes:
            return

        def _play():
            for freq, dur in notes:
                try:
                    winsound.Beep(freq, dur)
                except Exception:
                    pass

        threading.Thread(target=_play, daemon=True).start()

    def _stop_typing(self):
        self.stop_flag = True
        self._set_status("stopping...")

    def _reset_ui(self, stopped=False):
        self.is_running = False
        self.root.after(0, lambda: self.run_btn.config(state="normal"))
        self.root.after(0, lambda: self.stop_btn.config(state="disabled", fg=DIM))
        self.root.after(0, lambda: self.countdown_label.config(text=""))
        if not stopped:
            self.root.after(200, self._play_finish_sound)

    def _set_status(self, msg):
        self.root.after(0, lambda: self.status_var.set(msg))


def main():
    # use a hidden parent so overrideredirect child still shows in taskbar
    root_hidden = tk.Tk()
    root_hidden.withdraw()
    root_hidden.title("PasteTyper v20")

    # set icon on hidden root (shows in taskbar) try icon.ico first, then logo.png
    ico_path = os.path.join(SCRIPT_DIR, "icon.ico")
    if os.path.exists(ico_path):
        try:
            root_hidden.iconbitmap(ico_path)
        except Exception:
            pass
    else:
        icon_path = os.path.join(SCRIPT_DIR, "logo.png")
        if os.path.exists(icon_path):
            try:
                from PIL import Image, ImageTk
                img = Image.open(icon_path).resize((64, 64), Image.LANCZOS)
                _icon = ImageTk.PhotoImage(img)
                root_hidden.iconphoto(True, _icon)
                root_hidden._icon_ref = _icon
            except Exception:
                pass

    root = tk.Toplevel(root_hidden)
    root.title("PasteTyper v20")

    app  = PasteTyperApp(root)

    def _on_destroy():
        try:
            app._autosave()
        except Exception:
            pass
        os._exit(0)

    root.protocol("WM_DELETE_WINDOW", _on_destroy)
    root_hidden.protocol("WM_DELETE_WINDOW", _on_destroy)

    root.mainloop()

if __name__ == "__main__":
    main()
