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

    voxfile.write("/tmp/test_create_basic.vox")


def test_create_volume():
    volume = voxutil.Volume((10, 10, 10))
    volume.set((1, 1, 1), voxutil.Color(255, 0, 0))
    voxfile = volume.to_voxfile()
    voxfile.write("/tmp/test_create_volume.vox")


def test_create_volume_palette():
    volume = voxutil.Volume((10, 10, 10))
    volume.set((1, 1, 1), voxutil.Color(255, 0, 0))
    volume.set((1, 1, 2), voxutil.Color(0, 255, 0))
    volume.set((1, 1, 3), voxutil.Color(0, 0, 255))
    voxfile = volume.to_voxfile()
    voxfile.write("/tmp/test_create_volume_palette.vox")
