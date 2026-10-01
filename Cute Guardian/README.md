# PixelCat - free DIY desktop pixel cat

Run it on your own computer (Windows / macOS / Linux-X11). It will NOT work inside Kaggle/Colab because those have no desktop.

    pip install -r requirements.txt
    python pixelcat2.py

Right-click the cat for: feeding, name, fur color, pattern, tidy desktop, peek modes, walk toggle, stretch/water timers, one-time reminders, pinned note, Pomodoro, quit.
Settings are saved to ~/.pixelcat.json.

## What it does
| Reaction | Trigger |
|---|---|
| Eyes follow cursor | move the mouse |
| Mochi stretch + sway | drag the cat |
| Hunting (wide eyes, paw swipe) | move the mouse very fast |
| Purring + hearts | rub the mouse over its head |
| Keyboard kneading + keyboard | type |
| Overheat (red + steam) | type very fast |
| Paper roll | scroll |
| Sleeping (Z z z, loaf pose) | no input for 90 s |
| Walks around the screen on its own | automatic, every 20-50s (toggle in menu) |
| Eats from a little food bowl | menu -> "Feed the cat" |
| Chases a butterfly or bats a ball | appears at random intervals |
| **Tidy desktop**: walks over, sorts files into Images/Documents/Code/Media/Archives/Installers folders, bats them around a bit first | menu -> "Tidy desktop" (asks to confirm; nothing is deleted or overwritten; "Undo last tidy" puts everything back) |
| **Peek mode**: slides to the screen edge and mostly hides, so it stays out of the way | Ctrl+Alt+P, the menu toggle, or automatically when another app goes fullscreen (Windows only) |
| Peeks over the top edge of the screen | briefly after a Windows app window is minimized (toggle in menu) |
| Stretch / water reminders, Pomodoro, pinned note | menu |
| Thinking face / happy jump | local API (below) |

## Tidy desktop notes
- Only loose files directly in the chosen folder are touched; subfolders and their contents are left alone.
- Files are never deleted and never overwritten — a name clash gets " (1)", " (2)", etc.
- Shortcuts/.ini/.ds_store files are skipped, and at most 60 files are sorted per run (run it again for more).
- "Undo last tidy" reverses the most recent run by moving every file back to where it came from.

## AI-agent reactions (local API)
The cat listens on http://127.0.0.1:8765 (this machine only):

    curl "http://127.0.0.1:8765/status?state=thinking"
    curl "http://127.0.0.1:8765/status?state=done"
    curl "http://127.0.0.1:8765/say?text=Hello&secs=5"

Claude Code can call these through hooks in ~/.claude/settings.json
(check the current hooks docs at docs.claude.com if the format has changed):

    {
      "hooks": {
        "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "curl -s \"http://127.0.0.1:8765/status?state=thinking\""}]}],
        "Stop":             [{"hooks": [{"type": "command", "command": "curl -s \"http://127.0.0.1:8765/status?state=done\""}]}]
      }
    }

Any script can also call it, e.g. at the end of a long training run: `requests.get("http://127.0.0.1:8765/status?state=done")`.

## Windows install and release
- For development, install Python 3 and run `py -3 -m pip install -r requirements.txt`. `Start PixelCat.bat` starts `pixelcat2.py` without a console window.
- To build a public Windows installer, install [Inno Setup 6](https://jrsoftware.org/isinfo.php), then double-click `Build Windows Release.bat`. It builds the app with PyInstaller and creates `release\PixelCat-Setup-1.0.0.exe`.
- Share the installer, not just the executable in `dist\PixelCat`; the app folder contains required Qt and Python runtime files. Test the installer on a Windows PC that does not have Python installed.
- Setup creates a Start Menu shortcut, offers an unchecked option to start PixelCat when the user signs in, and can launch PixelCat after installation. The app can be uninstalled through Windows Settings > Apps.
- To publish a public GitHub release, upload the installer as a release asset. Unsigned installers may show a Microsoft Defender SmartScreen warning; code-signing with a trusted publisher certificate helps establish reputation. Choose and include a license before presenting the source as open source.
- Microsoft Store publication is separate: it requires Store developer enrollment, packaging, and certification. This installer workflow creates a normal downloadable Windows app, not a Store listing.
- To close PixelCat, right-click it and choose **Quit**. It saves its position and exits normally.

## Notes
- macOS: allow Terminal/Python under System Settings > Privacy & Security > Accessibility and Input Monitoring, or typing/scroll reactions won't work.
- PixelCat installs global keyboard and mouse listeners for its typing, scrolling, and hotkey reactions. It records key-press timestamps only, never key identities or text, and does not send input data over the network. Mention this behavior clearly on any public download page.
- Auto-peek-when-fullscreen (e.g. while you watch a video) only works on Windows; on macOS/Linux use Ctrl+Alt+P or the menu toggle instead.
- Minimize-peek detects minimized Windows application windows, not individual browser tabs. The top-edge peek is a screen animation; it cannot detect or appear on a physical laptop lid.
