"""
File watcher module for monitoring input files for changes.

Uses watchdog to efficiently watch for file modifications and invoke callbacks.

Usage:
    from acd_auto_export.watcher import FileWatcher

    def on_change(path):
        print(f"File changed: {path}")

    watcher = FileWatcher("input.L5X", on_change)
    watcher.start()
"""

import time
from pathlib import Path
from typing import Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class _FileChangeHandler(FileSystemEventHandler):
    """Internal watchdog event handler that invokes the user callback."""

    def __init__(self, target_path: Path, callback: Callable[[str], None]):
        super().__init__()
        self._target_path = target_path
        self._callback = callback
        self._last_event_time: float = 0
        self._debounce_seconds = 1  # debounce to avoid duplicate events

    def on_modified(self, event):
        if event.is_directory:
            return
        # Only react to the specific file being watched
        if Path(event.src_path).resolve() != self._target_path:
            return
        # Debounce: ignore events that happen too close together
        now = self._last_event_time
        if now == 0 or (now + self._debounce_seconds) < time.time():
            self._last_event_time = time.time()
            self._callback(event.src_path)


class FileWatcher:
    """Watches a file for changes and calls a callback when modified.

    Args:
        filepath: Path to the file to watch.
        callback: Function called with the file path when a change is detected.
        debounce: Seconds to wait between events to avoid duplicates (default 1.0).

    Example:
        def on_change(path):
            print(f"Changed: {path}")

        watcher = FileWatcher("input.L5X", on_change)
        watcher.start()
        # ... later ...
        watcher.stop()
    """

    def __init__(
        self,
        filepath: str | Path,
        callback: Callable[[str], None],
        debounce: float = 1.0,
    ):
        self._filepath = Path(filepath).resolve()
        self._callback = callback
        self._debounce = debounce
        self._observer: Optional[Observer] = None
        self._watch_dir: Optional[str] = None

    def start(self) -> None:
        """Start watching the file in a background thread."""
        if not self._filepath.exists():
            raise FileNotFoundError(f"File not found: {self._filepath}")

        watch_dir = str(self._filepath.parent)

        handler = _FileChangeHandler(self._filepath, self._callback)
        handler._debounce_seconds = self._debounce

        self._observer = Observer()
        # Watch the parent directory for changes to our specific file
        self._observer.schedule(handler, watch_dir, recursive=False)
        self._watch_dir = watch_dir

        self._observer.start()

    def stop(self) -> None:
        """Stop watching and clean up resources."""
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=2)
            self._observer = None


    @property
    def is_watching(self) -> bool:
        """Whether the watcher is currently active."""
        return self._observer is not None and self._observer.is_alive()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
