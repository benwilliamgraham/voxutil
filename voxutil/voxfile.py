"""VoxFile structure and related functions.

The goal of this module is to provide an interface for reading and writing
MagicaVoxel .vox files. This class is not meant to be used directly to create
or modify .vox files, but rather to provide a way to read and write .vox files
in a way that provides a more Pythonic interface than the raw .vox file format.
"""

import io
from typing import Optional, Union, Iterator


class Bytes:
    """Representative of .vox file bytes."""

    @staticmethod
    def read(byte_iter: Iterator[bytes], n: int) -> bytes:
        """Read n bytes from bytes."""
        return b"".join(next(byte_iter) for _ in range(n))


class Int32:
    """Representative of .vox file 32-bit integers."""

    @staticmethod
    def read(byte_iter: Iterator[bytes]) -> int:
        """Read a 32-bit integer from bytes."""
        return int.from_bytes(Bytes.read(byte_iter, 4), "little", signed=True)

    @staticmethod
    def write(int32: int) -> bytes:
        """Write a 32-bit integer to bytes."""
        return int32.to_bytes(4, "little", signed=True)


class String:
    """Representative of .vox file strings."""

    @staticmethod
    def read(byte_iter: Iterator[bytes]) -> str:
        """Read a string from bytes."""
        length = Int32.read(byte_iter)
        return Bytes.read(byte_iter, length).decode("utf-8")

    @staticmethod
    def write(string: str) -> bytes:
        """Write a string to bytes."""
        return Int32.write(len(string)) + bytes(string, "utf-8")


class Dict:
    """Representative of .vox file dictionaries."""

    @staticmethod
    def read(byte_iter: Iterator[bytes]) -> dict:
        """Read a dictionary from bytes."""
        length = Int32.read(byte_iter)
        dict_ = {}
        for _ in range(length):
            key = String.read(byte_iter)
            value = String.read(byte_iter)
            dict_[key] = value
        return dict_

    @staticmethod
    def write(dict_: dict) -> bytes:
        """Write a dictionary to bytes."""
        bytes_ = Int32.write(len(dict_))
        for key, value in dict_.items():
            bytes_ += String.write(key) + String.write(value)
        return bytes_


class VoxFile:
    """VoxFile class."""

    def __init__(self, version: int, main: "MainChunk"):
        """VoxFile constructor."""
        self.version = version
        self.main = main

    @staticmethod
    def read(path: str) -> "VoxFile":
        """Read a .vox file from the given path."""
        with open(path, "rb") as f:
            byte_iter = iter(f.read())

            header = Bytes.read(byte_iter, 4)
            if header != b"VOX ":
                raise ValueError("Invalid .vox file header.")

            version = Int32.read(byte_iter)

            main = MainChunk.read(byte_iter)

            return VoxFile(version, main)

    def write(self, path: str):
        """Write a .vox file to the given path."""
        with open(path, "wb") as f:
            f.write(b"VOX ")
            f.write(Int32.write(self.version))
            f.write(bytes(self.main))


class Chunk:
    """Chunk class."""

    id = b""
    has_children = False

    @classmethod
    def consume_header(cls, byte_iter: Iterator[bytes]):
        """Check that the next four bytes in the given byte iterator match the chunk ID."""
        id = byte_iter.read_bytes(4)
        if id != cls.id:
            raise ValueError(f"Invalid chunk ID: {id!r}; expected {cls.id!r}")

        byte_iter.read_int32()  # consume chunk content size
        child_bytes = byte_iter.read_int32()  # consume child chunk size
        if child_bytes and not cls.has_children:
            raise ValueError(f"Chunk {cls.id!r} has unexpected children")

    def to_chunk_byte_format(self, content: bytes, child_content: bytes) -> bytes:
        """Convert chunk to bytes"""
        bytes_ = self.id

        bytes_ += Int32.read(len(content))
        bytes_ += Int32.read(len(child_content))

        bytes_ += content
        bytes_ += child_content

        return bytes_


class MainChunk(Chunk):
    """Main chunk class.

    Chunk 'MAIN'
    {
        // pack of models
        Chunk 'PACK'    : optional

        // models
        Chunk 'SIZE'
        Chunk 'XYZI'

        Chunk 'SIZE'
        Chunk 'XYZI'

        ...

        Chunk 'SIZE'
        Chunk 'XYZI'

        // palette
        Chunk 'RGBA'    : optional
    }
    """

    id = b"MAIN"

    has_children = True

    def __init__(
        self,
        pack: Optional["PackChunk"],
        models: list[tuple["SizeChunk", "XYZIChunk"]],
        palette: Optional["PaletteChunk"],
        scene_graph: list[Union["TransformChunk", "GroupChunk", "ShapeChunk"]],
        materials: list["MaterialChunk"],
        layers: list["LayerChunk"],
        render_objects: list["RenderObjectChunk"],
        render_cameras: list["RenderCameraChunk"],
        palette_note: Optional["PaletteNoteChunk"],
        index_map: Optional["IndexMapChunk"],
    ):
        """MainChunk constructor."""
        self.pack = pack
        self.models = models
        self.palette = palette
        self.scene_graph = scene_graph
        self.materials = materials
        self.layers = layers
        self.render_objects = render_objects
        self.render_cameras = render_cameras
        self.palette_note = palette_note
        self.index_map = index_map

    @classmethod
    def read(cls, byte_iter: Iterator[bytes]) -> "MainChunk":
        """Read a main chunk from the given byte iterator."""
        cls.consume_header(byte_iter)

        pack = None
        models = []
        palette = None
        scene_graph: list[Union["TransformChunk", "GroupChunk", "ShapeChunk"]] = []
        materials = []
        layers = []
        render_objects = []
        render_cameras = []
        palette_note = None
        index_map = None

        while byte_iter:
            id = byte_iter.peek_bytes(4)

            if id == PackChunk.id:
                pack = PackChunk.read(byte_iter)
            elif id == SizeChunk.id:
                size_chunk = SizeChunk.read(byte_iter)

                # assume next chunk is XYZI chunk
                id = byte_iter.peek_bytes(4)
                if id != XYZIChunk.id:
                    raise ValueError(
                        f"Invalid chunk ID: {id!r}; expected {XYZIChunk.id!r} following {SizeChunk.id!r}"
                    )
                xyzi_chunk = XYZIChunk.read(byte_iter)

                models += [(size_chunk, xyzi_chunk)]
            elif id == PaletteChunk.id:
                palette = PaletteChunk.read(byte_iter)
            elif id == TransformChunk.id:
                transform_chunk = TransformChunk.read(byte_iter)
                scene_graph += [transform_chunk]
            elif id == GroupChunk.id:
                group_chunk = GroupChunk.read(byte_iter)
                scene_graph += [group_chunk]
            elif id == ShapeChunk.id:
                shape_chunk = ShapeChunk.read(byte_iter)
                scene_graph += [shape_chunk]
            elif id == MaterialChunk.id:
                material_chunk = MaterialChunk.read(byte_iter)
                materials += [material_chunk]
            elif id == LayerChunk.id:
                layer_chunk = LayerChunk.read(byte_iter)
                layers += [layer_chunk]
            elif id == RenderObjectChunk.id:
                render_object = RenderObjectChunk.read(byte_iter)
                render_objects += [render_object]
            elif id == RenderCameraChunk.id:
                render_camera = RenderCameraChunk.read(byte_iter)
                render_cameras += [render_camera]
            elif id == PaletteNoteChunk.id:
                palette_note = PaletteNoteChunk.read(byte_iter)
            elif id == IndexMapChunk.id:
                index_map = IndexMapChunk.read(byte_iter)
            else:
                raise ValueError(f"Invalid chunk ID: {id!r}")

        return MainChunk(
            pack,
            models,
            palette,
            scene_graph,
            materials,
            layers,
            render_objects,
            render_cameras,
            palette_note,
            index_map,
        )

    def __bytes__(self):
        child_content = b""

        if self.pack is not None:
            child_content += bytes(self.pack)

        for model in self.models:
            child_content += bytes(model[0])
            child_content += bytes(model[1])

        for item in self.scene_graph:
            child_content += bytes(item)

        for layer in self.layers:
            child_content += bytes(layer)

        if self.palette is not None:
            child_content += bytes(self.palette)

        if self.index_map is not None:
            child_content += bytes(self.index_map)

        for material in self.materials:
            child_content += bytes(material)

        for render_object in self.render_objects:
            child_content += bytes(render_object)

        for render_camera in self.render_cameras:
            child_content += bytes(render_camera)

        if self.palette_note is not None:
            child_content += bytes(self.palette_note)

        return self.to_chunk_byte_format(b"", child_content)


class PackChunk(Chunk):
    """Pack chunk class.

    -------------------------------------------------------------------------------
    # Bytes  | Type       | Value
    -------------------------------------------------------------------------------
    4        | int        | numModels : num of SIZE and XYZI chunks
    -------------------------------------------------------------------------------
    """

    id = b"PACK"

    def __init__(self, num_models: int):
        """PackChunk constructor."""
        self.num_models = num_models

    @classmethod
    def read(cls, byte_iter: Iterator[bytes]) -> "PackChunk":
        """Read a pack chunk from the given byte iterator."""
        cls.consume_header(byte_iter)

        num_models = byte_iter.read_int32()

        return PackChunk(num_models)


class SizeChunk(Chunk):
    """Size chunk class.

    -------------------------------------------------------------------------------
    # Bytes  | Type       | Value
    -------------------------------------------------------------------------------
    4        | int        | size x
    4        | int        | size y
    4        | int        | size z : gravity direction
    -------------------------------------------------------------------------------
    """

    id = b"SIZE"

    def __init__(self, size: tuple[int, int, int]):
        """SizeChunk constructor."""
        self.size = size

    @classmethod
    def read(cls, byte_iter: Iterator[bytes]) -> "SizeChunk":
        cls.consume_header(byte_iter)

        x = byte_iter.read_int32()
        y = byte_iter.read_int32()
        z = byte_iter.read_int32()

        return SizeChunk((x, y, z))

    def __bytes__(self):
        content = (
            Int32.read(self.size[0])
            + Int32.read(self.size[1])
            + Int32.read(self.size[2])
        )

        return self.to_chunk_byte_format(content, b"")


class XYZIChunk(Chunk):
    """XYZI chunk class.

    -------------------------------------------------------------------------------
    # Bytes  | Type       | Value
    -------------------------------------------------------------------------------
    4        | int        | numVoxels (N)
    4 x N    | int        | (x, y, z, colorIndex) : 1 byte for each component
    -------------------------------------------------------------------------------
    """

    id = b"XYZI"

    def __init__(self, voxels: list[tuple[int, int, int, int]]):
        """XYZIChunk constructor."""
        self.voxels = voxels

    @classmethod
    def read(cls, byte_iter: Iterator[bytes]) -> "XYZIChunk":
        cls.consume_header(byte_iter)

        num_voxels = byte_iter.read_int32()

        voxels = []
        for _ in range(num_voxels):
            x = int.from_bytes(byte_iter.read_byte(), "little")
            y = int.from_bytes(byte_iter.read_byte(), "little")
            z = int.from_bytes(byte_iter.read_byte(), "little")
            color_index = int.from_bytes(byte_iter.read_byte(), "little")
            voxels += [(x, y, z, color_index)]

        return XYZIChunk(voxels)

    def __bytes__(self):
        content = Int32.read(len(self.voxels))

        for voxel in self.voxels:
            for val in voxel:
                content += val.to_bytes(1, "little")

        return self.to_chunk_byte_format(content, b"")


class PaletteChunk(Chunk):
    """Palette chunk class.

    -------------------------------------------------------------------------------
    # Bytes  | Type     | Value
    -------------------------------------------------------------------------------
    4 x 256  | int      | (R, G, B, A) : 1 byte for each component
                        | * <NOTICE>
                        | * color [0-254] are mapped to palette index [1-255], e.g :
                        |
                        | for ( int i = 0; i <= 254; i++ ) {
                        |     palette[i + 1] = ReadRGBA();
                        | }
    -------------------------------------------------------------------------------
    """

    id = b"RGBA"

    def __init__(self, palette: list[tuple[int, int, int, int]]):
        """PaletteChunk constructor."""
        self.palette = palette

    @classmethod
    def read(cls, byte_iter: Iterator[bytes]) -> "PaletteChunk":
        cls.consume_header(byte_iter)

        palette = [(0, 0, 0, 0)]
        for _ in range(255):
            r = int.from_bytes(byte_iter.read_byte(), "little")
            g = int.from_bytes(byte_iter.read_byte(), "little")
            b = int.from_bytes(byte_iter.read_byte(), "little")
            a = int.from_bytes(byte_iter.read_byte(), "little")
            palette += [(r, g, b, a)]

        # for some reason, this still uses 256 bytes, so discard another 4 bytes afterwards
        byte_iter.read_bytes(4)

        return PaletteChunk(palette)

    def __bytes__(self):
        content = b""

        for color in self.palette[1:]:
            for val in color:
                content += val.to_bytes(1, "little")

        content += (0).to_bytes(4, "little")

        return self.to_chunk_byte_format(content, b"")


class TransformChunk(Chunk):
    """Transform chunk class.

    int32	: node id
    DICT	: node attributes
        (_name : string)
        (_hidden : 0/1)
    int32 	: child node id
    int32 	: reserved id (must be -1)
    int32	: layer id
    int32	: num of frames (must be greater than 0)

    // for each frame
    {
    DICT	: frame attributes
        (_r : int8)    ROTATION, see (c)
        (_t : int32x3) translation
        (_f : int32)   frame index, start from 0
    }xN
    """

    id = b"nTRN"

    def __init__(
        self,
        node_id: int,
        attributes: dict,
        child_node_id: int,
        layer_id: int,
        frames: list[dict],
    ):
        """TransformChunk constructor."""
        self.node_id = node_id
        self.attributes = attributes
        self.child_node_id = child_node_id
        self.layer_id = layer_id
        self.frames = frames

    @classmethod
    def read(cls, byte_iter: Iterator[bytes]) -> "TransformChunk":
        cls.consume_header(byte_iter)

        node_id = byte_iter.read_int32()
        attributes = byte_iter.read_dict()
        child_node_id = byte_iter.read_int32()
        reserved_id = byte_iter.read_int32()
        if reserved_id != -1:
            raise ValueError(f"Invalid reserved id: {reserved_id}")
        layer_id = byte_iter.read_int32()
        num_frames = byte_iter.read_int32()

        frames = []
        for _ in range(num_frames):
            frame_attributes = byte_iter.read_dict()
            frames += [frame_attributes]

        return TransformChunk(node_id, attributes, child_node_id, layer_id, frames)

    def __bytes__(self):
        content = Int32.read(self.node_id)
        content += Dict.read(self.attributes)
        content += Int32.read(self.child_node_id)
        content += Int32.read(-1)
        content += Int32.read(self.layer_id)
        content += Int32.read(len(self.frames))

        for frame in self.frames:
            content += Dict.read(frame)

        return self.to_chunk_byte_format(content, b"")


class GroupChunk(Chunk):
    """Group chunk class.

    int32	: node id
    DICT	: node attributes
    int32 	: num of children nodes

    // for each child
    {
    int32	: child node id
    }xN
    """

    id = b"nGRP"

    def __init__(
        self,
        node_id: int,
        attributes: dict,
        child_node_ids: list[int],
    ):
        """GroupChunk constructor."""
        self.node_id = node_id
        self.attributes = attributes
        self.child_node_ids = child_node_ids

    @classmethod
    def read(cls, byte_iter: Iterator[bytes]) -> "GroupChunk":
        cls.consume_header(byte_iter)

        node_id = byte_iter.read_int32()
        attributes = byte_iter.read_dict()
        num_children = byte_iter.read_int32()

        child_node_ids = []
        for _ in range(num_children):
            child_node_id = byte_iter.read_int32()
            child_node_ids += [child_node_id]

        return GroupChunk(node_id, attributes, child_node_ids)

    def __bytes__(self):
        content = Int32.read(self.node_id)

        content += Dict.read(self.attributes)

        content += Int32.read(len(self.child_node_ids))

        for child_node_id in self.child_node_ids:
            content += Int32.read(child_node_id)

        return self.to_chunk_byte_format(content, b"")


class ShapeChunk(Chunk):
    """Shape chunk class.

    int32	: node id
    DICT	: node attributes
    int32 	: num of models (must be greater than 0)

    // for each model
    {
    int32	: model id
    DICT	: model attributes : reserved
        (_f : int32)   frame index, start from 0
    }xN
    """

    id = b"nSHP"

    def __init__(self, node_id: int, attributes: dict, models: list[tuple[int, dict]]):
        """ShapeChunk constructor."""
        self.node_id = node_id
        self.attributes = attributes
        self.models = models

    @classmethod
    def read(cls, byte_iter: Iterator[bytes]) -> "ShapeChunk":
        cls.consume_header(byte_iter)

        node_id = byte_iter.read_int32()
        attributes = byte_iter.read_dict()
        num_models = byte_iter.read_int32()

        models = []
        for _ in range(num_models):
            model_id = byte_iter.read_int32()
            model_attributes = byte_iter.read_dict()
            models += [(model_id, model_attributes)]

        return ShapeChunk(node_id, attributes, models)

    def __bytes__(self):
        content = Int32.read(self.node_id)

        content += Dict.read(self.attributes)

        content += Int32.read(len(self.models))

        for model in self.models:
            content += Int32.read(model[0])
            content += Dict.read(model[1])

        return self.to_chunk_byte_format(content, b"")


class MaterialChunk(Chunk):
    """Material chunk class.

    int32	: material id
    DICT	: material properties
          (_type : str) _diffuse, _metal, _glass, _emit
          (_weight : float) range 0 ~ 1
          (_rough : float)
          (_spec : float)
          (_ior : float)
          (_att : float)
          (_flux : float)
          (_plastic)
    """

    id = b"MATL"

    def __init__(self, material_id: int, properties: dict):
        self.material_id = material_id
        self.properties = properties

    @classmethod
    def read(cls, byte_iter: Iterator[bytes]):
        cls.consume_header(byte_iter)

        material_id = byte_iter.read_int32()

        properties = byte_iter.read_dict()

        return MaterialChunk(material_id, properties)

    def __bytes__(self):
        content = Int32.read(self.material_id)

        content += Dict.read(self.properties)

        return self.to_chunk_byte_format(content, b"")


class LayerChunk(Chunk):
    """Layer chunk class.

    int32	: layer id
    DICT	: layer attribute
        (_name : string)
        (_hidden : 0/1)
    int32	: reserved id, must be -1
    """

    id = b"LAYR"

    def __init__(self, layer_id: int, attribute: dict):
        self.layer_id = layer_id
        self.attribute = attribute

    @classmethod
    def read(cls, byte_iter: Iterator[bytes]):
        cls.consume_header(byte_iter)

        layer_id = byte_iter.read_int32()

        attribute = byte_iter.read_dict()

        reserved_id = byte_iter.read_int32()
        if reserved_id != -1:
            raise ValueError(f"Invalid reserved id: {reserved_id}")

        return LayerChunk(layer_id, attribute)

    def __bytes__(self):
        content = Int32.read(self.layer_id)

        content += Dict.read(self.attribute)

        content += Int32.read(-1)

        return self.to_chunk_byte_format(content, b"")


class RenderObjectChunk(Chunk):
    """Render Object chunk class.

    DICT	: rendering attributes
    """

    id = b"rOBJ"

    def __init__(self, attributes: dict):
        self.attributes = attributes

    @classmethod
    def read(cls, byte_iter: Iterator[bytes]):
        cls.consume_header(byte_iter)

        attributes = byte_iter.read_dict()

        return RenderObjectChunk(attributes)

    def __bytes__(self):
        content = Dict.read(self.attributes)

        return self.to_chunk_byte_format(content, b"")


class RenderCameraChunk(Chunk):
    """Render Camera chunk class.

    int32	: camera id
    DICT	: camera attribute
        (_mode : string)
        (_focus : vec(3))
        (_angle : vec(3))
        (_radius : int)
        (_frustum : float)
        (_fov : int)
    """

    id = b"rCAM"

    def __init__(self, camera_id: int, attribute: dict):
        self.camera_id = camera_id
        self.attribute = attribute

    @classmethod
    def read(cls, byte_iter: Iterator[bytes]):
        cls.consume_header(byte_iter)

        camera_id = byte_iter.read_int32()

        attribute = byte_iter.read_dict()

        return RenderCameraChunk(camera_id, attribute)

    def __bytes__(self):
        content = Int32.read(self.camera_id)

        content += Dict.read(self.attribute)

        return self.to_chunk_byte_format(content, b"")


class PaletteNoteChunk(Chunk):
    """Palette Note chunk class.

    int32	: num of color names

    // for each name
    {
    STRING	: color name
    }xN
    """

    id = b"NOTE"

    def __init__(self, color_names: list[str]):
        self.color_names = color_names

    @classmethod
    def read(cls, byte_iter: Iterator[bytes]):
        cls.consume_header(byte_iter)

        color_names = []

        num_color_names = byte_iter.read_int32()

        for _ in range(num_color_names):
            color_names.append(byte_iter.read_string())

        return PaletteNoteChunk(color_names)

    def __bytes__(self):
        content = Int32.read(len(self.color_names))

        for color_name in self.color_names:
            content += String.read(color_name)

        return self.to_chunk_byte_format(content, b"")


class IndexMapChunk(Chunk):
    """Index Map chunk class.

    size	: 256
    // for each index
    {
    int32	: palette index association
    }x256

    NOTE: it appears that the documentation on this one is wrong, as each
    palette index association seems to only be one byte.
    """

    id = b"IMAP"

    def __init__(self, palette_indices: list[int]):
        self.palette_indices = palette_indices

    @classmethod
    def read(cls, byte_iter: Iterator[bytes]):
        cls.consume_header(byte_iter)

        palette_indices = [
            int.from_bytes(byte_iter.read_byte(), "little") for _ in range(256)
        ]

        return IndexMapChunk(palette_indices)

    def __bytes__(self):
        content = b""

        for palette_index in self.palette_indices:
            content += palette_index.to_bytes(1, "little")

        return self.to_chunk_byte_format(content, b"")
