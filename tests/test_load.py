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

        # Bytes will likely differ in order, but should all contain the same length/values
        if len(orig_bytes) != len(new_bytes):
            raise ValueError(
                f"Lengths of new ({len(new_bytes)}) "
                f"and original ({len(orig_bytes)}) "
                "files differ"
            )

        # TODO: check that same values are contained
