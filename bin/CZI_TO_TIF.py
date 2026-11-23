#!/usr/bin/env python3
import argparse
import czifile # see https://pypi.org/project/czifile/
import numpy as np
import tifffile

from pathlib import Path

# parse arguments
parser = argparse.ArgumentParser(description="Convert a CZI to multiple TIF")
parser.add_argument("input_file" , type=Path, help="Path to the input *.czi file")
parser.add_argument("output_file", type=Path, help="Path to the output *.tif file")
parser.add_argument("markers", nargs="*", help="Optional marker names for each channel")
args = parser.parse_args()

print(f"Loading '{args.input_file}' ...")
with czifile.CziFile(args.input_file) as czi:
    image = czi.scenes[0]
    print("-- Dims:", image.dims, "Shape:", image.shape, "Dtype:", image.dtype)

    num_channels = image.sizes.get("C", 1)

    for channel_i in range(num_channels):

        # Use provided marker name if available, otherwise fall back to C1, C2, ...
        channel_name = args.markers[channel_i] if channel_i < len(args.markers) else f"C{channel_i + 1}"

        out_path = Path(f"{args.output_file}_{channel_name}.tif")

        # Extract only channel channel_i (or full image if there is no C axis)
        channel_view = image(C=channel_i) if "C" in image.dims else image
        channel_arr = np.squeeze(channel_view.asarray())

        # Write image
        out_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"Writing '{out_path}' (shape: {channel_arr.shape}) ...")
        tifffile.imwrite(out_path, channel_arr, compression='lzw')

print("-- end --")