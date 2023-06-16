"""VoxFile structure and related functions.

The goal of this module is to provide an interface for reading and writing
MagicaVoxel .vox files. This class is not meant to be used directly to create
or modify .vox files, but rather to provide a way to read and write .vox files
in a way that provides a more Pythonic interface than the raw .vox file format.
"""


class FileIter:
    """Iterator for raw .vox file bytes."""

    def __init__(self, bytes_: bytes):
        """FileIter constructor."""
        self.bytes_ = bytes_
        self.index = 0

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

    id = b""

    def __init__(self, children: list["Chunk"]):
        """Chunk constructor."""
        self.children = children

    @classmethod
    def check_id(cls, byte_iter: FileIter):
        """Check that the next four bytes in the given byte iterator match the chunk ID."""
        id = byte_iter.read_bytes(4)
        if id != cls.id:
            raise ValueError(f"Invalid chunk ID: {id}; expected {cls.id}")


class MainChunk(Chunk):
    """Main chunk class."""

    id = b"MAIN"

    def __init__(
        self, models: list[tuple["SizeChunk", "XYZIChunk"]], palette: "PaletteChunk"
    ):
        """MainChunk constructor."""
        self.models = models
        self.palette = palette

    @classmethod
    def read(cls, byte_iter: FileIter) -> "MainChunk":
        """Read a main chunk from the given byte iterator."""
        cls.check_id(byte_iter)


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
