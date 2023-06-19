"""Volume class for VoxUtil.

The goal of this module is to provide an interface for creating and modifying
MagicaVoxel .vox files. This class is meant to be used by the user to create
volumes that can be converted to .vox files.
"""

from voxutil import voxfile
from typing import Optional


class Color:
    """Color class."""

    def __init__(self, r: int, g: int, b: int, a: int = 255):
        self.r = r
        self.g = g
        self.b = b
        self.a = a


class Palette:
    """Palette class."""

    def __init__(self):
        self.color_count_map: dict[Color, int] = {}

    def use_color(self, color: Color):
        if color in self.color_count_map:
            self.color_count_map[color] += 1
        else:
            if len(self.color_count_map) >= 256:
                raise ValueError("Palette is full.")
            self.color_count_map[color] = 1

    def unuse_color(self, color: Color):
        if color not in self.color_count_map:
            raise ValueError("Color is not in palette.")
        self.color_count_map[color] -= 1
        if self.color_count_map[color] == 0:
            del self.color_count_map[color]


class Volume:
    """Volume class."""

    def __init__(self, size: tuple[int, int, int]):
        self.size = size
        self.voxels: list[Optional[Color]] = [
            None for _ in range(size[0] * size[1] * size[2])
        ]
        self.palette = Palette()

    def set(self, index: tuple[int, int, int], color: Optional[Color]):
        for i in range(3):
            if index[i] < 0 or index[i] >= self.size[i]:
                raise ValueError(
                    f"Index {i} out of bounds: {index[0]} not in [0, {self.size[0]})"
                )

        if color is not None:
            self.palette.use_color(color)

        prev_color = self.get(index)
        if prev_color is not None:
            self.palette.unuse_color(prev_color)

        self.voxels[
            index[0] + index[1] * self.size[0] + index[2] * self.size[0] * self.size[1]
        ] = color

    def get(self, index) -> Optional[Color]:
        return self.voxels[
            index[0] + index[1] * self.size[0] + index[2] * self.size[0] * self.size[1]
        ]

    def to_voxfile(self) -> voxfile.VoxFile:
        pass
