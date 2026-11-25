#!/usr/bin/env python3
import argparse
import czifile # see https://pypi.org/project/czifile/
import numpy as np
import tifffile
import cv2
from pathlib import Path
import sys

# parse arguments
parser = argparse.ArgumentParser(description="Convert an image (*.czi or *.tif) to multiple TIF (one par channel).")
parser.add_argument("input_file" , type=Path, help="Path to the input *.czi file")
parser.add_argument("output_file", type=Path, help="Path to the output *.tif file")
parser.add_argument("markers", nargs="*", help="Optional marker names for each channel")
args = parser.parse_args()

input_file = Path(args.input_file)

print(f"Loading '{input_file}' ...")

def get_channel_name(channel_i):
    # Use provided marker name if available, otherwise fall back to C1, C2, ...
    channel_name = args.markers[channel_i] if channel_i < len(args.markers) else f"C{channel_i + 1}"
    return channel_name

match input_file.suffix:

    case ".czi":
        with czifile.CziFile(args.input_file) as czi:
            image = czi.scenes[0]
            print("-- Dims:", image.dims, "Shape:", image.shape, "Dtype:", image.dtype)
            num_channels = image.sizes.get("C", 1)

            for channel_i in range(num_channels):

                channel_name = get_channel_name(channel_i)
                out_path     = Path(f"{args.output_file}_{channel_name}.tif")
                channel_view = image(C=channel_i) if "C" in num_channels else image
                channel_arr  = np.squeeze(channel_view.asarray())
                    
                # Write image
                out_path.parent.mkdir(parents=True, exist_ok=True)
                print(f"Writing '{out_path}' (shape: {channel_arr.shape}) ...")
                tifffile.imwrite(out_path, channel_arr, compression='lzw')

    case ".tif":
        image = cv2.imread(input_file)
        if image is None:
            raise FileNotFoundError("Could not load TIFF image.")
        
        num_channels = image.shape[2]

        for channel_i in range(num_channels):

            channel_name = get_channel_name(channel_i)
            out_path     = Path(f"{args.output_file}_{channel_name}.tif")
            channel_arr  = image[:, :, channel_i]
                
            # Write image
            out_path.parent.mkdir(parents=True, exist_ok=True)
            print(f"Writing '{out_path}' (shape: {channel_arr.shape}) ...")
            tifffile.imwrite(out_path, channel_arr, compression='lzw')

    case _:
        raise RuntimeError(f"ERROR: *.czi or *.tif is expected. File format not handled: '{input_file.suffix}'.")

print("-- end --")