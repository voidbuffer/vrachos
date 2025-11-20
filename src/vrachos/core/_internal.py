"""Internal private utilities."""

import os
import shutil
import sys


def get_editor() -> str | None:
    """Get the best available text editor for the current OS."""
    # Check environment variables first
    if editor := os.environ.get("EDITOR"):
        editor_cmd = editor.split()[0]  # Get just the executable name
        if shutil.which(editor_cmd):
            return editor

    if editor := os.environ.get("VISUAL"):
        editor_cmd = editor.split()[0]
        if shutil.which(editor_cmd):
            return editor

    # Define editors by OS
    editors_by_os = {
        "linux": ["nano", "vim", "vi", "gedit", "kate"],
        "win32": ["notepad.exe", "notepad++"],
        "darwin": ["nano", "vim", "vi"],
    }
    common_editors = ["nano", "vim", "vi"]

    # Get editors
    editors = editors_by_os.get(sys.platform, [])
    editors += common_editors

    # Find first available editor
    for editor in editors:
        if shutil.which(editor):
            return editor

    return None
