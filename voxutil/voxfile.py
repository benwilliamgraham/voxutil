"""VoxFile structure and related functions.

The goal of this module is to provide an interface for reading and writing
MagicaVoxel .vox files. This class is not meant to be used directly to create
or modify .vox files, but rather to provide a way to read and write .vox files
in a way that provides a more Pythonic interface than the raw .vox file format.
"""


class VoxFile:
    """VoxFile class."""

    def __init__(self, version: int, main: "Chunk"):
        """VoxFile constructor."""
        self.version = version
        self.main = main

    @staticmethod
    def read(self, path: str) -> "VoxFile":
        """Read a .vox file from the given path."""
        with open(path, "rb") as f:
            byte_iter = iter(f.read())

            header = b"".join([next(byte_iter) for _ in range(4)])
            if header != b"VOX ":
                raise ValueError("Invalid .vox file header.")

            version = Int32.read(byte_iter)

            main = Chunk.read(byte_iter, b"MAIN", MainContent)

            return VoxFile(version, main)

    def write(self, path: str):
        """Write a .vox file to the given path."""
        with open(path, "wb") as f:
            # TODO: Write the file to the given path.
            pass


class Int32:
    """Int32 class."""

    @staticmethod
    def read(byte_iter: iter) -> int:
        """Read a 32-bit integer from the given byte iterator."""
        return int.from_bytes(b"".join([next(byte_iter) for _ in range(4)]), "little")

    @staticmethod
    def write(value: int) -> bytes:
        """Write a 32-bit integer to bytes."""
        return value.to_bytes(4, "little")


class Chunk:
    """Chunk class."""

    id = b""

    def __init__(self, children: list["Chunk"]):
        """Chunk constructor."""
        self.children = children

    @staticmethod
    def read(byte_iter: iter, expected_id: bytes, content_class: type) -> "Chunk":
        """Read a chunk from the given byte iterator."""
        raise NotImplementedError()


class MainChunk(Chunk):
    """Main chunk class."""

    id = b"MAIN"

    def __init__(
        self, models: list[tuple["SizeChunk", "XYZIChunk"]], palette: "PaletteChunk"
    ):
        """MainChunk constructor."""
        self.models = models
        self.palette = palette


class SizeChunk(Chunk):
    """Size chunk class."""

    id = b"SIZE"

    def __init__(self, size: tuple[int, int, int]):
        """SizeChunk constructor."""
        self.size = size


class XYZIChunk(Chunk):
    """XYZI chunk class."""

    id = b"XYZI"

    def __init__(self, voxels: list[tuple[int, int, int, int]]):
        """XYZIChunk constructor."""
        self.voxels = voxels


class PaletteChunk(Chunk):
    """Palette chunk class."""

    id = b"RGBA"

    def __init__(self, palette: list[tuple[int, int, int, int]]):
        """PaletteChunk constructor."""
        self.palette = palette
