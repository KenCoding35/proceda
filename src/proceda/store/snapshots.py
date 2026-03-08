"""ABOUTME: Placeholder for session snapshot persistence.
ABOUTME: Will support saving and restoring run session state for resumption."""

from __future__ import annotations

from pathlib import Path


class SnapshotStore:
    """Placeholder for v2 session snapshot persistence."""

    def __init__(self, run_dir: Path) -> None:
        self._run_dir = run_dir

    async def save_snapshot(self, session_data: dict[str, object]) -> None:
        """Save a session snapshot (v2)."""
        raise NotImplementedError("Snapshots are a v2 feature")

    async def load_snapshot(self) -> dict[str, object] | None:
        """Load a session snapshot (v2)."""
        raise NotImplementedError("Snapshots are a v2 feature")
