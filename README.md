# Studio 5000 Auto-Export

> Automatically export `.ACD` files to `.L5X` (XML-based) format.

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)
- Logix Designer SDK
  - As a result, this project only works on Windows

## Installation

**1. Clone this repo**
```bash
git clone https://github.com/zwood16/acd-auto-export.git
```

**2. Install dependencies**

```bash
uv sync
```

The `pyproject.toml` is configured to pull the Logix Designer SDK from the default install location found at:

`C:\Users\Public\Documents\Studio 5000\Logix Designer SDK\python`

If you encounter issues with this, copy the `.whl` file into this directory and call `uv add name-of-file.whl` to update the dependency.

**3. (Optional) Install as a global tool**

To run `acd-auto-export` from any directory without `uv run`, install it as a uv tool from the repo root:

```bash
uv tool install .
```

This puts `acd-auto-export.exe` in uv's tool bin directory (`%USERPROFILE%\.local\bin` by default). If that directory isn't on your `PATH`, run `uv tool update-shell` and open a new terminal. You can then drop the `uv run` prefix from the commands below, e.g. `acd-auto-export convert path\to\file.ACD`.

After pulling changes to this repo, reinstall to pick them up:

```bash
uv tool install . --reinstall
```

> [!NOTE]
> `uv tool install` doesn't use `uv.lock`, so it may install newer versions of dependencies (e.g. watchdog) than the ones the tests run against.

## Usage

### Convert a single file

Convert an `.ACD` file to `.L5X` once:

```bash
uv run acd-auto-export convert path/to/file.ACD
```

Write the output to a specific directory with `-o`:

```bash
uv run acd-auto-export convert path/to/file.ACD -o path/to/output/
```

### Watch a file for changes

Watch an `.ACD` file and automatically re-export it whenever it is saved:

```bash
uv run acd-auto-export watch path/to/file.ACD
```

With a specific output directory:

```bash
uv run acd-auto-export watch path/to/file.ACD -o path/to/output/
```

Press `Ctrl+C` to stop watching.

## Known limitations

- **UNC paths are not supported.** The Logix Designer SDK mangles paths like `\\server\share\project.ACD` (it drops a leading backslash and fails to find the file). Map the share to a drive letter and use that instead, e.g. `Z:\project.ACD`. Mapped drives are tested for both `convert` and `watch`.
- **Keep this repo on a local disk.** Earlier versions included a workaround for running the tool from a mapped network drive; it has been removed. Network locations for the `.ACD` and output files are fine.
- Each conversion opens the project in the SDK, which takes roughly 10-20 seconds for a small project.
- `watch` handles both in-place saves and atomic saves (temp file renamed over the `.ACD`). It is tested with SDK saves; saving from the Studio 5000 GUI has not been covered by the automated tests.

## Testing

```bash
uv run pytest
```

- Tests marked `sdk` need the Logix Designer SDK and a running `LdSdkService`. They are skipped automatically when the SDK can't be imported. Run only the fast tests with `uv run pytest -m "not sdk"`.
- File-based tests run in a local temp directory. To also run them on a network share, point `ACD_AUTO_EXPORT_NETWORK_DIR` at a writable directory on a mapped drive. Each test creates and removes its own subfolder.

  ```powershell
  $env:ACD_AUTO_EXPORT_NETWORK_DIR = "Z:\"
  uv run pytest
  ```

- The test project is `tests/fixtures/example_1_sm.ACD` (Logix Designer v37).
