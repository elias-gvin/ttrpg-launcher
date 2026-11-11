"""Copy text to the desktop clipboard using whichever tool is installed."""

from __future__ import annotations

import os
import shutil
import subprocess


class ClipboardError(Exception):
    pass


def _candidates() -> list[list[str]]:
    wayland = [["wl-copy"]]
    x11 = [["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]]
    return wayland + x11 if os.environ.get("WAYLAND_DISPLAY") else x11 + wayland


def find_tool() -> list[str] | None:
    for command in _candidates():
        if shutil.which(command[0]):
            return command
    return None


def copy(text: str) -> None:
    command = find_tool()
    if command is None:
        raise ClipboardError(
            "No clipboard tool is installed. Install wl-clipboard (Wayland) or "
            "xclip (X11), or select the text above by hand."
        )
    try:
        # These tools stay in the background to serve the clipboard, so their
        # output must not be captured or this call would never return.
        subprocess.run(
            command,
            input=text.encode(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ClipboardError(f"Copying with {command[0]} failed: {error}") from None
