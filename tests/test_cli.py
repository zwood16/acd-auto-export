"""CLI argument validation tests (no SDK needed)."""

import sys

import pytest

from acd_auto_export import cli


def _run(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["acd-auto-export", *args])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    return exc.value.code


def test_convert_missing_file(monkeypatch, capsys, tmp_path):
    missing = tmp_path / "nope.ACD"
    assert _run(monkeypatch, "convert", str(missing)) == 1
    err = capsys.readouterr().err
    assert "input file not found" in err
    assert str(missing) in err


def test_convert_non_acd_file(monkeypatch, capsys, tmp_path):
    txt = tmp_path / "file.txt"
    txt.write_text("x")
    assert _run(monkeypatch, "convert", str(txt)) == 1
    assert "must be a .ACD file" in capsys.readouterr().err


def test_watch_missing_file(monkeypatch, capsys, tmp_path):
    missing = tmp_path / "nope.ACD"
    assert _run(monkeypatch, "watch", str(missing)) == 1
    err = capsys.readouterr().err
    assert "file not found" in err
    assert str(missing) in err


def test_watch_non_acd_file(monkeypatch, capsys, tmp_path):
    txt = tmp_path / "file.txt"
    txt.write_text("x")
    assert _run(monkeypatch, "watch", str(txt)) == 1
    assert "must be a .ACD file" in capsys.readouterr().err


def test_convert_no_args(monkeypatch, capsys):
    assert _run(monkeypatch, "convert") == 2
