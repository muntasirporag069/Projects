#!/usr/bin/env python3
"""
PixelCat - a free, DIY pixel cat that lives on your desktop.
Run:  pip install PySide6 pynput   then   python pixelcat.py
Right-click the cat for settings. No art files needed: the cat is drawn in code.
Privacy: only the *number* of key presses is counted, never which keys.
"""
import sys, os, json, math, time, random, struct, wave, tempfile, threading, shutil, pathlib
from collections import deque
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from PySide6.QtCore import Qt, QTimer, QRectF, QUrl, QPoint
from PySide6.QtGui import (QPainter, QColor, QFont, QCursor, QPainterPath,
                           QFontMetrics, QPen)
from PySide6.QtWidgets import (QApplication, QWidget, QMenu, QInputDialog,
                               QColorDialog, QMessageBox, QFileDialog)
try:
    from PySide6.QtMultimedia import QSoundEffect
except Exception:
    QSoundEffect = None
try:
    from pynput import mouse, keyboard
except Exception:
    mouse = keyboard = None

# ---------------------------------------------------------------- settings
CFG_PATH = os.path.join(os.path.expanduser("~"), ".pixelcat.json")
DEFAULTS = dict(name="friend", color="#f2a65a", pattern="stripes",
                stretch_min=45, water_min=30, pinned="", port=8765, x=None, y=None,
                peek=False, auto_peek=True, walk=True, play=True)

def load_cfg():
    cfg = dict(DEFAULTS)
    try:
        with open(CFG_PATH, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg

def save_cfg(cfg):
    try:
        with open(CFG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass

# ---------------------------------------------------------------- helpers
S = 5                    # screen pixels per "cat pixel"
CW, CH = 40, 48          # cat canvas in cat pixels
W, H = 320, 340          # window size in screen pixels
OX = (W - CW * S) // 2   # cat's left edge inside the window
TEXT_FLAGS = Qt.AlignmentFlag.AlignCenter.value | Qt.TextFlag.TextWordWrap.value

OUT, WHITE, PINK = QColor("#2b2233"), QColor("#fffaf0"), QColor("#ff9db5")
CREAM, DARK, GREY = QColor("#fff0d6"), QColor("#1c1424"), QColor("#9a9ab8")
HEART = [".X.X.", "XXXXX", "XXXXX", ".XXX.", "..X.."]

def clamp(v, a, b): return max(a, min(b, v))

def mix(a, b, t):
    return QColor(*(int(x + (y - x) * t) for x, y in
                    ((a.red(), b.red()), (a.green(), b.green()), (a.blue(), b.blue()))))

def shade(c, f):
    return QColor(clamp(int(c.red() * f), 0, 255), clamp(int(c.green() * f), 0, 255),
                  clamp(int(c.blue() * f), 0, 255))

def make_meow(path):
    """Synthesize a tiny 'mew' sound so no audio file is needed."""
    sr, n, ph, buf = 22050, int(22050 * 0.45), 0.0, bytearray()
    for i in range(n):
        t = i / n
        ph += 2 * math.pi * (450 + 500 * math.sin(math.pi * t)) / sr
        v = 0.5 * math.sin(ph) + 0.25 * math.sin(2 * ph) + 0.12 * math.sin(3 * ph)
        buf += struct.pack("<h", int(32767 * 0.6 * (math.sin(math.pi * t) ** 0.7) * v))
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(bytes(buf))

def mk(p):
    """Tiny pixel-drawing helpers bound to a painter."""
    def R(x, y, w, h, c): p.fillRect(QRectF(x, y, w, h), c)
    def part(x, y, w, h, c): R(x - 1, y - 1, w + 2, h + 2, OUT); R(x, y, w, h, c)
    def blit(rows, x, y, c):
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                if ch == "X": R(x + i, y + j, 1, 1, c)
    return R, part, blit

# ------------------------------------------------------------ desktop tidying
CATS = {
    "Images": {"png", "jpg", "jpeg", "gif", "webp", "bmp", "svg", "heic", "tiff"},
    "Documents": {"pdf", "doc", "docx", "txt", "md", "rtf", "odt", "ppt", "pptx", "xls", "xlsx", "csv"},
    "Code": {"py", "ipynb", "js", "ts", "html", "css", "json", "c", "cpp", "java", "sh", "r"},
    "Media": {"mp3", "wav", "flac", "mp4", "mkv", "mov", "avi", "webm"},
    "Archives": {"zip", "rar", "7z", "tar", "gz"},
    "Installers": {"exe", "msi", "dmg", "pkg", "apk"},
}
CAT_COLORS = {"Images": "#5aa9e6", "Documents": "#e8505b", "Code": "#4fb286",
              "Media": "#b57edc", "Archives": "#e0a030", "Installers": "#888888", "Other": "#aaaaaa"}
SKIP_EXT = {"lnk", "url", "ini", "tmp", "ds_store"}
UNDO_PATH = os.path.join(os.path.expanduser("~"), ".pixelcat_undo.json")

def category(path):
    ext = path.suffix.lower().lstrip(".")
    return next((c for c, exts in CATS.items() if ext in exts), "Other")

def plan_tidy(folder, limit=60):
    """Plain files only (no folders, shortcuts or hidden files), at most `limit`."""
    out = []
    for f in sorted(pathlib.Path(folder).iterdir()):
        if (f.is_file() and not f.name.startswith(".") and f.name.lower() != "desktop.ini"
                and f.suffix.lower().lstrip(".") not in SKIP_EXT):
            out.append((f, category(f)))
    return out[:limit]

def unique_dest(d, name):
    """Never overwrite: add ' (1)', ' (2)'... if the name is taken."""
    dst, i = d / name, 1
    while dst.exists():
        dst = d / f"{dst.stem.rsplit(' (', 1)[0] if i > 1 else dst.stem} ({i}){dst.suffix}"; i += 1
    return dst

def move_file(src, cat, root):
    d = root / cat; d.mkdir(exist_ok=True)
    dst = unique_dest(d, src.name); shutil.move(str(src), str(dst))
    return str(src), str(dst)

def default_desktop():
    home = pathlib.Path.home()
    ex = [c for c in (home / "OneDrive" / "Desktop", home / "Desktop") if c.exists()]
    return max(ex, key=lambda c: sum(1 for _ in c.iterdir())) if ex else None

def is_fullscreen(own_hwnd):
    """Windows only: is another app (browser video, game...) covering the whole screen?"""
    if sys.platform != "win32": return False
    try:
        import ctypes
        from ctypes import wintypes
        u = ctypes.windll.user32
        hwnd = u.GetForegroundWindow()
        if not hwnd or hwnd == own_hwnd: return False
        buf = ctypes.create_unicode_buffer(64); u.GetClassNameW(hwnd, buf, 64)
        if buf.value in ("Progman", "WorkerW", "Shell_TrayWnd"): return False
        r = wintypes.RECT(); u.GetWindowRect(hwnd, ctypes.byref(r))
        return (r.left <= 0 and r.top <= 0 and
                r.right >= u.GetSystemMetrics(0) and r.bottom >= u.GetSystemMetrics(1))
    except Exception:
        return False

# ------------------------------------------------- global input + agent hooks
class Shared:
    """Written by background threads, read by the cat every frame."""
    def __init__(self):
        self.keys = deque(maxlen=64)   # timestamps only
        self.scroll = 0.0
        self.last_input = time.time()
        self.agent, self.agent_t = "idle", 0.0
        self.say = None
        self.peek_toggle = False

def start_listeners(sh):
    if not mouse:
        print("pynput not available: typing/scroll reactions disabled"); return
    def on_scroll(x, y, dx, dy): sh.scroll += abs(dy) or abs(dx); sh.last_input = time.time()
    def on_click(*a): sh.last_input = time.time()
    def on_press(key): sh.keys.append(time.time()); sh.last_input = time.time()
    try:
        mouse.Listener(on_scroll=on_scroll, on_click=on_click).start()
        keyboard.Listener(on_press=on_press).start()
        keyboard.GlobalHotKeys({"<ctrl>+<alt>+p": lambda: setattr(sh, "peek_toggle", True)}).start()
    except Exception as e:
        print("Could not start input listeners:", e)

def start_server(sh, port):
    """Tiny local-only API so AI tools can talk to the cat:
       /status?state=thinking|done|idle    /say?text=Hello&secs=5"""
    class Handler(BaseHTTPRequestHandler):
        def handle_any(self):
            try:
                u, q = urlparse(self.path), parse_qs(urlparse(self.path).query)
                if u.path == "/status":
                    sh.agent, sh.agent_t = q.get("state", ["idle"])[0], time.time()
                elif u.path == "/say":
                    sh.say = (q.get("text", [""])[0][:80], float(q.get("secs", ["5"])[0]))
            except Exception:
                pass
            self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
        do_GET = do_POST = handle_any
        def log_message(self, *a): pass
    try:
        srv = HTTPServer(("127.0.0.1", port), Handler)   # localhost only
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    except OSError:
        print(f"Port {port} busy: agent hooks disabled")

# ---------------------------------------------------------------- the cat
class Cat(QWidget):
    def __init__(self):
        super().__init__()
        self.cfg, self.sh = load_cfg(), Shared()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint |
                            Qt.Tool | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_MacAlwaysShowToolWindow)
        self.setMouseTracking(True)
        self.setFixedSize(W, H)
        geo = QApplication.primaryScreen().availableGeometry()
        x, y = self.cfg["x"], self.cfg["y"]
        if x is None or y is None or not geo.contains(x + W // 2, y + H // 2):
            x, y = geo.right() - W - 10, geo.bottom() - H + 20
        self.move(x, y)

        now = time.time()
        self.last_tick, self.lastc, self.speed = now, QCursor.pos(), 0.0
        self.heat = self.paper = self.paper_t = self.pet_acc = self.tilt = 0.0
        self.typing = self.kb_show = self.sleeping = self.thinking = self.dragging = False
        self.purr_until = self.hunt_until = self.jump_until = self.grow_until = 0.0
        self.blink_until, self.next_blink, self.gsc = 0.0, now + 3, 1.0
        self.bubble, self.seen_agent_t, self.last_key_t = None, 0.0, 0.0
        self.last_stretch = self.last_water = now
        self.pomo, self.reminders, self.drag_off, self.last_mp = None, [], QPoint(), None
        self.px, self.py, self.home_x = float(x), float(y), float(x)
        self.mode, self.facing, self.walk_target = "sit", 1, 0
        self.next_walk, self.pop_until, self.next_fs, self.fs = now + 15, 0.0, 0.0, False
        self.tidy, self.swatting = None, False
        self.FEED_DUR = 6.0
        self.feed_start, self.bowl_until, self.food_level, self.eating = 0.0, 0.0, 0.0, False
        self.ball, self.chase, self.swat_until, self.peeking = None, None, 0.0, False
        self.next_play = now + random.uniform(180, 420)
        self.font_ui = QFont("Consolas", 10, QFont.Bold)
        self.font_ui.setStyleHint(QFont.Monospace)

        self.snd = None
        if QSoundEffect:
            try:
                path = os.path.join(tempfile.gettempdir(), "pixelcat_meow.wav")
                make_meow(path)
                self.snd = QSoundEffect(self)
                self.snd.setSource(QUrl.fromLocalFile(path)); self.snd.setVolume(0.6)
            except Exception:
                self.snd = None

        start_listeners(self.sh); start_server(self.sh, self.cfg["port"])
        self.timer = QTimer(self); self.timer.timeout.connect(self.tick); self.timer.start(33)
        self.say(f"Hi {self.cfg['name']}! Right-click me~", 5)

    # ---- small actions
    def meow(self):
        if self.snd: self.snd.play()
        else: QApplication.beep()

    def say(self, text, secs=5, sound=True):
        self.bubble = (text, time.time() + secs)
        self.pop_until = max(self.pop_until, time.time() + secs + 0.5)   # pop out of peek mode
        if sound: self.meow()

    def start_feed(self):
        if self.tidy or self.chase is not None: return
        now = time.time()
        self.mode = "sit"
        self.feed_start, self.bowl_until = now, now + self.FEED_DUR + 2.5
        self.say(f"Yum, thank you {self.cfg['name']}!", 3)

    def start_play(self, kind=None):
        if self.tidy or self.feed_start or self.chase is not None or self.ball:
            return
        kind = kind or random.choice(("ball", "butterfly"))
        self.next_play = time.time() + random.uniform(180, 420)
        if kind == "ball":
            self.mode = "sit"
            self.ball = dict(x=20.0, vx=random.uniform(-2, 2),
                              until=time.time() + 22, next_bat=time.time() + 0.6)
            self.say("Ooh, a ball!", 3)
        else:
            bfly = Butterfly(self)
            bfly.show()
            self.chase = bfly
            self.say("A butterfly!", 3)

    def update_chase(self, now, dt, geo):
        """Chase whatever self.chase (a Butterfly widget) is doing, instead
        of the normal idle/random-walk logic."""
        target = self.chase
        if target is None or not target.isVisible():
            self.chase, self.mode = None, "sit"
            self.home_x = self.px
            return
        tx = target.x() + target.width() / 2 - W / 2
        dx = tx - self.px
        if abs(dx) < 26:
            self.mode = "sit"
            self.swatting, self.swat_until = True, now + 0.3
            target.spook(self.px + W / 2)
        else:
            self.mode = "walk"
            self.facing = 1 if dx > 0 else -1
            self.px += 95 * dt * self.facing
        if now > self.swat_until: self.swatting = False

    # ---- per-frame logic
    def tick(self):
        now = time.time(); dt = max(now - self.last_tick, 1e-3); self.last_tick = now
        sh, name = self.sh, self.cfg["name"]

        # mouse speed (polled, needs no permissions)
        c = QCursor.pos()
        d = math.hypot(c.x() - self.lastc.x(), c.y() - self.lastc.y()); self.lastc = c
        self.speed = 0.7 * self.speed + 0.3 * d / dt
        if d > 0: sh.last_input = now
        if self.speed > 2500 and not self.dragging: self.hunt_until = now + 1.0

        # typing speed -> kneading + overheat
        while sh.keys and now - sh.keys[0] > 2: sh.keys.popleft()
        cps = len(sh.keys) / 2
        if sh.keys: self.last_key_t = sh.keys[-1]
        self.typing = now - self.last_key_t < 0.4
        self.kb_show = now - self.last_key_t < 3
        target = 1.0 if cps >= 7 else 0.0
        self.heat += (target - self.heat) * min(1, dt * (1.5 if target else 0.6))

        # scrolling -> paper roll
        if sh.scroll:
            self.paper, self.paper_t, sh.scroll = min(9, self.paper + sh.scroll * 0.8), now, 0
        elif now - self.paper_t > 0.6:
            self.paper = max(0, self.paper - dt * 3)

        # petting decay, sleep, blink, growth
        self.pet_acc = max(0, self.pet_acc - 200 * dt)
        self.sleeping = now - sh.last_input > 90 and not (self.thinking or self.tidy)
        if now > self.next_blink:
            self.blink_until, self.next_blink = now + 0.15, now + random.uniform(2.5, 6)
        self.gsc += ((1.25 if now < self.grow_until else 1.0) - self.gsc) * min(1, dt * 6)
        if not self.dragging: self.tilt *= 0.8

        # AI-agent events from the local API
        if sh.agent_t != self.seen_agent_t:
            self.seen_agent_t = sh.agent_t
            self.thinking = sh.agent == "thinking"
            if sh.agent == "done":
                self.jump_until = now + 1.0
                self.say("All done!", 4)
        if self.thinking and now - sh.agent_t > 900: self.thinking = False
        if sh.say:
            (text, secs), sh.say = sh.say, None
            self.say(text, secs)

        # reminders
        if self.cfg["stretch_min"] and now - self.last_stretch > self.cfg["stretch_min"] * 60:
            self.last_stretch, self.grow_until = now, now + 7
            self.say(f"Stretch time, {name}! Reach up high~", 8)
        if self.cfg["water_min"] and now - self.last_water > self.cfg["water_min"] * 60:
            self.last_water = now
            self.say(f"Drink some water, {name}!", 7)
        for r in list(self.reminders):
            if now >= r[0]:
                self.reminders.remove(r); self.say(r[1], 10)
        if self.pomo and now >= self.pomo["end"]:
            p = self.pomo; p["focus_phase"] = not p["focus_phase"]
            p["end"] = now + 60 * (p["focus"] if p["focus_phase"] else p["brk"])
            if p["focus_phase"]:
                self.say(f"Focus time, {name}! You can do it!", 8)
            else:
                self.grow_until = now + 5
                self.say("Break time! Stretch a little~", 8)

        # movement: peek at the screen edge / walk around / tidy animation
        geo = self.screen().availableGeometry()
        if sh.peek_toggle:
            sh.peek_toggle = False
            self.set_cfg(peek=not self.cfg["peek"])
        if now > self.next_fs:
            self.next_fs = now + 1
            self.fs = bool(self.cfg["auto_peek"]) and is_fullscreen(int(self.winId()))
        self.peeking = ((self.cfg["peek"] or self.fs) and now > self.pop_until
                         and not self.tidy and not self.feed_start and not self.chase)
        if self.dragging:
            self.px, self.py, self.mode, self.home_x = self.x(), self.y(), "sit", self.x()
        elif self.chase is not None:
            self.update_chase(now, dt, geo)
        elif self.peeking:
            if self.mode == "walk": self.home_x = self.px
            self.mode = "sit"
            self.px += (geo.right() - 160 - self.px) * min(1, dt * 5)   # half the cat hides off-screen
        else:
            blocked = (self.typing or self.thinking or self.sleeping or self.tidy
                       or self.feed_start or now < self.pop_until)
            can_walk = not blocked
            if self.mode == "walk":
                if not can_walk or (self.px - self.walk_target) * self.facing >= 0:
                    self.mode, self.home_x = "sit", self.px
                    self.next_walk = now + random.uniform(20, 50)
                else:
                    self.px += 70 * dt * self.facing
            elif abs(self.px - self.home_x) > 1:
                self.px += (self.home_x - self.px) * min(1, dt * 5)     # slide back out of peek
            elif can_walk and self.cfg["walk"] and now > self.next_walk:
                tx = random.randint(geo.left(), max(geo.left(), geo.right() - W))
                if abs(tx - self.px) > 150:
                    self.mode, self.facing, self.walk_target = "walk", (1 if tx > self.px else -1), tx
                self.next_walk = now + random.uniform(20, 50)
        if not self.dragging: self.move(round(self.px), round(self.py))

        # feeding
        if self.feed_start:
            if now < self.bowl_until:
                elapsed = now - self.feed_start
                self.eating = elapsed < self.FEED_DUR
                self.food_level = max(0.0, 1 - elapsed / self.FEED_DUR)
            else:
                self.feed_start, self.eating, self.food_level = 0.0, False, 0.0

        # ball: simple physics, cat bats it every so often
        if self.ball:
            b = self.ball
            if now >= b["until"]:
                self.ball = None
            else:
                b["vx"] *= 0.985
                b["x"] += b["vx"] * dt * 60
                if b["x"] < 3 or b["x"] > 37:
                    b["x"] = clamp(b["x"], 3, 37); b["vx"] *= -0.7
                if now >= b["next_bat"] and abs(b["x"] - 20) < 14:
                    b["vx"] += random.uniform(-3, 3) + (2.5 if b["x"] < 20 else -2.5)
                    b["next_bat"] = now + random.uniform(0.8, 1.6)
                    self.swatting, self.swat_until = True, now + 0.3
                if now > getattr(self, "swat_until", 0): self.swatting = False

        # occasional unprompted playtime, if nothing else is going on
        if (self.cfg["play"] and now > self.next_play and self.mode != "walk"
                and not (self.tidy or self.feed_start or self.chase or self.ball
                         or self.sleeping or self.peeking or self.dragging)):
            self.start_play()

        if self.tidy: self.update_tidy(now)
        elif not self.ball: self.swatting = False
        self.update()

    # ---- drawing
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        now = time.time()

        # eye direction toward the cursor
        eye_c = self.mapToGlobal(QPoint(OX + CW * S // 2, H - (CH - 16) * S))
        cur = QCursor.pos()
        eye = tuple(1 if v > 40 else -1 if v < -40 else 0
                    for v in (cur.x() - eye_c.x(), cur.y() - eye_c.y()))

        jump = 0.0
        if now < self.jump_until:
            t = 1 - (self.jump_until - now)
            jump = -240 * t * (1 - t)
        purring = now < self.purr_until
        sx, sy = (0.86, 1.22) if self.dragging else (1.0, 1.0)
        if not self.dragging:
            sy += 0.03 * math.sin(now * 22) if purring else 0.015 * math.sin(now * 2.2)
        if now < self.hunt_until: sy *= 0.92
        g = self.gsc

        p.save()
        p.translate(OX + CW * S / 2, H + jump)
        p.rotate(self.tilt)
        p.scale(sx * g, sy * g); p.scale(S, S)
        p.translate(-CW / 2, -CH)
        if self.heat > 0.6: p.translate(random.choice((-0.5, 0, 0.5)), 0)
        if self.mode == "walk" or self.sleeping:
            if self.facing < 0: p.translate(CW, 0); p.scale(-1, 1)
            self.draw_side(p, now)
        else:
            self.draw_cat(p, now, eye)
        p.restore()

        if self.tidy: self.draw_tidy(p, now)

        # bubble text (transient > thinking > pinned note)
        head_top = H - (CH - 4) * S * g
        bottom = max(60, head_top - 6)
        if self.bubble and now < self.bubble[1]:
            self.draw_bubble(p, self.bubble[0], bottom, WHITE)
        elif self.thinking:
            self.draw_bubble(p, "thinking" + "." * (int(now * 2) % 4), bottom, WHITE)
        elif self.cfg["pinned"]:
            self.draw_bubble(p, self.cfg["pinned"], bottom, QColor("#fff3a8"))

        if self.pomo:   # floating pixel timer
            left = max(0, int(self.pomo["end"] - now))
            p.setFont(self.font_ui); p.setPen(QPen(OUT, 2))
            p.setBrush(QColor("#e8505b") if self.pomo["focus_phase"] else QColor("#4fb286"))
            p.drawRect(QRectF(OX + CW * S - 10, 230, 68, 26))
            p.setPen(WHITE)
            p.drawText(QRectF(OX + CW * S - 10, 230, 68, 26), TEXT_FLAGS,
                       f"{left // 60:02d}:{left % 60:02d}")

        if self.sleeping:
            p.setFont(QFont("Consolas", 14, QFont.Bold)); p.setPen(QColor(90, 80, 120))
            for i in range(3):
                zx = OX + 34 * S + i * 9
                if self.facing < 0: zx = W - zx - 10
                p.drawText(int(zx), int(H - (CH - 22) * S - ((now * 15 + i * 18) % 50)), "Z")
        p.end()

    def draw_bubble(self, p, text, bottom, fill):
        p.setFont(self.font_ui)
        r = QFontMetrics(self.font_ui).boundingRect(0, 0, 230, 200, TEXT_FLAGS, text)
        w, h = r.width() + 24, r.height() + 14
        x, y = (W - w) / 2, bottom - h - 8
        path = QPainterPath(); path.addRoundedRect(QRectF(x, y, w, h), 8, 8)
        tail = QPainterPath()
        tail.moveTo(W / 2 - 6, y + h - 1); tail.lineTo(W / 2 + 6, y + h - 1)
        tail.lineTo(W / 2, y + h + 8); tail.closeSubpath()
        p.setPen(QPen(OUT, 2)); p.setBrush(fill); p.drawPath(path.united(tail))
        p.setPen(OUT); p.drawText(QRectF(x + 12, y + 7, r.width(), r.height()), TEXT_FLAGS, text)

    def draw_cat(self, p, now, eye):
        cfg, sh = self.cfg, self.sh
        base = mix(QColor(cfg["color"]), QColor("#ff3b3b"), self.heat * 0.6)
        dark, belly = shade(base, 0.72), mix(base, CREAM, 0.6)
        purring, hunting = now < self.purr_until, (now < self.hunt_until or self.swatting)
        stretching = now < self.grow_until
        happy = purring or stretching or now < self.jump_until
        blinking = now < self.blink_until

        R, part, blit = mk(p)

        # tail + body
        sw = round(math.sin(now * (6 if purring else 2)))
        part(27, 28, 7, 3, base); part(32 + sw, 21, 3, 9, base)
        part(12, 25, 16, 12, base); R(16, 30, 8, 6, belly)
        if cfg["pattern"] == "tuxedo": R(15, 27, 10, 9, CREAM)

        # keyboard (appears while you type)
        if self.kb_show:
            part(5, 38, 30, 6, QColor("#4a4a5e"))
            for i in range(0, 28, 3):
                R(6 + i, 39, 2, 1, GREY); R(7 + i, 41, 2, 1, GREY)

        # scroll paper roll
        if self.paper > 0.3:
            L = max(1, int(self.paper))
            part(14, 36, 12, 3, WHITE); part(15, 39, 10, L, WHITE)
            for i in range(2, L, 3): R(16, 39 + i, 8, 1, QColor("#cfc8d8"))

        # ears + head
        for ex, ix in ((9, 10), (26, 28)):
            part(ex + 1 if ex == 9 else ex + 1, 4, 3, 3, base)
            part(ex, 6, 5, 5, base); R(ix, 8, 2, 3, PINK)
        part(8, 9, 24, 16, base)

        # markings
        pat = cfg["pattern"]
        if pat == "stripes":
            for x0, w0, h0 in ((16, 2, 3), (19, 2, 4), (22, 2, 3)): R(x0, 10, w0, h0, dark)
            for y0, w0 in ((15, 3), (18, 2)): R(8, y0, w0, 1, dark); R(32 - w0, y0, w0, 1, dark)
        elif pat == "patch":
            R(20, 9, 12, 9, dark)
        elif pat == "tuxedo":
            R(15, 19, 10, 6, CREAM)

        # cheeks, whiskers, eyes
        R(10, 20, 3, 2, QColor(255, 157, 181, 150)); R(27, 20, 3, 2, QColor(255, 157, 181, 150))
        R(3, 19, 5, 1, GREY); R(3, 22, 5, 1, GREY); R(32, 19, 5, 1, GREY); R(32, 22, 5, 1, GREY)
        for ex in (12, 23):
            if self.sleeping or blinking:
                R(ex, 17, 5, 1, DARK)
            elif happy:
                for dx, dy in ((0, 3), (1, 2), (2, 1), (3, 2), (4, 3)): R(ex + dx, 14 + dy, 1, 1, DARK)
            else:
                part(ex, 14, 5, 6, WHITE)
                if hunting:
                    R(ex, 14, 5, 6, DARK); R(ex + 1, 15, 1, 1, WHITE)
                else:
                    ox, oy = (1, -1) if self.thinking else eye
                    R(ex + 1 + ox, 15 + oy, 3, 4, DARK); R(ex + 1 + ox, 15 + oy, 1, 1, WHITE)

        # nose + mouth
        R(19, 20, 2, 1, PINK)
        if self.heat > 0.5:
            R(19, 22, 2, 2, QColor("#7a2030"))
        else:
            R(18, 21, 1, 1, OUT); R(21, 21, 1, 1, OUT); R(19, 22, 2, 1, OUT)
        if self.eating and int(now * 6) % 2 == 0:
            R(17, 21, 5, 3, OUT)   # mouth open wide while chewing

        # steam when typing too fast
        if self.heat > 0.5:
            for i in range(3):
                R(13 + i * 6 + (i % 2), 8 - ((now * 10 + i * 4) % 12), 2, 2, QColor(255, 255, 255, 210))

        # hearts while being petted
        if purring:
            for i, hx in enumerate((3, 32)):
                blit(HEART, hx, 3 - ((now * 8 + i * 7) % 12), PINK)

        # front paws
        lp = rp = lx = rx = 0
        if self.swatting:
            lp, lx = -7, -2
        elif hunting:
            if eye[0] >= 0: rp, rx = -7, 2
            else: lp, lx = -7, -2
        elif self.typing or self.paper > 0.3:
            ph = int(now * 9) % 2
            lp, rp = -2 * ph, -2 * (1 - ph)
        pc = CREAM if pat == "tuxedo" else base
        part(13 + lx, 34 + lp, 6, 4, pc); part(21 + rx, 34 + rp, 6, 4, pc)
        if stretching:
            part(3, 15, 5, 9, base); part(32, 15, 5, 9, base)

        # food bowl
        if self.feed_start:
            bx, by = 30, 34
            part(bx, by, 7, 3, QColor("#b8b8c4"))
            if self.food_level > 0:
                fh = max(1, round(2 * self.food_level))
                R(bx + 1, by + 3 - fh, 5, fh, QColor("#caa15a"))
            if self.eating and int(now * 6) % 2 == 0:
                for cx0, cy0 in ((bx - 1, by), (bx + 8, by + 1)):
                    R(cx0, cy0, 1, 1, QColor("#caa15a"))

        # ball toy
        if self.ball:
            bx = self.ball["x"]
            part(round(bx) - 2, 35, 4, 4, QColor("#e8505b"))
            R(round(bx) - 1, 36, 1, 1, QColor("#ffb3bb"))

    def draw_side(self, p, now):
        """Side view used for walking (legs cycle) and napping (loaf pose)."""
        cfg = self.cfg
        base = QColor(cfg["color"]); dark, belly = shade(base, 0.72), mix(base, CREAM, 0.6)
        far = shade(base, 0.82)
        R, part, _ = mk(p)
        pat = cfg["pattern"]; tux = pat == "tuxedo"

        def silhouette(blocks):
            """Draw several blocks as ONE merged shape: outlines first (so touching/
            overlapping blocks fuse with no seam), then each block's own fill on top."""
            for x, y, w, h, _ in blocks: R(x - 1, y - 1, w + 2, h + 2, OUT)
            for x, y, w, h, c in blocks: R(x, y, w, h, c)

        if self.sleeping:
            silhouette([(2, 30, 6, 3, base), (5, 22, 26, 11, base),
                        (25, 15, 4, 5, base), (31, 15, 4, 5, base), (24, 17, 13, 12, base)])
            R(9, 27, 16, 3, belly)
            R(35, 21, 2, 4, DARK); R(35, 22, 1, 1, WHITE)
            R(37, 25, 2, 1, PINK); R(35, 26, 2, 1, OUT)
            if pat == "stripes":
                for x0 in (10, 14, 18): R(x0, 23, 1, 3, dark)
            elif pat == "patch": R(9, 23, 9, 6, dark)
            elif tux: R(24, 21, 13, 8, CREAM)
            return

        moving = self.mode == "walk"
        ph, breathe = (now * 8, 0) if moving else (0.0, round(math.sin(now * 2)))
        BODY_Y, BODY_H = 21 - breathe, 11
        GROUND, LEGW = 38, 4
        HIP_Y = BODY_Y + BODY_H - 3     # thigh always overlaps into the body - never detaches
        THIGH_H, SHIN_H = 5, GROUND - (BODY_Y + BODY_H - 3 + 5)

        def leg(hip_x, phase, col):
            """Two-segment leg: the thigh is fixed to the hip (always fused into the body
            silhouette); only the shin swings from the knee, so it bends like a real leg
            instead of the whole leg sliding around as one loose block."""
            swing = math.sin(ph + phase) if moving else 0.0
            lift = max(0, math.cos(ph + phase)) if moving else 0.0
            knee_x = hip_x + round(2.2 * swing)
            knee_y = HIP_Y + THIGH_H - round(2 * lift)   # knee tucks up as the foot lifts off
            return (hip_x, HIP_Y, LEGW, THIGH_H, col), (knee_x, knee_y, LEGW, SHIN_H, col)

        # diagonal trot: near-fore+far-hind swing together, far-fore+near-hind swing opposite
        # all 4 hips sit within the torso (x=6..25) with clearance from both the tail and
        # the head, so the front leg attaches under the shoulder, not under the neck/head
        near_fore_t, near_fore_s = leg(17, 0, base)
        far_hind_t, far_hind_s = leg(10, 0, far)
        far_fore_t, far_fore_s = leg(14, math.pi, far)
        near_hind_t, near_hind_s = leg(7, math.pi, base)

        silhouette([
            (1, 11 - breathe, 5, 9, base), (2, 18 - breathe, 4, 11, base),   # tail (curl + base)
            far_hind_t, far_hind_s, far_fore_t, far_fore_s,
            (6, BODY_Y, 19, BODY_H, base),                                   # torso
            near_hind_t, near_hind_s, near_fore_t, near_fore_s,
            (24, 7 - breathe, 4, 5, base), (30, 7 - breathe, 4, 5, base),    # ears
            (23, 11 - breathe, 12, 12, base),                                # head
            (33, 17 - breathe, 3, 4, base),                                  # muzzle
        ])
        # re-fill any body pixels the far (background) legs' outline pass painted over
        R(6, BODY_Y, 19, BODY_H, base)
        R(9, BODY_Y + 6, 13, 3, belly)
        if pat == "stripes":
            for x0 in (9, 13, 17): R(x0, BODY_Y, 1, 3, dark)
        elif pat == "patch": R(9, BODY_Y, 9, 6, dark)
        elif tux:
            R(20, BODY_Y + 3, 5, 8, CREAM)
            for sx, sy, sw_, sh_, _c in (near_hind_s, near_fore_s):
                R(sx, sy + sh_ - 3, sw_, 3, CREAM)
        for ex, ix in ((24, 25), (30, 31)):
            R(ix, 8 - breathe, 2, 2, PINK)
        eye_y = 15 - breathe
        R(31, eye_y, 3, 4, DARK); R(31, eye_y, 1, 1, WHITE)
        R(34, 18 - breathe, 2, 2, PINK)
        R(31, 20 - breathe, 3, 1, OUT)
        for wy in (16, 19):
            R(36 - breathe, wy - breathe, 3, 1, GREY)

    def draw_file(self, p, x, y, cat, ext, scale):
        p.save(); p.translate(x + 14, y + 18); p.scale(scale, scale)
        p.setPen(QPen(OUT, 2)); p.setBrush(WHITE); p.drawRect(-14, -18, 28, 36)
        p.fillRect(-13, -17, 27, 8, QColor(CAT_COLORS.get(cat, "#aaaaaa")))
        p.setPen(OUT); p.drawText(QRectF(-14, -8, 28, 24), TEXT_FLAGS, ext.lstrip(".")[:4].upper())
        p.restore()

    def draw_tidy(self, p, now):
        """Files slide into a folder; the cat bats them. Big batches end in a page swirl."""
        td = self.tidy; items = td["items"]; n = len(items)
        T, sing = 1.4, min(len(items), 5)
        el = now - td["t0"]
        fx, fy, bounce, label = W - 50, H - 46, 0.0, items[0][1]
        p.setFont(QFont("Consolas", 7, QFont.Bold))
        if el < sing * T:
            i = min(int(el // T), sing - 1); u = (el - i * T) / T
            f, cat = items[i]; label = cat
            x0, x1, y = 30, fx - 34, H - 52
            if u < 0.3: self.draw_file(p, x0, y, cat, f.suffix, u / 0.3)
            elif u < 0.55: self.draw_file(p, x0, y, cat, f.suffix, 1)
            elif u < 0.9:
                k = (u - 0.55) / 0.35
                self.draw_file(p, x0 + (x1 - x0) * (1 - (1 - k) ** 2), y, cat, f.suffix, 1 - 0.3 * k)
            else:
                bounce = 8 * math.sin((u - 0.9) / 0.1 * math.pi)
        elif n > sing:
            fin, k = el - sing * T, min(n - sing, 10)
            cx, cy, grow = W / 2, H - 120, 0.0
            grow = min(1, fin / 0.4)
            for j in range(k):
                a = fin * 7 + j * 2 * math.pi / k
                ox, oy = cx + 95 * grow * math.cos(a), cy + 55 * grow * math.sin(a)
                if fin > 1.4:
                    m = min(1, (fin - 1.4) / 0.8)
                    if m >= 1: continue
                    ox, oy = ox + (fx + 20 - ox) * m, oy + (fy + 20 - oy) * m
                p.save(); p.translate(ox, oy); p.rotate(math.degrees(a))
                p.setPen(QPen(OUT, 1)); p.setBrush(WHITE); p.drawRect(-8, -10, 16, 20); p.restore()
            if fin > 2.1: bounce = 6 * abs(math.sin(fin * 20))
        p.setPen(QPen(OUT, 2)); p.setBrush(QColor("#ffcf4a"))
        p.drawRect(int(fx), int(fy + 6 - bounce), 44, 32); p.drawRect(int(fx), int(fy - bounce), 18, 8)
        p.setPen(OUT); p.drawText(QRectF(fx, fy + 12 - bounce, 44, 24), TEXT_FLAGS, label[:7])

    # ---- mouse interaction: drag, pet, right-click menu
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_off = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.lastx = e.globalPosition().x()
        elif e.button() == Qt.RightButton:
            self.show_menu(e.globalPosition().toPoint())

    def mouseMoveEvent(self, e):
        if self.dragging:
            gx = e.globalPosition().x()
            self.tilt = clamp(0.8 * self.tilt + -0.5 * (gx - self.lastx), -18, 18)
            self.lastx = gx
            self.move(e.globalPosition().toPoint() - self.drag_off)
            return
        pos = e.position()
        head = QRectF(OX + 8 * S, H - CH * S + 4 * S, 24 * S, 21 * S)
        if head.contains(pos) and self.last_mp is not None:
            self.pet_acc += abs(pos.x() - self.last_mp.x()) + abs(pos.y() - self.last_mp.y())
            if self.pet_acc > 80: self.purr_until = time.time() + 1.5
        self.last_mp = pos

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.dragging:
            self.dragging = False
            self.cfg["x"], self.cfg["y"] = self.x(), self.y()
            save_cfg(self.cfg)

    # ---- menu
    def show_menu(self, pos):
        m = QMenu(self)
        m.addAction("Tidy desktop (cat sorts files)...", lambda: self.start_tidy())
        m.addAction("Tidy another folder...", self.ask_tidy_other)
        m.addAction("Undo last tidy", self.undo_tidy)
        m.addSeparator()
        m.addAction(f"Feed {self.cfg['name']}", self.start_feed)
        play_menu = m.addMenu("Play")
        play_menu.addAction("Ball", lambda: self.start_play("ball"))
        play_menu.addAction("Butterfly", lambda: self.start_play("butterfly"))
        play_menu.addAction("Surprise me", lambda: self.start_play())
        self.add_toggle(m, "Let it play on its own sometimes", "play")
        m.addSeparator()
        self.add_toggle(m, "Peek mode (Ctrl+Alt+P)", "peek")
        self.add_toggle(m, "Auto-peek when an app is fullscreen (Windows)", "auto_peek")
        self.add_toggle(m, "Walk around", "walk")
        m.addSeparator()
        m.addAction("Preset: tuxedo cat", lambda: self.set_cfg(color="#26252e", pattern="tuxedo"))
        m.addAction("Set my name...", self.ask_name)
        m.addAction("Cat color...", self.ask_color)
        pm = m.addMenu("Pattern")
        for pt in ("stripes", "patch", "tuxedo", "none"):
            pm.addAction(pt, lambda checked=False, pt=pt: self.set_cfg(pattern=pt))
        m.addAction("Stretch reminder (minutes)...", lambda: self.ask_int("stretch_min", "Stretch every N minutes (0 = off)"))
        m.addAction("Water reminder (minutes)...", lambda: self.ask_int("water_min", "Water every N minutes (0 = off)"))
        m.addAction("Add one-time reminder...", self.ask_reminder)
        m.addAction("Pin a message...", self.ask_pin)
        m.addSeparator()
        m.addAction("Start Pomodoro...", self.ask_pomodoro)
        m.addAction("Stop Pomodoro", lambda: setattr(self, "pomo", None))
        m.addSeparator()
        m.addAction("Quit", self.quit_app)
        m.exec(pos)

    def set_cfg(self, **kw):
        self.cfg.update(kw); save_cfg(self.cfg)

    def ask_name(self):
        t, ok = QInputDialog.getText(self, "PixelCat", "What should I call you?", text=self.cfg["name"])
        if ok and t.strip():
            self.set_cfg(name=t.strip()); self.say(f"Nice to meet you, {t.strip()}!")

    def ask_color(self):
        c = QColorDialog.getColor(QColor(self.cfg["color"]), self, "Pick fur color")
        if c.isValid(): self.set_cfg(color=c.name())

    def ask_int(self, key, label):
        v, ok = QInputDialog.getInt(self, "PixelCat", label, self.cfg[key], 0, 600)
        if ok:
            self.set_cfg(**{key: v}); self.last_stretch = self.last_water = time.time()

    def ask_reminder(self):
        t, ok = QInputDialog.getText(self, "PixelCat", "Reminder message:")
        if not ok or not t.strip(): return
        m, ok = QInputDialog.getInt(self, "PixelCat", "In how many minutes?", 10, 1, 1440)
        if ok:
            self.reminders.append((time.time() + m * 60, t.strip()))
            self.say(f"OK! I'll remind you in {m} min.")

    def ask_pin(self):
        t, ok = QInputDialog.getText(self, "PixelCat", "Pinned message (empty = remove):", text=self.cfg["pinned"])
        if ok: self.set_cfg(pinned=t.strip()[:80])

    def ask_pomodoro(self):
        f, ok = QInputDialog.getInt(self, "PixelCat", "Focus minutes:", 25, 1, 180)
        if not ok: return
        b, ok = QInputDialog.getInt(self, "PixelCat", "Break minutes:", 5, 1, 60)
        if ok:
            self.pomo = dict(focus=f, brk=b, focus_phase=True, end=time.time() + f * 60)
            self.say(f"Focus time, {self.cfg['name']}! {f} minutes.")

    def add_toggle(self, m, text, key):
        a = m.addAction(text); a.setCheckable(True); a.setChecked(bool(self.cfg[key]))
        a.toggled.connect(lambda v, k=key: self.set_cfg(**{k: v}))

    def ask_tidy_other(self):
        d = QFileDialog.getExistingDirectory(self, "Folder to tidy")
        if d: self.start_tidy(d)

    def start_tidy(self, folder=None):
        if self.tidy: return
        folder = folder or default_desktop()
        if not folder:
            folder = QFileDialog.getExistingDirectory(self, "Folder to tidy")
            if not folder: return
        folder = pathlib.Path(folder)
        items = plan_tidy(folder)
        if not items:
            self.say("Nothing to tidy here!", 4); return
        cnt = {}
        for _, c in items: cnt[c] = cnt.get(c, 0) + 1
        ok = QMessageBox.question(
            self, "PixelCat",
            f"Sort {len(items)} files in\n{folder}\ninto category folders?\n\n"
            + ", ".join(f"{k}: {v}" for k, v in cnt.items())
            + "\n\nNothing is deleted or overwritten, and you can undo.")
        if ok != QMessageBox.Yes: return
        self.mode = "sit"
        self.tidy = dict(root=folder, items=items, i=0, t0=time.time(), moved=[], failed=0)

    def tidy_one(self, j):
        td = self.tidy; f, cat = td["items"][j]
        try: td["moved"].append(move_file(f, cat, td["root"]))
        except Exception: td["failed"] += 1

    def update_tidy(self, now):
        td = self.tidy; n = len(td["items"]); T, sing = 1.4, min(len(td["items"]), 5)
        el = now - td["t0"]; playing = el < sing * T
        self.swatting = playing and 0.3 < (el % T) / T < 0.6
        upto = min(sing, int(el // T)) if playing else sing
        while td["i"] < upto:
            self.tidy_one(td["i"]); td["i"] += 1
        if el >= sing * T + (2.2 if n > sing else 0):
            for j in range(sing, n): self.tidy_one(j)
            moved, failed = td["moved"], td["failed"]
            try:
                with open(UNDO_PATH, "w", encoding="utf-8") as f: json.dump(moved, f)
            except Exception: pass
            self.tidy, self.swatting, self.jump_until = None, False, now + 1.0
            self.say(f"Tidied {len(moved)} files!" + (f" ({failed} skipped)" if failed else ""), 7)

    def undo_tidy(self):
        try:
            with open(UNDO_PATH, encoding="utf-8") as f: log = json.load(f)
        except Exception:
            log = []
        n = 0
        for src, dst in reversed(log):
            s, d = pathlib.Path(src), pathlib.Path(dst)
            try:
                if d.exists():
                    shutil.move(str(d), str(unique_dest(s.parent, s.name))); n += 1
            except Exception: pass
        try:
            with open(UNDO_PATH, "w", encoding="utf-8") as f: json.dump([], f)
        except Exception: pass
        self.say(f"Put {n} files back!" if n else "Nothing to undo.", 5)

    def quit_app(self):
        self.cfg["x"], self.cfg["y"] = self.x(), self.y()
        save_cfg(self.cfg); QApplication.quit()


# ---------------------------------------------------------------- butterfly toy
BFLY_UP = [
    "..XX.XX..",
    ".XXXXXXX.",
    ".XXXXXXX.",
    ".XXXXXXX.",
    "..XX.XX..",
]
BFLY_DOWN = [
    ".........",
    "...XXX...",
    "...XXX...",
    "...XXX...",
    ".........",
]

class Butterfly(QWidget):
    """A small wandering toy the cat will chase. Created on demand by
    Cat.start_play(); closes itself when its lifespan ends or the cat
    "catches" it a few times, at which point the cat notices (via
    isVisible()) and goes back to normal on its own."""
    BW = BH = 48
    BS = 4   # screen pixels per butterfly-sprite pixel

    def __init__(self, cat):
        super().__init__()
        self.cat = cat
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint |
                            Qt.Tool | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(self.BW, self.BH)

        geo = cat.screen().availableGeometry()
        cx, cy = cat.x() + W / 2, cat.y()
        ang = random.uniform(0, 2 * math.pi)
        sx = clamp(cx + 170 * math.cos(ang), geo.left() + 10, geo.right() - self.BW - 10)
        sy = clamp(cy - 60 + 130 * math.sin(ang), geo.top() + 10, geo.bottom() - self.BH - 60)
        self.x_, self.y_ = float(sx), float(sy)
        self.vx, self.vy = random.uniform(-15, 15), random.uniform(-15, 15)
        self.target, self.next_target = None, 0.0
        now = time.time()
        self.spawn_t, self.lifespan = now, random.uniform(25, 45)
        self.flee_until, self.close_calls, self.phase = 0.0, 0, 0.0

        self.move(round(self.x_), round(self.y_))
        self.timer = QTimer(self); self.timer.timeout.connect(self.tick); self.timer.start(40)

    def spook(self, cat_center_x):
        """Called by the cat when it gets close - dart away, and after a
        few close calls, "get caught" and end the chase happily."""
        self.close_calls += 1
        if self.close_calls >= 3:
            self.cat.jump_until = time.time() + 1.0
            self.cat.say("Got it!", 3)
            self.close()
            return
        away = -1 if cat_center_x > self.x_ + self.BW / 2 else 1
        self.vx += away * random.uniform(90, 150)
        self.vy += random.uniform(-70, 70)
        self.flee_until = time.time() + 1.2

    def tick(self):
        now = time.time()
        dt = 0.04
        if not self.cat.isVisible() or now - self.spawn_t > self.lifespan:
            self.close(); return

        geo = self.screen().availableGeometry()
        fleeing = now < self.flee_until
        if not fleeing and now > self.next_target:
            self.next_target = now + random.uniform(1.5, 3.0)
            self.target = (random.uniform(geo.left() + 10, geo.right() - self.BW - 10),
                            random.uniform(geo.top() + 10, geo.bottom() - self.BH - 60))
        if self.target:
            tx, ty = self.target
            self.vx += (tx - self.x_) * 0.02
            self.vy += (ty - self.y_) * 0.02
        self.vx *= 0.90 if fleeing else 0.94
        self.vy *= 0.90 if fleeing else 0.94
        self.phase += dt * (16 if fleeing else 9)
        self.x_ += self.vx * dt + 6 * math.sin(self.phase * 0.7) * dt
        self.y_ += self.vy * dt + 10 * math.sin(self.phase) * dt
        self.x_ = clamp(self.x_, geo.left(), geo.right() - self.BW)
        self.y_ = clamp(self.y_, geo.top(), geo.bottom() - self.BH)
        self.move(round(self.x_), round(self.y_))
        self.update()

    def closeEvent(self, e):
        if self.cat.chase is self:
            self.cat.chase, self.cat.mode = None, "sit"
            self.cat.home_x = self.cat.px
        super().closeEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        p.scale(self.BS, self.BS)   # sprite-pixel units -> real screen pixels
        R, part, blit = mk(p)
        flap = math.sin(self.phase)
        rows = BFLY_UP if flap > 0 else BFLY_DOWN
        wing = mix(QColor("#ff9db5"), QColor("#a879e0"), (flap + 1) / 2)
        ox = (self.BW / self.BS - 9) / 2
        blit(rows, ox, 1, wing)
        R(ox + 4, 0, 1, 5, OUT)   # body
        p.end()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    cat = Cat(); cat.show()
    if "--smoke" in sys.argv:   # headless self-test: render a few frames then exit
        def shot():
            from PySide6.QtGui import QPixmap
            pm = QPixmap(cat.size()); pm.fill(QColor("#c8d6e5")); cat.render(pm)
            pm.save("frame.png"); app.quit()
        QTimer.singleShot(1500, shot)
    sys.exit(app.exec())