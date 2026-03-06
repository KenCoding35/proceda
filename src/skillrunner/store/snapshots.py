"""Snapshot support (v2 placeholder)."""

from __future__ import annotations

from pathlib import Path


class SnapshotStore:
    """Placeholder for v2 session snapshot persistence."""

    def __init__(self, run_dir: Path) -> None:
        self._run_dir = run_dir

    async def save_snapshot(self, session_data: dict) -> None:
        """Save a session snapshot (v2)."""
        raise NotImplementedError("Snapshots are a v2 feature")

    async def load_snapshot(self) -> dict | None:
        """Load a session snapshot (v2)."""
        raise NotImplementedError("Snapshots are a v2 feature")
