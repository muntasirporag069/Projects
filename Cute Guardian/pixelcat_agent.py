#!/usr/bin/env python3
"""
PixelCat Local Agent
--------------------
Voice-first local assistant for the PixelCat desktop pet.

Architecture:
    F8 -> microphone capture -> faster-whisper -> safe local tools
                                                  |
                                                  +-> PixelCat localhost API

Environment variables:
    PIXELCAT_PORT  default: 8765
    WHISPER_MODEL  default: base.en
    TTS_RATE       default: 175
    PIXELCAT_VOICE_THRESHOLD  default: 0.012
    PIXELCAT_INPUT_DEVICE     default: system default microphone
    PIXELCAT_STARTUP_SHORTCUT optional per-user Windows Startup shortcut

Install:
    pip install -r requirements-pixelcat-agent.txt

"""

import datetime as dt
import ipaddress
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path

import requests

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

try:
    import sounddevice as sd
    import numpy as np
except ImportError:
    sd = None
    np = None

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

try:
    from pynput import keyboard
except ImportError:
    keyboard = None

PIXELCAT_PORT = int(os.getenv("PIXELCAT_PORT", "8765"))
WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "base.en")
SAMPLE_RATE = 16000
VOICE_THRESHOLD = float(os.getenv("PIXELCAT_VOICE_THRESHOLD", "0.012"))
VOICE_SILENCE_SECONDS = 0.65
VOICE_MAX_SECONDS = 12
VOICE_START_TIMEOUT = 8
AUDIO_BLOCK_SECONDS = 0.1
VOICE_PRE_ROLL_SECONDS = 0.25

def pixelcat(path, **params):
    """Send an event to the running PixelCat UI."""
    try:
        q = urllib.parse.urlencode(params)
        url = f"http://127.0.0.1:{PIXELCAT_PORT}/{path}?{q}"
        requests.get(url, timeout=0.7)
    except Exception:
        pass


def cat_state(state):
    pixelcat("status", state=state)


def cat_say(text, secs=5):
    text = str(text).strip()
    if not text:
        return
    pixelcat("say", text=text[:80], secs=secs)


class PixelCatAgent:
    def __init__(self):
        self.running = True
        self.recording = False
        self.recording_lock = threading.Lock()
        self.whisper = None
        self.tts = None
        self.reminders = []
        self._start_menu_shortcuts = None

    # ---------- speech ----------

    def load_whisper(self):
        if self.whisper is not None:
            return
        if WhisperModel is None:
            raise RuntimeError(
                "faster-whisper is not installed. Run: pip install faster-whisper"
            )

        print(f"[voice] Loading Whisper model: {WHISPER_MODEL_NAME}")
        # CPU is the portable default. If you have an NVIDIA GPU, change
        # device="cuda", compute_type="float16".
        self.whisper = WhisperModel(
            WHISPER_MODEL_NAME,
            device="cpu",
            compute_type="int8",
        )
        print("[voice] Whisper ready")

    def warm_up_whisper(self):
        if np is None:
            raise RuntimeError(
                "sounddevice/numpy are not installed. Run the requirements file."
            )
        self.load_whisper()
        silence = np.zeros(int(SAMPLE_RATE * 0.5), dtype=np.float32)
        segments, _ = self.whisper.transcribe(
            silence,
            language="en",
            beam_size=1,
            vad_filter=False,
        )
        list(segments)

    def input_device(self):
        devices = sd.query_devices()
        requested = os.getenv("PIXELCAT_INPUT_DEVICE", "").strip()
        if requested:
            if requested.isdigit():
                index = int(requested)
                device = sd.query_devices(index, "input")
                if device["max_input_channels"] > 0:
                    return index
                raise RuntimeError(f"Audio device {index} has no input channels.")
            for index, device in enumerate(devices):
                if (requested.casefold() in device["name"].casefold()
                        and device["max_input_channels"] > 0):
                    return index
            raise RuntimeError(f"No microphone matches PIXELCAT_INPUT_DEVICE={requested!r}.")

        default_device = sd.default.device[0]
        if default_device is not None and default_device >= 0:
            default_info = sd.query_devices(default_device, "input")
            if (default_info["max_input_channels"] > 0
                    and "stereo mix" not in default_info["name"].casefold()):
                return default_device

        for index, device in enumerate(devices):
            name = device["name"].casefold()
            if (device["max_input_channels"] > 0
                    and "stereo mix" not in name
                    and ("microphone" in name or "mic " in name or "mic in" in name)):
                return index

        return default_device

    def record_utterance(self):
        if sd is None or np is None:
            raise RuntimeError(
                "sounddevice/numpy are not installed. Run the requirements file."
            )

        device = self.input_device()
        device_name = sd.query_devices(device, "input")["name"]
        block_size = int(SAMPLE_RATE * AUDIO_BLOCK_SECONDS)
        pre_roll = []
        pre_roll_blocks = max(1, round(VOICE_PRE_ROLL_SECONDS / AUDIO_BLOCK_SECONDS))
        utterance = None
        silence_seconds = 0.0
        utterance_seconds = 0.0
        started_at = time.monotonic()

        print(f"[voice] Listening for one command on: {device_name}")
        cat_state("thinking")

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=block_size,
            device=device,
        ) as stream:
            while self.running and self.recording:
                if (utterance is None
                        and time.monotonic() - started_at >= VOICE_START_TIMEOUT):
                    print("[voice] No speech detected; press F8 to try again.")
                    cat_say("I didn't hear a command.", 4)
                    return None

                frames, _ = stream.read(block_size)
                frame = frames[:, 0].copy()
                level = float(np.sqrt(np.mean(frame * frame)))

                if utterance is None:
                    pre_roll.append(frame)
                    pre_roll = pre_roll[-pre_roll_blocks:]
                    if level < VOICE_THRESHOLD:
                        continue
                    utterance = list(pre_roll)
                    utterance_seconds = len(utterance) * AUDIO_BLOCK_SECONDS
                    silence_seconds = 0.0
                    cat_state("thinking")
                    print("[voice] Speech detected; listening for the end of the phrase...")
                    continue

                utterance.append(frame)
                utterance_seconds += AUDIO_BLOCK_SECONDS
                if level < VOICE_THRESHOLD:
                    silence_seconds += AUDIO_BLOCK_SECONDS
                else:
                    silence_seconds = 0.0

                if (silence_seconds >= VOICE_SILENCE_SECONDS
                        or utterance_seconds >= VOICE_MAX_SECONDS):
                    return np.concatenate(utterance)

        return None

    def one_shot(self):
        try:
            audio = self.record_utterance()
            if audio is None:
                return
            text = self.transcribe(audio)
            if text:
                self.handle(text)
            else:
                print("[voice] No speech recognized; press F8 to try again.")
                cat_say("I didn't catch that. Press F8 to try again.", 4)
        except Exception as e:
            print(f"[voice] Command failed: {e}")
        finally:
            with self.recording_lock:
                self.recording = False
            cat_state("idle")

    def transcribe(self, audio):
        self.load_whisper()
        segments, _ = self.whisper.transcribe(
            audio,
            language="en",
            vad_filter=True,
            beam_size=1,
            condition_on_previous_text=False,
        )
        text = " ".join(s.text.strip() for s in segments).strip()
        return text

    def speak(self, text):
        text = re.sub(r"\s+", " ", str(text)).strip()
        if not text:
            return

        print(f"PixelCat: {text}")
        cat_say(text, min(8, max(3, len(text) // 12)))
        cat_state("done")

        if pyttsx3 and self.tts is None:
            try:
                self.tts = pyttsx3.init()
                self.tts.setProperty("rate", int(os.getenv("TTS_RATE", "175")))
            except Exception:
                self.tts = None

        if self.tts:
            try:
                self.tts.say(text)
                self.tts.runAndWait()
                return
            except Exception as e:
                print("[tts]", e)

    # ---------- tools ----------

    def tool(self, obj):
        if not isinstance(obj, dict):
            return None

        name = obj.get("tool")

        if name == "open_folder":
            return self.open_folder(str(obj.get("path", "")))

        if name == "create_folder":
            return self.create_folder(
                str(obj.get("name", "")),
                str(obj.get("location", "desktop")),
            )

        if name == "open_url":
            url = str(obj.get("url", "")).strip()
            if not re.match(r"^https?://", url, re.I):
                return "I can only open normal HTTP or HTTPS web addresses."
            webbrowser.open(url)
            return "Opened the website."

        if name == "web_search":
            q = str(obj.get("query", "")).strip()
            if not q:
                return "I need something to search for."
            webbrowser.open(
                "https://www.google.com/search?q=" +
                urllib.parse.quote_plus(q)
            )
            return f"I opened a search for {q}."

        if name == "open_app":
            app = str(obj.get("app", "")).lower().strip()
            return self.open_app(app)

        if name == "get_time":
            now = dt.datetime.now().strftime("%I:%M %p")
            return f"It is {now}."

        if name == "system_info":
            return (
                f"You are running {platform.system()} {platform.release()} "
                f"on {platform.machine()}."
            )

        if name == "reminder":
            try:
                minutes = max(1, min(1440, int(obj.get("minutes", 10))))
            except Exception:
                minutes = 10
            message = str(obj.get("message", "Reminder"))[:200]
            due = time.time() + minutes * 60
            self.reminders.append((due, message))
            threading.Thread(
                target=self._wait_reminder,
                args=(due, message),
                daemon=True,
            ).start()
            return f"Okay. I'll remind you in {minutes} minutes."

        return "I don't have that tool."

    def open_app(self, app):
        app = re.sub(r"\s+", " ", app.casefold().strip())
        app = {
            "windows terminal": "terminal",
            "command prompt": "cmd",
            "file explorer": "explorer",
            "edge": "microsoft edge",
        }.get(app, app)
        system = platform.system().lower()

        allowed = {
            "windows": {
                "calculator": ["calc.exe"],
                "notepad": ["notepad.exe"],
                "browser": None,
                "explorer": ["explorer.exe"],
                "terminal": ["wt.exe"],
                "powershell": ["powershell.exe"],
                "cmd": ["cmd.exe"],
            },
            "darwin": {
                "calculator": ["open", "-a", "Calculator"],
                "notepad": ["open", "-a", "TextEdit"],
                "browser": None,
                "explorer": ["open", "."],
                "terminal": ["open", "-a", "Terminal"],
            },
            "linux": {
                "calculator": ["gnome-calculator"],
                "notepad": ["gedit"],
                "browser": None,
                "explorer": ["xdg-open", "."],
                "terminal": ["x-terminal-emulator"],
            },
        }

        key = "windows" if system == "windows" else "darwin" if system == "darwin" else "linux"
        apps = allowed[key]

        if app == "terminal":
            return self.open_terminal()

        if app not in apps:
            return self.open_installed_app(app)

        if app == "browser":
            webbrowser.open("https://www.google.com")
            return "Opened your browser."

        try:
            subprocess.Popen(apps[app])
            return f"Opened {app}."
        except Exception as e:
            print("[app]", e)
            return f"I couldn't open {app}."

    def open_terminal(self):
        for candidate in ("wt.exe", "powershell.exe", "cmd.exe"):
            executable = shutil.which(candidate)
            if not executable:
                continue
            try:
                subprocess.Popen([executable])
                return f"Opened terminal using {candidate}."
            except OSError as e:
                print(f"[app] Could not start {candidate}: {e}")
        return "I couldn't find Windows Terminal, PowerShell, or Command Prompt."

    def folder_path(self, target):
        aliases = {
            "home": Path.home(),
            "desktop": Path.home() / "Desktop",
            "documents": Path.home() / "Documents",
            "downloads": Path.home() / "Downloads",
            "pictures": Path.home() / "Pictures",
            "music": Path.home() / "Music",
            "videos": Path.home() / "Videos",
        }
        key = re.sub(r"\s+", " ", target.strip().casefold())
        if key.startswith("my "):
            key = key[3:]
        if key in aliases:
            return aliases[key]
        path = Path(os.path.expandvars(os.path.expanduser(target)))
        if not path.is_absolute():
            path = Path.home() / path
        return path.resolve()

    def open_folder(self, target):
        path = self.folder_path(target)
        if not path.is_dir():
            return f"Folder not found: {path}"
        try:
            if sys.platform == "win32":
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
            return f"Opened folder: {path}"
        except Exception as e:
            print("[folder]", e)
            return f"I couldn't open folder: {path}"

    def create_folder(self, name, location="desktop"):
        name = name.strip().strip("\"'")
        if (not name or name in {".", ".."}
                or "/" in name or "\\" in name):
            return "Use a simple folder name without a path."

        home = Path.home().resolve()
        parent = self.folder_path(location).resolve()
        try:
            parent.relative_to(home)
        except ValueError:
            return "For safety, I can only create folders inside your user folder."

        path = parent / name
        try:
            existed = path.exists()
            path.mkdir(parents=True, exist_ok=True)
            return f"Folder already exists: {path}" if existed else f"Created folder: {path}"
        except OSError as e:
            print("[folder]", e)
            return f"I couldn't create folder: {path}"

    def open_installed_app(self, app):
        if not re.fullmatch(r"[\w .&()-]{1,80}", app, flags=re.UNICODE):
            return "Use the installed app's name, without a command or file path."

        if self._start_menu_shortcuts is None:
            roots = (
                Path(os.getenv("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
                Path(os.getenv("PROGRAMDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
            )
            self._start_menu_shortcuts = {}
            for root in roots:
                if not root.is_dir():
                    continue
                try:
                    for shortcut in root.rglob("*.lnk"):
                        key = re.sub(r"[^a-z0-9]+", "", shortcut.stem.casefold())
                        self._start_menu_shortcuts.setdefault(key, shortcut)
                except OSError:
                    continue

        key = re.sub(r"[^a-z0-9]+", "", app.casefold())
        shortcut = self._start_menu_shortcuts.get(key)
        if shortcut is not None:
            try:
                os.startfile(str(shortcut))
                return f"Opened {app}."
            except Exception as e:
                print("[app]", e)
                return f"I couldn't open {app}."

        executable = shutil.which(app)
        if executable:
            try:
                subprocess.Popen([executable])
                return f"Opened {app}."
            except Exception as e:
                print("[app]", e)
                return f"I couldn't open {app}."
        return f"I couldn't find an installed app named {app}."

    def _wait_reminder(self, due, message):
        wait = max(0, due - time.time())
        time.sleep(wait)
        if self.running:
            cat_say(message, 10)
            self.speak(message)

    # ---------- command pipeline ----------

    def command_to_tool(self, text):
        command = re.sub(r"\s+", " ", text).strip().rstrip(" .,!?")
        create_match = re.match(
            r"^(?:please\s+)?(?:create|make)\s+(?:a\s+)?(?:new\s+)?folder(?:\s+(?:named|called))?\s+(.+?)(?:\s+(?:on|in|under)\s+(?:my\s+)?(desktop|documents|downloads|home))?$",
            command,
            re.IGNORECASE,
        )
        if create_match:
            return {
                "tool": "create_folder",
                "name": create_match.group(1).strip(),
                "location": create_match.group(2) or "desktop",
            }

        search_match = re.match(
            r"^(?:please\s+)?(?:can you\s+)?(?:search(?:\s+(?:the\s+)?web)?(?:\s+for)?|google|look\s+up|find)\s+(.+)$",
            command,
            re.IGNORECASE,
        )
        if search_match:
            query = search_match.group(1).strip().rstrip(" .,!?")
            return {"tool": "web_search", "query": query} if query else None

        website_match = re.match(r"^(?:please\s+)?go to\s+(.+)$", command, re.IGNORECASE)
        if website_match:
            url = self.normalize_website_url(website_match.group(1))
            return {"tool": "open_url", "url": url} if url else None

        launch_match = re.match(r"^(?:please\s+)?(?:launch|start)\s+(.+)$", command, re.IGNORECASE)
        if launch_match:
            target = launch_match.group(1).strip().strip(".?! ")
            target = re.sub(r"^(?:the|my)\s+", "", target, flags=re.IGNORECASE)
            target = re.sub(r"^(?:the\s+)?(?:app|application)\s+(?:named\s+)?", "", target, flags=re.IGNORECASE)
            target = re.sub(r"\s+(?:app|application)$", "", target, flags=re.IGNORECASE).strip()
            normalized_target = re.sub(r"[^a-z0-9]+", " ", target.casefold()).strip()
            app_aliases = {
                "text editor": "notepad",
                "text edit": "notepad",
                "text editer": "notepad",
                "texted it or": "notepad",
                "note pad": "notepad",
                "notepad": "notepad",
            }
            target = app_aliases.get(normalized_target, target)
            return {"tool": "open_app", "app": target} if target else None

        folder_match = re.match(
            r"^(?:please\s+)?open\s+(?:(?:the\s+)?(?:folder|directory)\s+)?(.+)$",
            command,
            re.IGNORECASE,
        )
        if folder_match:
            target = folder_match.group(1).strip().strip(".?! ")
            target = re.sub(r"^(?:the|my)\s+", "", target, flags=re.IGNORECASE)
            target = re.sub(r"^(?:named|called|at)\s+", "", target, flags=re.IGNORECASE)
            target = re.sub(r"\s+(?:folder|directory)$", "", target, flags=re.IGNORECASE).strip()
            return {"tool": "open_folder", "path": target} if target else None

        return None

    @staticmethod
    def normalize_website_url(target):
        target = target.strip().strip("<>\"'").rstrip(".,!?; ")
        target = re.sub(r"\s+dot\s+", ".", target, flags=re.IGNORECASE)
        target = re.sub(r"\s+slash\s+", "/", target, flags=re.IGNORECASE)
        target = re.sub(r"^the\s+", "", target, flags=re.IGNORECASE)
        aliases = {
            "google": "https://www.google.com",
            "youtube": "https://www.youtube.com",
            "gmail": "https://mail.google.com",
            "googledrive": "https://drive.google.com",
            "googledocs": "https://docs.google.com",
            "googlemaps": "https://maps.google.com",
            "googlemeet": "https://meet.google.com",
            "googlephotos": "https://photos.google.com",
            "googlecalendar": "https://calendar.google.com",
            "googletranslate": "https://translate.google.com",
            "bing": "https://www.bing.com",
            "copilot": "https://copilot.microsoft.com",
            "microsoftcopilot": "https://copilot.microsoft.com",
            "chatgpt": "https://chatgpt.com",
            "openai": "https://openai.com",
            "claude": "https://claude.ai",
            "gemini": "https://gemini.google.com",
            "perplexity": "https://www.perplexity.ai",
            "facebook": "https://www.facebook.com",
            "messenger": "https://www.messenger.com",
            "instagram": "https://www.instagram.com",
            "threads": "https://www.threads.net",
            "twitter": "https://x.com",
            "x": "https://x.com",
            "tiktok": "https://www.tiktok.com",
            "snapchat": "https://www.snapchat.com",
            "reddit": "https://www.reddit.com",
            "pinterest": "https://www.pinterest.com",
            "linkedin": "https://www.linkedin.com",
            "discord": "https://discord.com",
            "whatsapp": "https://www.whatsapp.com",
            "telegram": "https://telegram.org",
            "twitch": "https://www.twitch.tv",
            "bluesky": "https://bsky.app",
            "wikipedia": "https://www.wikipedia.org",
            "netflix": "https://www.netflix.com",
            "disneyplus": "https://www.disneyplus.com",
            "primevideo": "https://www.primevideo.com",
            "spotify": "https://open.spotify.com",
            "applemusic": "https://music.apple.com",
            "amazon": "https://www.amazon.com",
            "ebay": "https://www.ebay.com",
            "etsy": "https://www.etsy.com",
            "walmart": "https://www.walmart.com",
            "target": "https://www.target.com",
            "aliexpress": "https://www.aliexpress.com",
            "github": "https://github.com",
            "gitlab": "https://gitlab.com",
            "stackoverflow": "https://stackoverflow.com",
            "npm": "https://www.npmjs.com",
            "pypi": "https://pypi.org",
            "mdn": "https://developer.mozilla.org",
            "bbc": "https://www.bbc.com",
            "cnn": "https://www.cnn.com",
            "nytimes": "https://www.nytimes.com",
            "outlook": "https://outlook.live.com",
            "onedrive": "https://onedrive.live.com",
            "one drive": "https://onedrive.live.com",
            "microsoft365": "https://www.microsoft365.com",
            "zoom": "https://zoom.us",
            "slack": "https://slack.com",
            "notion": "https://www.notion.so",
            "canva": "https://www.canva.com",
            "dropbox": "https://www.dropbox.com",
            "adobe": "https://www.adobe.com",
        }
        alias_key = re.sub(r"[^a-z0-9]+", "", target.casefold())
        target = aliases.get(alias_key, target)
        if not target:
            return None
        if not re.match(r"^https?://", target, re.IGNORECASE):
            target = "https://" + target

        try:
            parsed = urllib.parse.urlsplit(target)
            hostname = parsed.hostname
            if (parsed.scheme.lower() not in {"http", "https"}
                    or not hostname or parsed.username or parsed.password):
                return None
            parsed.port
        except ValueError:
            return None

        try:
            ipaddress.ip_address(hostname)
        except ValueError:
            try:
                ascii_host = hostname.encode("idna").decode("ascii").rstrip(".")
            except UnicodeError:
                return None
            labels = ascii_host.split(".")
            if len(labels) < 2 or any(
                not re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", label)
                for label in labels
            ):
                return None

        return urllib.parse.urlunsplit(parsed)

    def handle(self, text):
        text = text.strip()
        if not text:
            return

        print(f"\nYou: {text}")
        cat_say(f"Heard: {text}", 4)
        cat_state("thinking")
        command = self.command_to_tool(text)
        if command is None:
            print("No supported action recognized. Try 'open calculator' or 'search for ...'.")
            cat_say("I heard that, but didn't recognize the command.", 5)
            cat_state("idle")
            return

        result = self.tool(command)
        print(result or "Command completed.")
        cat_state("idle")

    def run(self):
        print()
        print("======================================")
        print("        PixelCat Local Agent")
        print("======================================")
        print(f"Whisper: {WHISPER_MODEL_NAME}")
        print("Commands: open/search the web, launch apps, and manage folders.")
        print("Loading and warming up speech recognition...")
        print("======================================")
        print()

        try:
            self.warm_up_whisper()
            if keyboard is None:
                raise RuntimeError("pynput is required for the F8 hotkey; install the agent requirements.")

            def on_press(key):
                if key != keyboard.Key.f8:
                    return
                with self.recording_lock:
                    if self.recording or not self.running:
                        return
                    self.recording = True
                threading.Thread(target=self.one_shot, daemon=True).start()

            listener = keyboard.Listener(on_press=on_press)
            listener.start()
            print("Ready. Microphone is idle; press F8 to give one command. Press Ctrl+C to quit.")
            while self.running and listener.is_alive():
                time.sleep(0.25)
        except KeyboardInterrupt:
            self.running = False
            cat_state("idle")
            print("\nBye~")
        except Exception as e:
            self.running = False
            cat_state("idle")
            print(f"[agent] {e}")


if __name__ == "__main__":
    PixelCatAgent().run()