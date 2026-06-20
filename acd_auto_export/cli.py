"""Command-line interface for acd-auto-export.

Provides CLI commands to convert Logix Designer .ACD files to L5X format,
either as a one-time conversion or by continuously watching a directory
for new/modified .ACD files.

Usage:
    acd-auto-export convert path/to/file.ACD [-o output_dir]
    acd-auto-export watch /path/to/dir [-o output_dir]
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

from acd_auto_export.watcher import FileWatcher


def _normalize_syspath() -> None:
    """Replace UNC paths in sys.path with drive-letter equivalents.

    When running from a mapped network drive on Windows, the exe launcher
    may populate sys.path with raw UNC paths (\\\\server\\share\\...).
    os.path.realpath() on a UNC path adds the \\\\?\\UNC\\ extended-length
    prefix, which the .NET CLR refuses when loading assemblies.
    Swapping those entries back to their drive-letter form (Z:\\...) keeps
    the paths short and CLR-compatible.
    """
    if sys.platform != "win32":
        return
    import ctypes

    unc_to_drive: dict[str, str] = {}
    buf = ctypes.create_unicode_buffer(512)
    buf_size = ctypes.c_ulong(512)
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        drive = f"{letter}:"
        buf_size.value = 512
        if ctypes.windll.mpr.WNetGetConnectionW(drive, buf, ctypes.byref(buf_size)) == 0:
            unc_to_drive[buf.value.lower()] = drive

    if not unc_to_drive:
        return

    for i, p in enumerate(sys.path):
        p_norm = p.replace("/", "\\")
        # Strip extended-length UNC prefix (\\?\UNC\server\share -> \\server\share)
        if p_norm.lower().startswith("\\\\?\\unc\\"):
            p_norm = "\\\\" + p_norm[8:]
        p_lower = p_norm.lower()
        for unc, drive in unc_to_drive.items():
            if p_lower.startswith(unc + "\\"):
                sys.path[i] = drive + p_norm[len(unc):]
                break
            elif p_lower == unc:
                sys.path[i] = drive
                break


def _run_convert(input_file: Path, output_dir: Path) -> None:
    """Run a single conversion synchronously.

    Args:
        input_file: Resolved path to the .ACD file to convert.
        output_dir: Resolved path to the directory where the L5X file
            will be saved.
    """
    from acd_auto_export.convert import convert_to_l5x
    print(f"Converting {input_file} -> {output_dir}")
    asyncio.run(convert_to_l5x(str(input_file), str(output_dir)))


def _on_file_change(path: str, output_dir: Path) -> None:
    """Callback invoked when a watched .ACD file is modified.

    Args:
        path: File system path of the changed file.
        output_dir: Resolved path to the output directory for the L5X file.
    """
    if not path.lower().endswith(".acd"):
        return
    from acd_auto_export.convert import convert_to_l5x
    print(f"Detected change: {path}")
    asyncio.run(convert_to_l5x(path, str(output_dir)))


def cmd_convert(args: argparse.Namespace) -> None:
    """Convert a single .ACD file to L5X format.

    Validates that the input file exists and has a .ACD extension,
    then runs the conversion asynchronously.

    Args:
        args: Parsed CLI arguments containing ``input`` (path to .ACD)
            and optional ``output`` (output directory).
    """
    input_file = Path(args.input)
    if not input_file.exists():
        print(f"Error: input file not found: {input_file}", file=sys.stderr)
        sys.exit(1)
    if not input_file.suffix.lower() == ".acd":
        print(f"Error: input file must be a .ACD file", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output) if args.output else input_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    _run_convert(input_file, output_dir)


def cmd_watch(args: argparse.Namespace) -> None:
    """Watch a single .ACD file for changes and auto-convert it.

    Uses ``FileWatcher`` to monitor the specified file. When the .ACD
    file is modified, it is automatically converted to L5X in the output
    directory.

    Args:
        args: Parsed CLI arguments containing ``file`` (path to .ACD file)
            and optional ``output`` (output directory).
    """
    input_file = Path(args.file)
    if not input_file.exists():
        print(f"Error: file not found: {input_file}", file=sys.stderr)
        sys.exit(1)
    if not input_file.suffix.lower() == ".acd":
        print(f"Error: watched file must be a .ACD file, got: {input_file.suffix}", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output) if args.output else input_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Watching {input_file} for changes. Output -> {output_dir}")
    print("Press Ctrl+C to stop.")

    watcher = FileWatcher(input_file, lambda path: _on_file_change(path, output_dir))
    watcher.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        watcher.stop()


def main() -> None:
    """Entry point for the acd-auto-export CLI.

    Parses command-line arguments and dispatches to the appropriate
    subcommand handler (``convert`` or ``watch``).
    """
    _normalize_syspath()
    parser = argparse.ArgumentParser(
        prog="acd-auto-export",
        description="Export Logix Designer .ACD files to L5X format.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # -- convert subcommand --
    convert_parser = subparsers.add_parser(
        "convert",
        help="Convert a single .ACD file to L5X.",
    )
    convert_parser.add_argument("input", help="Path to the .ACD input file.")
    convert_parser.add_argument(
        "-o", "--output",
        help="Output directory (default: same directory as input file).",
    )
    convert_parser.set_defaults(func=cmd_convert)

    # -- watch subcommand --
    watch_parser = subparsers.add_parser(
        "watch",
        help="Watch a directory and auto-convert any .ACD file that changes.",
    )
    watch_parser.add_argument(
        "file",
        help="Path to the .ACD file to watch for changes.",
    )
    watch_parser.add_argument(
        "-o", "--output",
        help="Output directory (default: same as watched directory).",
    )
    watch_parser.set_defaults(func=cmd_watch)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
