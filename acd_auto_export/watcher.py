"""
File watcher module for monitoring input files for changes.

Uses watchdog to efficiently watch for file modifications and invoke callbacks.
Handles in-place writes as well as atomic saves (write a temp file, then rename
it over the target).

Usage:
    from acd_auto_export.watcher import FileWatcher

    def on_change(path):
        print(f"File changed: {path}")

    watcher = FileWatcher("input.L5X", on_change)
    watcher.start()
"""

import os
import time
from pathlib import Path
from typing import Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


def _normalize(path: str | Path) -> str:
    """Absolute, case-normalized path string used for comparisons.

    Deliberately avoids Path.resolve() so mapped drives are not turned into UNC paths.
    """
    return os.path.normcase(os.path.abspath(os.fspath(path)))


_POLL_INTERVAL = 0.1  # seconds between stat() polls while waiting for the file to settle
_MAX_SETTLE = 30.0  # give up waiting for the file to stop changing after this long


def _signature(path: str) -> Optional[tuple[int, int]]:
    """(mtime_ns, size) of the file, or None if it cannot be stat'ed (e.g. mid-rename)."""
    try:
        st = os.stat(path)
    except OSError:
        return None
    return (st.st_mtime_ns, st.st_size)


class _FileChangeHandler(FileSystemEventHandler):
    """Internal watchdog event handler that invokes the user callback.

    On a matching event it waits for the file to settle (signature unchanged for
    `debounce` seconds), then fires the callback unless the settled signature equals
    the one recorded at the last fire. Watchdog dispatches events serially, so events
    queued while a slow callback runs are handled afterwards; the signature check
    drops those duplicates, while a real change made meanwhile still fires.
    """

    def __init__(
        self,
        target_path: str,
        callback: Callable[[str], None],
        debounce: float = 1.0,
        initial_signature: Optional[tuple[int, int]] = None,
    ):
        super().__init__()
        self._target_path = target_path  # absolute, original case (passed to callback)
        self._target_key = _normalize(target_path)  # used for comparisons
        self._callback = callback
        self._debounce = debounce
        self._last_signature = initial_signature

    def _wait_for_settle(self) -> Optional[tuple[int, int]]:
        """Poll until the signature is unchanged (and the file exists) for `debounce` s."""
        start = time.monotonic()
        sig = _signature(self._target_path)
        stable_since = start
        while True:
            time.sleep(_POLL_INTERVAL)
            now = time.monotonic()
            new = _signature(self._target_path)
            if new != sig:
                sig = new
                stable_since = now
            elif sig is not None and (now - stable_since) >= self._debounce:
                return sig
            if now - start >= _MAX_SETTLE:
                return sig

    def _handle(self, path) -> None:
        if _normalize(path) != self._target_key:
            return
        sig = self._wait_for_settle()
        if sig is None or sig == self._last_signature:
            return
        self._last_signature = sig
        self._callback(self._target_path)

    def on_modified(self, event):
        if event.is_directory:
            return
        self._handle(event.src_path)

    def on_created(self, event):
        if event.is_directory:
            return
        self._handle(event.src_path)

    def on_moved(self, event):
        if event.is_directory:
            return
        # Atomic saves rename a temp file over the target; the target is the destination.
        self._handle(event.dest_path)


class FileWatcher:
    """Watches a file for changes and calls a callback when it is modified,
    created, or replaced (renamed over).

    Args:
        filepath: Path to the file to watch.
        callback: Function called with the file path (str) when a change is detected.
        debounce: How long (seconds) the file must be unchanged (same mtime and size)
            before the callback fires (default 1.0). A change that leaves the file
            identical to the last one reported does not fire again.

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
        self._filepath = os.path.abspath(os.fspath(filepath))
        self._callback = callback
        self._debounce = debounce
        self._observer: Optional[Observer] = None

    def start(self) -> None:
        """Start watching the file in a background thread.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        if not os.path.exists(self._filepath):
            raise FileNotFoundError(f"File not found: {self._filepath}")

        handler = _FileChangeHandler(
            self._filepath,
            self._callback,
            self._debounce,
            initial_signature=_signature(self._filepath),
        )

        self._observer = Observer()
        # Watch the parent directory for changes to our specific file
        self._observer.schedule(handler, os.path.dirname(self._filepath), recursive=False)

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
