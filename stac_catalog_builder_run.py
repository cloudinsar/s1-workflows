from typing import Union

import pprint
import tempfile
from datetime import datetime
from pathlib import Path

# run pip install -e . in the root directory to install this package
import stacbuilder

containing_folder = Path(__file__).parent


def main(
        root_dir: Union[str, Path],
        tiffs_glob: str = "*2images_slv*.tif",
        collection_filename: str = "collection.json",
        collection_config_path: Union[str, Path] = containing_folder
                                                   / "stac-catalog-builder-config-collection-slv.json",
):
    assert " " not in root_dir
    root_dir = Path(root_dir.rstrip("/")).absolute()
    collection_config_path = Path(collection_config_path)
    assert collection_config_path.exists()

    # Input Paths
    tiff_input_path = Path(root_dir).absolute()

    # Output Paths with date-time stamp
    output_path = Path(
        tempfile.mkdtemp(
            prefix="stac-" + datetime.now().strftime("%Y-%m-%d_%H-%M") + "-"
        )
    )
    # output_path = Path(os.path.abspath(containing_folder / "tmp/"))
    print(f"{output_path=}")

    # list input files
    input_files = stacbuilder.list_input_files(
        glob=tiffs_glob, input_dir=tiff_input_path, max_files=None
    )
    assert input_files
    print(f"Found {len(input_files)} input files. 5 first files:")
    for i in input_files[:5]:
        print(i)

    # list meta data
    asset_metadata = stacbuilder.list_asset_metadata(
        collection_config_path=collection_config_path,
        glob=tiffs_glob,
        input_dir=tiff_input_path,
        max_files=5,
    )
    for k in asset_metadata:
        pprint.pprint(k.to_dict())

    # list items
    stac_items, failed_files = stacbuilder.list_stac_items(
        collection_config_path=collection_config_path,
        glob=tiffs_glob,
        input_dir=tiff_input_path,
        max_files=0,
    )
    print(f"Found {len(stac_items)} STAC items")
    if failed_files:
        print(f"Failed files: {failed_files}")

    print("First stac item:")
    print(stac_items[0])

    # if os.path.exists(output_path):
    #     rmtree(output_path)  # this accidentally deleted my source repo once

    # build collection
    stacbuilder.build_collection(
        collection_config_path=collection_config_path,
        glob=tiffs_glob,
        input_dir=tiff_input_path,
        output_dir=output_path,
        # overwrite=overwrite,
    )

    # show collection
    stacbuilder.load_collection(collection_file=output_path / collection_filename)

    # validate collection
    stacbuilder.validate_collection(
        collection_file=output_path / collection_filename,
    )


if __name__ == "__main__":
    main(".")
