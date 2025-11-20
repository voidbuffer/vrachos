"""IO operations."""

import os
import subprocess
import tempfile
import uuid
from pathlib import Path

from ._internal import get_editor


def random_temp_file_path(suffix: str = "") -> Path:
    """Get a random filepath in the temporary directory."""
    tmp = Path(tempfile.gettempdir())
    processed_suffix = suffix.lstrip(".")
    if processed_suffix == "":
        return tmp / f"{uuid.uuid4()}"
    else:
        return tmp / f"{uuid.uuid4()}.{processed_suffix}"


def open_editor(initial_text: str = "") -> str:
    """Open a text editor and return the edited text."""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".txt", encoding="utf-8"
    ) as f:
        f.write(initial_text)
        temp_file = f.name

    # Determine which editor to use
    editor = get_editor()
    if not editor:
        raise ValueError("Editor not found")

    try:
        # Open the editor
        subprocess.run(  # noqa: S603
            [*editor.split(), temp_file], shell=False, check=True
        )

        # Read the edited content
        with open(temp_file, encoding="utf-8") as f:
            result = f.read()

        return result

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Editor process failed: {e}")

    except FileNotFoundError as e:
        raise RuntimeError(f"Editor '{editor}' not found: {e}")

    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file):
            os.remove(temp_file)
