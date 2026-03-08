"""ABOUTME: Default keyboard bindings for the Proceda TUI.
ABOUTME: Maps keys to actions like quit, approve, reject, skip, and help."""

from __future__ import annotations

from textual.binding import Binding

# Default bindings for the Proceda TUI
DEFAULT_BINDINGS = [
    Binding("q", "quit", "Quit", show=True),
    Binding("a", "approve", "Approve", show=False),
    Binding("r", "reject", "Reject", show=False),
    Binding("s", "skip", "Skip", show=False),
    Binding("?", "help", "Help", show=True),
    Binding("escape", "dismiss", "Dismiss", show=False),
]
