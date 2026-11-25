#!/usr/bin/env python3
import argparse
import czifile # see https://pypi.org/project/czifile/
import numpy as np
import tifffile
import cv2
from pathlib import Path
import sys
import pandas as pd

# parse arguments
parser = argparse.ArgumentParser(description="Convert an image (*.czi or *.tif) to multiple TIF (one par channel).")
parser.add_argument("--samples", type=Path, help="Path to a CSV listing samples (requires a column 'path')")
parser.add_argument("--output" , type=Path, help="Path to the desired output path")
args = parser.parse_args()

output = Path(args.output)

# Load CSV
print(f"Loading {args.samples} ...")
samples = pd.read_csv(args.samples)
print(f"Found {len(samples)} sample(s)")

def get_channel_name(sample, channel_i):

    column_name = f"C{channel_i + 1}"

    has_col = column_name in samples.columns
    if not has_col:
        return column_name
    
    marker_name = sample[column_name]
    if marker_name:
        return f"{column_name}_{marker_name}"
    return column_name

# Iterate over Samples
for index, sample in samples.iterrows():
    print(f"Processing sample {index}/{len(samples)} ...")
    print(f"sample: {sample}")
    image_path = Path(sample.path)

    print(f"Loading '{image_path}' ...")

    match image_path.suffix:

        case ".czi":
            with czifile.CziFile(str(image_path)) as czi:
                image = czi.scenes[0]
                print("-- Dims:", image.dims, "Shape:", image.shape, "Dtype:", image.dtype)
                num_channels = image.sizes.get("C", 1)

                for channel_i in range(num_channels):

                    channel_name = get_channel_name(sample, channel_i)
                    out_path     = output / f"{image_path.stem}_{channel_name}.tif"
                    channel_view = image(C=channel_i) if "C" in image.dims else image
                    channel_arr  = np.squeeze(channel_view.asarray())
                        
                    # Write image
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    print(f"Writing '{out_path}' (shape: {channel_arr.shape}) ...")
                    tifffile.imwrite(out_path, channel_arr, compression='lzw')

        case ".tif":
            image = cv2.imread(image_path)
            if image is None:
                raise FileNotFoundError("Could not load TIFF image.")
            
            num_channels = image.shape[2]

            for channel_i in range(num_channels):

                channel_name = get_channel_name(sample, channel_i)
                out_path     = output / f"{image_path.stem}_{channel_name}.tif"
                channel_arr  = image[:, :, channel_i]
                    
                # Write image
                out_path.parent.mkdir(parents=True, exist_ok=True)
                print(f"Writing '{out_path}' (shape: {channel_arr.shape}) ...")
                tifffile.imwrite(out_path, channel_arr, compression='lzw')

        case _:
            raise RuntimeError(f"ERROR: *.czi or *.tif is expected. File format not handled: '{image_path.suffix}'.")

print("-- end --")