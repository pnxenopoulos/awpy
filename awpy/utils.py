"""Util functions for csgo package."""

import re
import subprocess
from typing import Self, TypeVar

import pandas as pd
from typing_extensions import override

from awpy.types import Area, TileId

_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


class AutoVivification(dict[_KT, _VT | Self]):
    """Implementation of perl's autovivification feature.

    Stolen from:
    https://stackoverflow.com/questions/651794/whats-the-best-way-to-initialize-a-dict-of-dicts-in-python
    """

    @override
    def __getitem__(self, item: _KT) -> _VT | Self:
        """Autovivified get item from dict.

        Tries to get the item as normal.
        If a KeyError is encountered another
        AutoVivification dict is added instead.

        Args:
            item (_KT): Item to retrieve the value for.

        Returns:
            _VT | Self: Retrieved value.
        """
        try:
            return dict[_KT, _VT | Self].__getitem__(self, item)
        except KeyError:
            value = self[item] = type(self)()
            return value


def check_go_version() -> bool:
    """Function to check the Golang version of the current machine.

    Returns True if greater than 1.18.0

    Returns:
        bool: bool whether the found go version is recent enough

    Raises:
        ValueError: If the go version could not be retrieved
    """

    def parse_go_version(parsed_resp: list[bytes] | None) -> list[str]:
        """Parse the go version from a list of bytes.

        Args:
            parsed_resp (list[bytes] | None): Raw input to extract version from.

        Returns:
            list[str]: List representation of the version.

        Raises:
            ValueError: If the go version could not be retrieved
        """
        if parsed_resp is None or len(parsed_resp) != 1:
            msg = "Error finding Go version"
            raise ValueError(msg)
        go_version_text = parsed_resp[0].decode("utf-8")
        go_version = re.findall(r"\d\.\d+", go_version_text)
        return go_version[0].split(".")

    try:
        with subprocess.Popen(
            ["go", "version"], stdout=subprocess.PIPE  # noqa: S603, S607
        ) as proc:
            parsed_resp = (
                proc.stdout.read().splitlines() if proc.stdout is not None else None
            )
        parsed_go_version = parse_go_version(parsed_resp)
    except Exception as e:  # noqa: BLE001
        print(e)
        return False
    return [int(x) for x in parsed_go_version] >= [1, 18]


def is_in_range(value: float, minimum: float, maximum: float) -> bool:
    """Checks if a value is in the range of two others inclusive.

    Args:
        value (float): Value to check whether it is in range
        minimum (float): Lower inclusive bound of the range check
        maximum (float): Upper inclusive bound of the range check

    Returns:
        bool: Whether the value us between min and max.
    """
    return minimum <= value <= maximum


def transform_csv_to_json(sample_csv: pd.DataFrame) -> dict[str, dict[TileId, Area]]:
    """From Adi. Used to transform a nav file CSV to JSON.

    Args:
        sample_csv (pd.DataFrame): Information about areas of each map

    Returns:
        dict[str, dict[TileId, Area]]: Information about each area of each map
    """
    final_dic: dict[str, dict[TileId, Area]] = {}
    for cur_map in sample_csv["mapName"].unique():
        map_dic: dict[TileId, Area] = {}
        for i in sample_csv[sample_csv["mapName"] == cur_map].index:
            cur_tile = sample_csv.iloc[i]
            cur_dic = {
                cur_feature: cur_tile[cur_feature]
                for cur_feature in sample_csv.columns
                if cur_feature not in ["mapName", "areaId"]
            }
            map_dic[cur_tile["areaId"]] = cur_dic  # type: ignore[assignment]
        final_dic[cur_map] = map_dic
    return final_dic
