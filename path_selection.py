"""Windows-friendly path selection helpers for manual pipeline scripts.

The helpers prefer explicit command-line arguments, then existing default
paths, then a tkinter dialog, then command-line input. They use only the Python
standard library and never import ANSYS, Fluent, Tecplot, SpaceClaim, or torch.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable


class PathSelectionError(RuntimeError):
    """Raised when a required path cannot be resolved."""


def is_interactive_session() -> bool:
    """Return whether stdin appears interactive enough for text fallback."""
    return bool(getattr(sys.stdin, "isatty", lambda: False)())


def _normalize(path_value: str | Path | None) -> Path | None:
    if path_value is None:
        return None
    text = str(path_value).strip().strip('"')
    if not text:
        return None
    return Path(text).expanduser()


def _ask_with_tk(title: str, dialog: str, **kwargs: object) -> Path | None:
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        if dialog == "directory":
            selected = filedialog.askdirectory(title=title)
        elif dialog == "open_file":
            selected = filedialog.askopenfilename(title=title, **kwargs)
        elif dialog == "save_file":
            selected = filedialog.asksaveasfilename(title=title, **kwargs)
        else:
            selected = ""
        root.destroy()
        return _normalize(selected)
    except Exception:
        return None


def _ask_with_input(prompt: str) -> Path | None:
    if not is_interactive_session():
        return None
    try:
        return _normalize(input(f"{prompt}: "))
    except EOFError:
        return None


def _resolve(
    *,
    arg_value: str | Path | None,
    default: str | Path | None,
    prompt: str,
    no_dialog: bool,
    validator: Callable[[Path], bool],
    dialog: str,
    create: bool = False,
    filetypes: list[tuple[str, str]] | None = None,
    defaultextension: str | None = None,
) -> Path:
    arg_path = _normalize(arg_value)
    if arg_path is not None:
        if create:
            if arg_path.suffix:
                arg_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                arg_path.mkdir(parents=True, exist_ok=True)
        if validator(arg_path):
            return arg_path
        raise PathSelectionError(f"Provided path is not valid: {arg_path}")

    default_path = _normalize(default)
    if default_path is not None and validator(default_path):
        return default_path

    if no_dialog:
        default_note = f" Default path was not usable: {default_path}" if default_path else ""
        raise PathSelectionError(f"{prompt} is required.{default_note}")

    selected = _ask_with_tk(
        prompt,
        dialog,
        filetypes=filetypes or (),
        defaultextension=defaultextension or "",
    )
    if selected is None:
        selected = _ask_with_input(prompt)
    if selected is None:
        raise PathSelectionError(f"No path selected for: {prompt}")

    if create:
        if selected.suffix and dialog == "save_file":
            selected.parent.mkdir(parents=True, exist_ok=True)
        else:
            selected.mkdir(parents=True, exist_ok=True)
    if not validator(selected):
        raise PathSelectionError(f"Selected path is not valid: {selected}")
    return selected


def choose_existing_file(
    prompt: str,
    *,
    arg_value: str | Path | None = None,
    default: str | Path | None = None,
    no_dialog: bool = False,
    filetypes: list[tuple[str, str]] | None = None,
) -> Path:
    """Choose an existing input file."""
    return _resolve(
        arg_value=arg_value,
        default=default,
        prompt=prompt,
        no_dialog=no_dialog,
        validator=lambda path: path.is_file(),
        dialog="open_file",
        filetypes=filetypes,
    )


def choose_existing_directory(
    prompt: str,
    *,
    arg_value: str | Path | None = None,
    default: str | Path | None = None,
    no_dialog: bool = False,
) -> Path:
    """Choose an existing input directory."""
    return _resolve(
        arg_value=arg_value,
        default=default,
        prompt=prompt,
        no_dialog=no_dialog,
        validator=lambda path: path.is_dir(),
        dialog="directory",
    )


def choose_output_directory(
    prompt: str,
    *,
    arg_value: str | Path | None = None,
    default: str | Path | None = None,
    no_dialog: bool = False,
) -> Path:
    """Choose an output directory, creating command-line selections if needed."""
    return _resolve(
        arg_value=arg_value,
        default=default,
        prompt=prompt,
        no_dialog=no_dialog,
        validator=lambda path: path.is_dir(),
        dialog="directory",
        create=True,
    )


def choose_save_file(
    prompt: str,
    *,
    arg_value: str | Path | None = None,
    default: str | Path | None = None,
    no_dialog: bool = False,
    filetypes: list[tuple[str, str]] | None = None,
    defaultextension: str | None = None,
) -> Path:
    """Choose an output file path, creating command-line parent folders."""
    return _resolve(
        arg_value=arg_value,
        default=default,
        prompt=prompt,
        no_dialog=no_dialog,
        validator=lambda path: path.parent.is_dir(),
        dialog="save_file",
        create=True,
        filetypes=filetypes,
        defaultextension=defaultextension,
    )


def fail_with_path_error(error: Exception) -> int:
    """Print a clear path-selection error and return a failure exit code."""
    print(f"Path selection error: {error}", file=sys.stderr)
    return 2
