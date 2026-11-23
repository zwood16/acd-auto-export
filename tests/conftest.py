"""Shared pytest fixtures.

Tests that touch the filesystem run twice: once in a local temp directory and
once on a network share. The network run is skipped unless the environment
variable ``ACD_AUTO_EXPORT_NETWORK_DIR`` points at a writable directory on a
mapped drive, e.g.::

    $env:ACD_AUTO_EXPORT_NETWORK_DIR = "Z:\\"

Tests marked ``sdk`` need Windows, the Logix Designer SDK and a running
LdSdkService. They are skipped automatically when the SDK can't be imported.
"""

import os
import shutil
import sys
import uuid
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURE_ACD = FIXTURES / "example_1_sm.ACD"
NETWORK_ENV = "ACD_AUTO_EXPORT_NETWORK_DIR"


def _sdk_available() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import logix_designer_sdk  # noqa: F401
    except Exception:
        return False
    return True


def pytest_collection_modifyitems(config, items):
    if _sdk_available():
        return
    skip = pytest.mark.skip(reason="Logix Designer SDK not available")
    for item in items:
        if "sdk" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(params=["local", "network"])
def work_dir(request, tmp_path):
    """An empty directory, either local or on the network share."""
    if request.param == "local":
        yield tmp_path
        return
    root = os.environ.get(NETWORK_ENV)
    if not root:
        pytest.skip(f"set {NETWORK_ENV} to a network share directory to run network tests")
    d = Path(root) / f"acd-auto-export-test-{uuid.uuid4().hex[:8]}"
    d.mkdir(parents=True)
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def acd_file(work_dir):
    """A fresh copy of the fixture .ACD project inside ``work_dir``."""
    dest = work_dir / FIXTURE_ACD.name
    shutil.copy2(FIXTURE_ACD, dest)
    return dest
