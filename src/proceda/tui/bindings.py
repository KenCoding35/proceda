"""TUI key bindings configuration."""

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
