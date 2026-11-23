"""Logix Designer SDK file open and save utility.

Allows opening a Logix Designer project and saving it as an L5X file. This is
based on an example from the Logix Designer SDK.

Usage as module:
    from acd_auto_export.convert import convert_to_l5x
    await convert_to_l5x("existing.ACD", "output_dir", detailed_l5x=False)

"""

import shutil
import tempfile
from pathlib import Path
from logix_designer_sdk import LogixProject


async def convert_to_l5x(
    existing_file_path: str,
    output_dir: str,
    detailed_l5x: bool = True,
) -> str:
    """Open a Logix Designer project and save it as an L5X file.

    Args:
        existing_file_path: Path to the source Logix Designer project file.
        output_dir: Directory where the L5X file should be saved.
        detailed_l5x: If True, include additional info when saving as L5X.

    Returns:
        The path to the saved L5X file.

    Raises:
        logix_designer_sdk.LogixError: If the project cannot be opened or saved.
    """
    source = Path(existing_file_path)
    output_path = Path(output_dir) / f"{source.stem}.l5x"

    # The SDK writes a .bak next to the project it opens/saves. Working on a
    # copy avoids locking or touching the user's file while Studio 5000 has it open.
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_copy = Path(tmp_dir) / source.name
        shutil.copy2(source, tmp_copy)

        with await LogixProject.open_logix_project(str(tmp_copy)) as project:
            await project.save_as(str(output_path), True, detailed_l5x)

    print(f"Project has been saved to: {output_path}")
    return str(output_path)
