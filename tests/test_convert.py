"""Conversion tests that need the Logix Designer SDK."""

import asyncio
import hashlib
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET

import pytest

from acd_auto_export.convert import convert_to_l5x

pytestmark = pytest.mark.sdk

LAST_RESULT_XPATH = (
    "Controller/Programs/Program[@Name='Camera']/Tags/Tag[@Name='lastResult']"
)


def _last_result_value(l5x_path):
    """Return the Decorated DataValue Value of Camera/lastResult, or None."""
    root = ET.parse(l5x_path).getroot()
    for program in root.iter("Program"):
        if program.get("Name") != "Camera":
            continue
        for tag in program.findall("Tags/Tag"):
            if tag.get("Name") != "lastResult":
                continue
            value = tag.find("Data[@Format='Decorated']/DataValue")
            return None if value is None else value.get("Value")
    return None


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_convert_produces_l5x(work_dir, acd_file):
    out = work_dir / "out"
    out.mkdir()
    result = asyncio.run(convert_to_l5x(str(acd_file), str(out)))

    expected = out / "example_1_sm.l5x"
    assert result == str(expected)
    assert expected.exists()
    root = ET.parse(expected).getroot()
    assert root.tag == "RSLogix5000Content"
    assert root.find("Controller").get("Name") == "example_1"


def test_convert_leaves_source_untouched(work_dir, acd_file):
    before_hash = _sha256(acd_file)
    before_names = {p.name for p in acd_file.parent.iterdir()}

    out = work_dir / "out"
    out.mkdir()
    asyncio.run(convert_to_l5x(str(acd_file), str(out)))

    assert _sha256(acd_file) == before_hash
    after_names = {p.name for p in acd_file.parent.iterdir()} - {"out"}
    assert after_names == before_names


async def _edit_in_place(acd_file):
    from logix_designer_sdk import LogixProject, OperationMode

    with await LogixProject.open_logix_project(str(acd_file)) as project:
        await project.set_tag_value_dint(
            LAST_RESULT_XPATH, OperationMode.OFFLINE, 4242
        )
        await project.save()


def test_watch_reexports_on_save(work_dir, acd_file):
    out = work_dir / "out"
    out.mkdir()
    l5x = out / "example_1_sm.l5x"

    proc = subprocess.Popen(
        [sys.executable, "-u", "-m", "acd_auto_export.cli",
         "watch", str(acd_file), "-o", str(out)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    lines = []

    def _reader():
        for line in proc.stdout:
            lines.append(line)

    threading.Thread(target=_reader, daemon=True).start()

    def _output():
        return "".join(lines)

    try:
        deadline = time.monotonic() + 30
        while "Watching" not in _output() and time.monotonic() < deadline:
            time.sleep(0.2)
        assert "Watching" in _output(), f"watcher did not start:\n{_output()}"
        assert not list(out.glob("*.l5x"))

        asyncio.run(_edit_in_place(acd_file))

        deadline = time.monotonic() + 180
        value = None
        while time.monotonic() < deadline:
            if l5x.exists():
                try:
                    value = _last_result_value(l5x)
                except ET.ParseError:
                    value = None
                if value == "4242":
                    break
            time.sleep(1)
        assert value == "4242", (
            f"re-exported L5X lastResult={value!r}\nwatcher output:\n{_output()}"
        )
        time.sleep(5)  # let any duplicate detection/export show up
        assert _output().count("Detected change") == 1, (
            f"expected exactly one 'Detected change'\nwatcher output:\n{_output()}"
        )
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
