"""ABOUTME: Append-only JSONL event storage for skill runs with secret redaction.
ABOUTME: Manages run directories, writes events/metadata/artifacts, and reads logs for replay."""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Any

from proceda.events import RunEvent

_SECRET_PATTERN = re.compile(
    r"(api_key|secret|password|credential)"
    r"|^(token|auth)$"
    r"|_(token|key)$",
    re.IGNORECASE,
)


def _redact_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively redact values whose keys match secret patterns."""
    result: dict[str, Any] = {}
    for k, v in data.items():
        if _SECRET_PATTERN.search(k):
            result[k] = "**REDACTED**"
        elif isinstance(v, dict):
            result[k] = _redact_dict(v)
        elif isinstance(v, list):
            result[k] = [_redact_dict(item) if isinstance(item, dict) else item for item in v]
        else:
            result[k] = v
    return result


class RunDirectoryManager:
    """Creates and manages run directories."""

    def __init__(self, base_dir: str = ".proceda/runs") -> None:
        self._base_dir = Path(base_dir)

    def create_run_dir(self, run_id: str | None = None) -> Path:
        """Create a new run directory with timestamp and short ID."""
        now = datetime.now(UTC)
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        short_id = (run_id or uuid.uuid4().hex)[:8]
        dirname = f"{timestamp}_{short_id}"

        run_dir = self._base_dir / dirname
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def list_runs(self) -> list[Path]:
        """List all run directories, newest first."""
        if not self._base_dir.exists():
            return []
        dirs = [d for d in self._base_dir.iterdir() if d.is_dir()]
        return sorted(dirs, reverse=True)

    def find_run(self, run_id_or_path: str) -> Path | None:
        """Find a run directory by ID prefix or path."""
        path = Path(run_id_or_path)
        if path.is_dir():
            return path

        # Search by ID prefix
        for run_dir in self.list_runs():
            if run_id_or_path in run_dir.name:
                return run_dir
        return None


class EventLogWriter:
    """Writes events as JSONL to a run directory."""

    def __init__(self, run_dir: Path, redact_secrets: bool = False) -> None:
        self._run_dir = run_dir
        self._events_path = run_dir / "events.jsonl"
        self._artifacts_dir = run_dir / "artifacts"
        self._file: IO[str] | None = None
        self._redact = redact_secrets

    async def open(self) -> None:
        self._file = open(self._events_path, "a", encoding="utf-8")

    async def handle(self, event: RunEvent) -> None:
        """Write an event to the log (implements EventSink protocol)."""
        if self._file is None:
            await self.open()
        if self._redact:
            event = RunEvent(
                id=event.id,
                timestamp=event.timestamp,
                run_id=event.run_id,
                type=event.type,
                payload=_redact_dict(event.payload),
            )
        line = event.to_json()
        self._file.write(line + "\n")  # type: ignore
        self._file.flush()  # type: ignore

    async def close(self) -> None:
        if self._file:
            self._file.close()
            self._file = None

    def write_metadata(self, metadata: dict[str, Any]) -> None:
        """Write run metadata to metadata.json."""
        meta_path = self._run_dir / "metadata.json"
        data = _redact_dict(metadata) if self._redact else metadata
        meta_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def write_summary(self, summary: str) -> None:
        """Write run summary to summary.txt."""
        summary_path = self._run_dir / "summary.txt"
        summary_path.write_text(summary, encoding="utf-8")

    def write_artifact(self, name: str, content: str, content_type: str = "text/plain") -> Path:
        """Store an artifact file."""
        self._artifacts_dir.mkdir(exist_ok=True)
        artifact_path = self._artifacts_dir / name
        artifact_path.write_text(content, encoding="utf-8")
        return artifact_path


class EventLogReader:
    """Reads events from a run directory for replay."""

    def __init__(self, run_dir: Path) -> None:
        self._run_dir = run_dir
        self._events_path = run_dir / "events.jsonl"
        self._metadata_path = run_dir / "metadata.json"
        self._summary_path = run_dir / "summary.txt"

    def read_metadata(self) -> dict[str, Any]:
        """Read run metadata."""
        if not self._metadata_path.exists():
            return {}
        result: dict[str, Any] = json.loads(self._metadata_path.read_text(encoding="utf-8"))
        return result

    def read_summary(self) -> str | None:
        """Read run summary."""
        if not self._summary_path.exists():
            return None
        return self._summary_path.read_text(encoding="utf-8")

    def read_events(self) -> list[RunEvent]:
        """Read all events from the log."""
        if not self._events_path.exists():
            return []
        events = []
        with open(self._events_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(RunEvent.from_json(line))
        return events

    def iter_events(self) -> Iterator[RunEvent]:
        """Iterate events lazily for large logs."""
        if not self._events_path.exists():
            return
        with open(self._events_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield RunEvent.from_json(line)

    @property
    def exists(self) -> bool:
        return self._events_path.exists()
