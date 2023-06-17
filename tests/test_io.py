import pytest
import os
import voxutil

# find all models
MODEL_PATHS = []
for root, dirs, files in os.walk("tests/models"):
    for file in files:
        if file.endswith(".vox"):
            MODEL_PATHS.append(os.path.join(root, file))


@pytest.mark.parametrize("model_path", MODEL_PATHS)
def test_read(model_path):
    voxutil.VoxFile.read(model_path)


@pytest.mark.parametrize("model_path", MODEL_PATHS)
def test_read_write(model_path):
    tmp_path = os.path.join("/tmp", os.path.basename(model_path))

    vox_file = voxutil.VoxFile.read(model_path)

    vox_file.write(tmp_path)

    # make sure vox file generated is identical
    with open(model_path, "rb") as orig_file, open(tmp_path, "rb") as new_file:
        orig_bytes = orig_file.read()
        new_bytes = new_file.read()

        if orig_bytes != new_bytes:
            if len(orig_bytes) != len(new_bytes):
                raise ValueError(
                    f"original file length ({len(orig_bytes)}) != "
                    f"new file length ({len(new_bytes)})"
                )

            # find first differing byte
            index = 0
            while True:
                if orig_bytes[index] != new_bytes[index]:
                    raise ValueError(f"Files differ at {hex(index)}")

                index += 1