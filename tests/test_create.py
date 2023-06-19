import pytest
import os
import voxutil


def test_create_basic():
    voxfile = voxutil.VoxFile(
        150,
        voxutil.voxfile.MainChunk(
            None,
            [
                (
                    voxutil.voxfile.SizeChunk((10, 10, 10)),
                    voxutil.voxfile.XYZIChunk([(1, 1, 1, 2)]),
                )
            ],
            None,
            [],
            [],
            [],
            [],
            [],
            None,
            None,
        ),
    )

    voxfile.write("/tmp/test.vox")
