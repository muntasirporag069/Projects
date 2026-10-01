# PixelCat Local Voice Agent

The agent listens continuously, transcribes speech locally with faster-whisper,
and runs a small set of safe desktop actions. It does not use Ollama or send
audio to a cloud service.

## Setup

Install the agent dependencies:

```powershell
py -m pip install -r requirements-pixelcat-agent.txt
```

Start PixelCat's desktop pet separately with `py pixelcat2.py`, then start the
voice agent:

```powershell
py pixelcat_agent.py
```

On first startup, faster-whisper downloads the default `base.en` model if it is
not cached. The agent warms up the model and waits for F8; the microphone only
opens while capturing one command. Press F8, speak after the listening message,
then wait for the silence-based recording to finish. Press Ctrl+C to stop it.

## Voice commands

- "Launch calculator" or "launch notepad"
- "Launch [installed app name]" for apps with a Start Menu shortcut
- "Launch terminal" (tries Windows Terminal, then PowerShell, then Command Prompt)
- "Launch terminal" (tries Windows Terminal, then PowerShell, then Command Prompt)
- "Open folder Downloads" or "Open folder C:\\Users\\you\\Documents"
- "Create a folder called Projects on Desktop"
- "Go to example.com" or "go to docs.python.org/3"
- "Go to youtube" or "go to copilot" for common site shortcuts
- "Search for [query]" to open browser search results

Created folders are restricted to locations within your Windows user folder.
Relative folder names resolve from your user folder. The agent does not run
arbitrary shell commands. Use "launch" for applications, "open folder" for
folders, and "go to" for websites so the actions do not conflict.

## Start At Sign-In

The agent can be added to the current Windows user's Startup folder with a
shortcut to `pythonw.exe` and this script. It loads Whisper at sign-in, but
keeps the microphone idle until F8 is pressed.

## Settings

The defaults use the English `base.en` model and the Windows default input
device. Override them in PowerShell before starting the agent:

```powershell
$env:WHISPER_MODEL = "tiny.en"
$env:PIXELCAT_INPUT_DEVICE = "Microphone"
$env:PIXELCAT_VOICE_THRESHOLD = "0.012"
py pixelcat_agent.py
```

Use a higher voice threshold if background noise triggers commands; lower it
if normal speech is not detected. `PIXELCAT_INPUT_DEVICE` may be a device name
substring or sounddevice's numeric input-device index.