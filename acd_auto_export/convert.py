"""Logix Designer SDK file open and save utility.

Allows opening a Logix Designer project and saving it to a new location. This is
based on an example from the Logix Designer SDK.

Usage as module:
    from convert import convert_project
    await convert_project("existing.L5K", "output.L5X", detailed_l5x=False)

"""

import asyncio
import shutil
import sys
import tempfile
from pathlib import Path
from logix_designer_sdk import LogixProject, StdOutEventLogger


async def _convert_project(
    existing_file_path: str,
    new_file_path: str,
    detailed_l5x: bool = False,
) -> str:
    """Internal function to open a Logix Designer project and save it to a new file.

    Args:
        existing_file_path: Path to the source Logix Designer project file.
        new_file_path: Path where the converted project should be saved.
        detailed_l5x: If True, include additional info when saving as L5X.

    Returns:
        The path to the saved project file.

    Raises:
        logix_designer_sdk.LogixError: If the project cannot be opened or saved.
    """
    project = await LogixProject.open_logix_project(
        existing_file_path, StdOutEventLogger()
    )
    await project.save_as(new_file_path, True, detailed_l5x)

    print(f"Project has been saved to: {new_file_path}.")
    return new_file_path

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
        The path to the saved project file.
    Raises:        
        logix_designer_sdk.LogixError: If the project cannot be opened or saved.
    """

    source = Path(existing_file_path)
    output_path = Path(output_dir) / f"{source.stem}.l5x"

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_copy = Path(tmp_dir) / source.name
        shutil.copy2(source, tmp_copy)

        converted_path = await _convert_project(
            str(tmp_copy),
            str(output_path),
            detailed_l5x=detailed_l5x,
        )
    return converted_path
