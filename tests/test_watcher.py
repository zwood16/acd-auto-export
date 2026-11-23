"""Tests for FileWatcher (pure watchdog, no SDK)."""

import os
import threading
import time

import pytest

from acd_auto_export.watcher import FileWatcher

DEBOUNCE = 0.5


class Recorder:
    def __init__(self):
        self.calls = []
        self.event = threading.Event()

    def __call__(self, path):
        self.calls.append(path)
        self.event.set()

    def wait(self, timeout=5.0):
        return self.event.wait(timeout)


@pytest.fixture
def target(work_dir):
    p = work_dir / "proj.ACD"
    p.write_bytes(b"initial")
    return p


@pytest.fixture
def watching(target):
    rec = Recorder()
    watcher = FileWatcher(target, rec, debounce=DEBOUNCE)
    watcher.start()
    time.sleep(0.3)  # let the observer get ready
    try:
        yield rec
    finally:
        watcher.stop()


def _append(path, data=b"x"):
    with open(path, "ab") as f:
        f.write(data)


def test_in_place_write_triggers(target, watching):
    _append(target)
    assert watching.wait()
    assert os.path.normcase(watching.calls[0]) == os.path.normcase(os.path.abspath(target))


def test_atomic_replace_triggers(target, watching):
    tmp = target.with_name("proj.tmp")
    tmp.write_bytes(b"new contents")
    os.replace(tmp, target)
    assert watching.wait()
    assert os.path.normcase(watching.calls[0]) == os.path.normcase(os.path.abspath(target))


def test_other_files_do_not_trigger(target, watching):
    (target.parent / "other.ACD").write_bytes(b"a")
    (target.parent / "proj.ACD.bak").write_bytes(b"b")
    time.sleep(1.5)
    assert watching.calls == []


def test_burst_is_debounced(target, watching):
    for _ in range(5):
        _append(target)
        time.sleep(0.02)
    assert watching.wait()
    time.sleep(1.5)
    assert len(watching.calls) == 1


def test_separated_writes_trigger_twice(target, watching):
    _append(target)
    assert watching.wait()
    time.sleep(1.0)
    _append(target)
    deadline = time.monotonic() + 5.0
    while len(watching.calls) < 2 and time.monotonic() < deadline:
        time.sleep(0.05)
    assert len(watching.calls) == 2


def _start(target, callback):
    watcher = FileWatcher(target, callback, debounce=DEBOUNCE)
    watcher.start()
    time.sleep(0.3)
    return watcher


def test_slow_callback_single_change_fires_once(work_dir, target):
    calls = []

    def slow(path):
        calls.append(path)
        time.sleep(2.0)

    watcher = _start(target, slow)
    try:
        with open(target, "ab") as f:
            f.write(b"a" * 1000)
            f.flush()
            os.fsync(f.fileno())
            time.sleep(0.05)
            f.write(b"b" * 1000)
        deadline = time.monotonic() + 10.0
        while not calls and time.monotonic() < deadline:
            time.sleep(0.05)
        assert len(calls) == 1
        time.sleep(3.0)
        assert len(calls) == 1
    finally:
        watcher.stop()


def test_change_during_slow_callback_not_lost(work_dir, target):
    calls = []
    started = threading.Event()

    def slow(path):
        calls.append(path)
        started.set()
        time.sleep(2.0)

    watcher = _start(target, slow)
    try:
        _append(target, b"first")
        assert started.wait(10.0)
        _append(target, b"second change with different content")
        deadline = time.monotonic() + 15.0
        while len(calls) < 2 and time.monotonic() < deadline:
            time.sleep(0.05)
        assert len(calls) == 2
    finally:
        watcher.stop()


def test_start_missing_file_raises(tmp_path):
    watcher = FileWatcher(tmp_path / "missing.ACD", lambda p: None)
    with pytest.raises(FileNotFoundError):
        watcher.start()
    assert not watcher.is_watching


def test_context_manager(target):
    watcher = FileWatcher(target, lambda p: None, debounce=DEBOUNCE)
    assert not watcher.is_watching
    with watcher as w:
        assert w is watcher
        assert watcher.is_watching
    assert not watcher.is_watching
