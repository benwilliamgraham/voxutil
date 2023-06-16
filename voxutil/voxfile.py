"""VoxFile structure and related functions.

The goal of this module is to provide an interface for reading and writing
MagicaVoxel .vox files. This class is not meant to be used directly to create
or modify .vox files, but rather to provide a way to read and write .vox files
in a way that provides a more Pythonic interface than the raw .vox file format.
"""

from typing import Optional


class FileIter:
    """Iterator for raw .vox file bytes."""

    def __init__(self, bytes_: bytes):
        """FileIter constructor."""
        self.bytes_ = bytes_
        self.index = 0

    def __bool__(self):
        """Return whether the iterator has reached the end of the file."""
        return self.index < len(self.bytes_)

    def peek_byte(self) -> bytes:
        """Peek at the next byte without advancing the iterator."""
        return self.bytes_[self.index]

    def read_byte(self) -> bytes:
        """Read a single byte."""
        byte = self.peek_byte()
        self.index += 1
        return byte

    def peek_bytes(self, n: int) -> bytes:
        """Peek at the next n bytes without advancing the iterator."""
        return self.bytes_[self.index : self.index + n]

    def read_bytes(self, n: int) -> bytes:
        """Read n bytes."""
        bytes_ = self.peek_bytes(n)
        self.index += n
        return bytes_

    def peek_int32(self) -> int:
        """Peek at the next 32-bit integer without advancing the iterator."""
        return int.from_bytes(self.peek_bytes(4), "little")

    def read_int32(self) -> int:
        """Read a 32-bit integer."""
        int32 = self.peek_int32()
        self.index += 4
        return int32


class VoxFile:
    """VoxFile class."""

    def __init__(self, version: int, main: "Chunk"):
        """VoxFile constructor."""
        self.version = version
        self.main = main

    @staticmethod
    def read(path: str) -> "VoxFile":
        """Read a .vox file from the given path."""
        with open(path, "rb") as f:
            byte_iter = FileIter(f.read())

            header = byte_iter.read_bytes(4)
            if header != b"VOX ":
                raise ValueError("Invalid .vox file header.")

            version = byte_iter.read_int32()

            main = MainChunk.read(byte_iter)

            return VoxFile(version, main)

    def write(self, path: str):
        """Write a .vox file to the given path."""
        with open(path, "wb") as f:
            # TODO: Write the file to the given path.
            pass


class Chunk:
    """Chunk class."""

    id = None

    def __init__(self, children: list["Chunk"]):
        """Chunk constructor."""
        self.children = children

    @classmethod
    def check_id(cls, byte_iter: FileIter):
        """Check that the next four bytes in the given byte iterator match the chunk ID."""
        id = byte_iter.read_bytes(4)
        if id != cls.id:
            raise ValueError(f"Invalid chunk ID: {id}; expected {cls.id}")

    @classmethod
    def read_num_bytes(cls, byte_iter: FileIter) -> tuple[int, int]:
        """Read the number of bytes in the chunk content and children."""
        content_size = byte_iter.read_int32()
        children_size = byte_iter.read_int32()
        return content_size, children_size


class MainChunk(Chunk):
    """Main chunk class."""

    id = b"MAIN"

    def __init__(
        self,
        pack: Optional["PackChunk"],
        models: list[tuple["SizeChunk", "XYZIChunk"]],
        palette: Optional["PaletteChunk"],
    ):
        """MainChunk constructor."""
        self.pack = pack
        self.models = models
        self.palette = palette

    @classmethod
    def read(cls, byte_iter: FileIter) -> "MainChunk":
        """Read a main chunk from the given byte iterator."""
        cls.check_id(byte_iter)

        cls.read_num_bytes(byte_iter)

        pack = None
        models = []
        palette = None

        while byte_iter:
            id = byte_iter.peek_bytes(4)

            if id == SizeChunk.id:
                size_chunk = SizeChunk.read(byte_iter)

                # assume next chunk is XYZI chunk
                id = byte_iter.peek_bytes(4)
                if id != XYZIChunk.id:
                    raise ValueError(
                        f"Invalid chunk ID: {id}; expected {XYZIChunk.id} following {SizeChunk.id}"
                    )
                xyzi_chunk = XYZIChunk.read(byte_iter)

                models += [(size_chunk, xyzi_chunk)]
            else:
                raise ValueError(f"Invalid chunk ID: {id}")

        return MainChunk(pack, models, palette)


class PackChunk(Chunk):
    """Pack chunk class."""

    id = b"PACK"

    def __init__(self, num_models: int):
        """PackChunk constructor."""
        self.num_models = num_models

    @classmethod
    def read(cls, byte_iter: FileIter) -> "PackChunk":
        """Read a pack chunk from the given byte iterator."""
        cls.check_id(byte_iter)

        cls.read_num_bytes(byte_iter)

        num_models = byte_iter.read_int32()

        return PackChunk(num_models)


class SizeChunk(Chunk):
    """Size chunk class."""

    id = b"SIZE"

    def __init__(self, size: tuple[int, int, int]):
        """SizeChunk constructor."""
        self.size = size

    @classmethod
    def read(cls, byte_iter: FileIter) -> "SizeChunk":
        cls.check_id(byte_iter)

        cls.read_num_bytes(byte_iter)

        x = byte_iter.read_int32()
        y = byte_iter.read_int32()
        z = byte_iter.read_int32()

        return SizeChunk((x, y, z))


class XYZIChunk(Chunk):
    """XYZI chunk class."""

    id = b"XYZI"

    def __init__(self, voxels: list[tuple[int, int, int, int]]):
        """XYZIChunk constructor."""
        self.voxels = voxels

    @classmethod
    def read(cls, byte_iter: FileIter) -> "XYZIChunk":
        cls.check_id(byte_iter)

        cls.read_num_bytes(byte_iter)

        num_voxels = byte_iter.read_int32()

        voxels = []
        for _ in range(num_voxels):
            x = byte_iter.read_byte()
            y = byte_iter.read_byte()
            z = byte_iter.read_byte()
            color_index = byte_iter.read_byte()
            voxels += [(x, y, z, color_index)]

        return XYZIChunk(voxels)


class PaletteChunk(Chunk):
    """Palette chunk class."""

    id = b"RGBA"

    def __init__(self, palette: list[tuple[int, int, int, int]]):
        """PaletteChunk constructor."""
        self.palette = palette

    @classmethod
    def read(cls, byte_iter: FileIter) -> "PaletteChunk":
        cls.check_id(byte_iter)

        cls.read_num_bytes(byte_iter)

        palette = [(0, 0, 0, 0)]
        for _ in range(255):
            r = byte_iter.read_byte()
            g = byte_iter.read_byte()
            b = byte_iter.read_byte()
            a = byte_iter.read_byte()
            palette += [(r, g, b, a)]

        return PaletteChunk(palette)