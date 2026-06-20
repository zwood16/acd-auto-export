# Studio 5000 Auto-Export

> Automatically export `.ACD` files to `.L5X` (XML-based) format.

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)
- Logix Designer SDK (installed with Studio 5000; not redistributable)

## Installation

**1. Update Logix Designer SDK wheel path**

The SDK ships with Studio 5000 and cannot be redistributed. Copy the wheel from your Studio 5000 installation into a `vendor/` folder at the root of this repo:

```
vendor/
  logix_designer_sdk-2.0.1-py3-none-any.whl
```

The default wheel location is:

```
C:/Users/Public/Documents/Studio 5000/Logix Designer SDK/python/
```

The `vendor/` directory is gitignored so the wheel will not be committed.

**2. Install dependencies**

```bash
uv sync
```

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
