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
        return int.from_bytes(self.peek_bytes(4), "little", signed=True)

    def read_int32(self) -> int:
        """Read a 32-bit integer."""
        int32 = self.peek_int32()
        self.index += 4
        return int32

    def read_string(self) -> str:
        """Read a string."""
        length = self.read_int32()
        return self.read_bytes(length).decode("utf-8")

    def read_dict(self) -> dict:
        """Read a dictionary."""
        length = self.read_int32()
        dict_ = {}
        for _ in range(length):
            key = self.read_string()
            value = self.read_string()
            dict_[key] = value
        return dict_

    def read_rotation(self) -> int:
        """Read a rotation."""
        return ord(self.read_byte())


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
            file_iter = FileIter(f.read())

            header = file_iter.read_bytes(4)
            if header != b"VOX ":
                raise ValueError("Invalid .vox file header.")

            version = file_iter.read_int32()

            main = MainChunk.read(file_iter)

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
    def consume_header(cls, file_iter: FileIter):
        """Check that the next four bytes in the given byte iterator match the chunk ID."""
        id = file_iter.read_bytes(4)
        if id != cls.id:
            raise ValueError(f"Invalid chunk ID: {id}; expected {cls.id}")

        file_iter.read_int32()  # consume chunk content size
        file_iter.read_int32()  # consume child chunk size


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

    def __init__(
        self,
        pack: Optional["PackChunk"],
        models: list[tuple["SizeChunk", "XYZIChunk"]],
        palette: Optional["PaletteChunk"],
        transforms: list["TransformChunk"],
        groups: list["GroupChunk"],
        shapes: list["ShapeChunk"],
        materials: list["MaterialChunk"],
        render_objects: list["RenderObjectChunk"],
        render_cameras: list["RenderCameraChunk"],
        palette_note: Optional["PaletteNoteChunk"],
        index_map: Optional["IndexMapChunk"],
    ):
        """MainChunk constructor."""
        self.pack = pack
        self.models = models
        self.palette = palette
        self.transforms = transforms
        self.groups = groups
        self.shapes = shapes
        self.materials = materials
        self.render_object = render_objects
        self.render_camera = render_cameras
        self.palette_note = palette_note
        self.index_map = index_map

    @classmethod
    def read(cls, file_iter: FileIter) -> "MainChunk":
        """Read a main chunk from the given byte iterator."""
        cls.consume_header(file_iter)

        pack = None
        models = []
        palette = None
        transforms = []
        groups = []
        shapes = []
        materials = []
        layers = []
        render_objects = []
        render_cameras = []
        palette_note = None
        index_map = None

        while file_iter:
            id = file_iter.peek_bytes(4)

            if id == PackChunk.id:
                pack = PackChunk.read(file_iter)
            elif id == SizeChunk.id:
                size_chunk = SizeChunk.read(file_iter)

                # assume next chunk is XYZI chunk
                id = file_iter.peek_bytes(4)
                if id != XYZIChunk.id:
                    raise ValueError(
                        f"Invalid chunk ID: {id}; expected {XYZIChunk.id} following {SizeChunk.id}"
                    )
                xyzi_chunk = XYZIChunk.read(file_iter)

                models += [(size_chunk, xyzi_chunk)]
            elif id == PaletteChunk.id:
                palette = PaletteChunk.read(file_iter)
            elif id == TransformChunk.id:
                transform_chunk = TransformChunk.read(file_iter)
                transforms += [transform_chunk]
            elif id == GroupChunk.id:
                group_chunk = GroupChunk.read(file_iter)
                groups += [group_chunk]
            elif id == ShapeChunk.id:
                shape_chunk = ShapeChunk.read(file_iter)
                shapes += [shape_chunk]
            elif id == MaterialChunk.id:
                material_chunk = MaterialChunk.read(file_iter)
                materials += [material_chunk]
            elif id == LayerChunk.id:
                layer_chunk = LayerChunk.read(file_iter)
                layers += [layer_chunk]
            elif id == RenderObjectChunk.id:
                render_object = RenderObjectChunk.read(file_iter)
                render_objects += [render_objects]
            elif id == RenderCameraChunk.id:
                render_camera = RenderCameraChunk.read(file_iter)
                render_cameras += [render_camera]
            elif id == PaletteNoteChunk.id:
                palette_note = PaletteNoteChunk.read(file_iter)
            elif id == IndexMapChunk.id:
                index_map = IndexMapChunk.read(file_iter)
            else:
                raise ValueError(f"Invalid chunk ID: {id}")

        return MainChunk(
            pack,
            models,
            palette,
            transforms,
            groups,
            shapes,
            materials,
            render_objects,
            render_cameras,
            palette_note,
            index_map,
        )


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
    def read(cls, file_iter: FileIter) -> "PackChunk":
        """Read a pack chunk from the given byte iterator."""
        cls.consume_header(file_iter)

        num_models = file_iter.read_int32()

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
    def read(cls, file_iter: FileIter) -> "SizeChunk":
        cls.consume_header(file_iter)

        x = file_iter.read_int32()
        y = file_iter.read_int32()
        z = file_iter.read_int32()

        return SizeChunk((x, y, z))


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
    def read(cls, file_iter: FileIter) -> "XYZIChunk":
        cls.consume_header(file_iter)

        num_voxels = file_iter.read_int32()

        voxels = []
        for _ in range(num_voxels):
            x = file_iter.read_byte()
            y = file_iter.read_byte()
            z = file_iter.read_byte()
            color_index = file_iter.read_byte()
            voxels += [(x, y, z, color_index)]

        return XYZIChunk(voxels)


class PaletteChunk(Chunk):
    """Palette chunk class.

    -------------------------------------------------------------------------------
    # Bytes  | Type       | Value
    -------------------------------------------------------------------------------
    4 x 256  | int        | (R, G, B, A) : 1 byte for each component
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
    def read(cls, file_iter: FileIter) -> "PaletteChunk":
        cls.consume_header(file_iter)

        palette = [(0, 0, 0, 0)]
        for _ in range(255):
            r = file_iter.read_byte()
            g = file_iter.read_byte()
            b = file_iter.read_byte()
            a = file_iter.read_byte()
            palette += [(r, g, b, a)]

        return PaletteChunk(palette)


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
    def read(cls, file_iter: FileIter) -> "TransformChunk":
        cls.consume_header(file_iter)

        node_id = file_iter.read_int32()
        attributes = file_iter.read_dict()
        child_node_id = file_iter.read_int32()
        reserved_id = file_iter.read_int32()
        if reserved_id != -1:
            raise ValueError(f"Invalid reserved id: {reserved_id}")
        layer_id = file_iter.read_int32()
        num_frames = file_iter.read_int32()

        frames = []
        for _ in range(num_frames):
            frame_attributes = file_iter.read_dict()
            frames += [frame_attributes]

        return TransformChunk(node_id, attributes, child_node_id, layer_id, frames)


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
    def read(cls, file_iter: FileIter) -> "GroupChunk":
        cls.consume_header(file_iter)

        node_id = file_iter.read_int32()
        attributes = file_iter.read_dict()
        num_children = file_iter.read_int32()

        child_node_ids = []
        for _ in range(num_children):
            child_node_id = file_iter.read_int32()
            child_node_ids += [child_node_id]

        return GroupChunk(node_id, attributes, child_node_ids)


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
    def read(cls, file_iter: FileIter) -> "ShapeChunk":
        cls.consume_header(file_iter)

        node_id = file_iter.read_int32()
        attributes = file_iter.read_dict()
        num_models = file_iter.read_int32()

        models = []
        for _ in range(num_models):
            model_id = file_iter.read_int32()
            model_attributes = file_iter.read_dict()
            models += [(model_id, model_attributes)]

        return ShapeChunk(node_id, attributes, models)


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
    def read(cls, file_iter : FileIter):
        cls.consume_header(file_iter)

        material_id = file_iter.read_int32()

        properties = file_iter.read_dict()

        return MaterialChunk(material_id, properties)


class LayerChunk(Chunk):
    """Layer chunk class.

    int32	: layer id
    DICT	: layer attribute
        (_name : string)
        (_hidden : 0/1)
    int32	: reserved id, must be -1
    """

    id = b"LAYR"

    def __init__(self, layer_id : int, attribute: dict):
        self.layer_id = layer_id
        self.attribute = attribute

    @classmethod
    def read(cls, file_iter: FileIter):
        cls.consume_header()

        layer_id = file_iter.read_int32()

        attribute = file_iter.read_dict()

        reserved_id = file_iter.read_int32()
        if reserved_id != -1:
            raise ValueError(f"Invalid reserved id: {reserved_id}")
        
        return LayerChunk(layer_id, attribute)


class RenderObjectChunk(Chunk):
    """Render Object chunk class.

    DICT	: rendering attributes
    """

    id = b"rOBJ"

    def __init__(self, attributes: dict):
        self.attributes = attributes

    @classmethod
    def read(cls, file_iter: FileIter):
        cls.consume_header()

        attributes = file_iter.read_dict()

        return RenderObjectChunk(attributes)


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
    def read(cls, file_iter: FileIter):
        cls.consume_header()

        camera_id = file_iter.read_int32()

        attribute = file_iter.read_dict()

        return RenderCameraChunk(camera_id, attribute)


class PaletteNoteChunk(Chunk):
    """Palette Note chunk class.

    int32	: num of color names

    // for each name
    {
    STRING	: color name
    }xN
    """

    id = b"NOTE"


class IndexMapChunk(Chunk):
    """Index Map chunk class.

    size	: 256
    // for each index
    {
    int32	: palette index association
    }x256
    """

    id = b"IMAP"
