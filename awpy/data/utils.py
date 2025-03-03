"""Manages data folders for Awpy."""

import zipfile

import requests
import tqdm
from loguru import logger

from awpy.data import AWPY_DATA_DIR


def create_data_dir_if_not_exists() -> None:
    """Creates the awpy data directory if it doesn't exist."""
    if not AWPY_DATA_DIR.exists():
        AWPY_DATA_DIR.mkdir(parents=True, exist_ok=True)
        awpy_data_dir_creation_msg = f"Created awpy data directory at {AWPY_DATA_DIR}"
        logger.debug(awpy_data_dir_creation_msg)


def fetch_resource(resource: str, patch: int, filetype: str = ".zip") -> None:
    """Download and optionally extract a resource file from the Awpy mirror.

    Constructs the URL for the resource based on the provided resource name, patch version,
    and file extension. The file is then downloaded with a progress bar displayed via tqdm.
    If the filetype is '.zip', the resource is extracted into a corresponding directory,
    a '.patch' file containing the patch number is written into that directory, and the
    original ZIP file is deleted after successful extraction.

    Args:
        resource (str): The name of the resource to fetch.
        patch (int): The patch version number to include in the URL.
        filetype (str, optional): The file extension of the resource. Defaults to ".zip".

    Raises:
        requests.HTTPError: If the HTTP GET request fails (i.e., the response status is not OK).
    """
    # Create directory if compressed folder
    resource_path = AWPY_DATA_DIR / f"{resource}{filetype}"
    if filetype == ".zip":
        resource_dir = AWPY_DATA_DIR / resource
        resource_dir.mkdir(parents=True, exist_ok=True)
        resource_path = resource_dir / f"{resource}{filetype}"

    # Fetch the resource
    resource_url = f"https://awpycs.com/{patch}/{resource}{filetype}"
    response = requests.get(resource_url, stream=True, timeout=300)
    if not response.ok:
        bad_resp_err_msg = f"Failed to fetch {resource_url}: {response.status_code}"
        raise requests.HTTPError(bad_resp_err_msg)
    total_size = int(response.headers.get("content-length", 0))
    block_size = 1024
    with (
        tqdm.tqdm(total=total_size, unit="B", unit_scale=True) as progress_bar,
        open(resource_path, "wb") as file,
    ):
        for data in response.iter_content(block_size):
            progress_bar.update(len(data))
            file.write(data)  # Could also write the patchnumber to .patch

    # Write the patch number to a ".patch" file in the resource directory (if applicable)
    if filetype == ".zip":
        patch_file = resource_dir / ".patch"
        with open(patch_file, "w") as pf:
            pf.write(str(patch))
        logger.info(f"Wrote patch number {patch} to {patch_file}")

    # Unzip the file
    if filetype == ".zip":
        try:
            with zipfile.ZipFile(resource_path, "r") as zip_ref:
                zip_ref.extractall(resource_dir)
            logger.success(f"Extracted contents of {resource_path} to {resource_dir}")
        except zipfile.BadZipFile as e:
            logger.error(f"Failed to unzip {resource_path}: {e}")
            return
        resource_path.unlink()
