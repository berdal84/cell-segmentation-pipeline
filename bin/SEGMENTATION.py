#!/usr/bin/env python3
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from cellpose import models, io, utils
import cv2

def clamp( x, x_min: float = 0.0, x_max: float = 1.0 ):
    """
    x is modified in-place.
    """
    return np.clip(x, x_min, x_max, out=x)

def remap(x: np.ndarray, xmin: float, xmax: float ):
    """
    Remap x to make sure xmin and xmax becomes 0.0, and 1.0 respectively, x < 0.0 or x > 1.0 is still possible (see remap_clamped).
    x is modified in-place.
    """
    x -= xmin
    x /= (xmax - xmin)
    return x

def remap_clamped(x: np.ndarray, x_min: float, x_max: float ):
    """
    Remap x to make sure xmin and xmax becomes 0.0, and 1.0 respectively, and ensure x is in [0.0, 1.0].
    x is modified in-place.
    """
    return clamp(
        remap(x, x_min, x_max), 0.0, 1.0)

def normalize_at_percentile(x: np.ndarray, percentile_min: float = 1.0, percentile_max: float = 99.0):
    """
        Filter channel using percentile_min/percentile_max and remap the result to a [0.0, 1.0] range.
        x is modified in-place.
    """
    [x_min, x_max] = np.percentile(x, [percentile_min, percentile_max] )
    return remap_clamped(x, x_min, x_max ) # in-place

# parse arguments
parser = argparse.ArgumentParser(description="Segmentation Tool (uses cellpose to segmentize cell microscopy images)")
parser.add_argument("--samples" , type=Path, help="Path to a CSV listing samples (requires a column 'path')")
parser.add_argument("-o", "--output", default="./results/segmentation", type=Path, help="Path to the desired output path")
parser.add_argument("--use_gpu", default=False,  action=argparse.BooleanOptionalAction)
parser.add_argument('--normalize', action=argparse.BooleanOptionalAction, default=False, help="When true, the image is normalized globally (outside cellpose) using the two percentiles.")
parser.add_argument('--save_normalized', action=argparse.BooleanOptionalAction, default=True, help="If normalization is ON, when this argument is ON it will save the normalized images to disk. ON by default since it helps to understand the results.")
parser.add_argument('--percentile_min', type=float, default=1)
parser.add_argument('--percentile_max', type=float, default=99)
parser.add_argument('--flow_threshold', type=float, default=0.0)
parser.add_argument('--cellprob_threshold', type=float, default=0.0)
parser.add_argument('--diameter', type=float, default=None)
args = parser.parse_args()

output = Path(args.output)

# Load CSV
print(f"Loading {args.samples} ...")
samples = pd.read_csv(args.samples)
print(f"Found {len(samples)} sample(s)")

# Iterate over Samples
results = samples.copy()
results['cell_count'] = 0
print("Initializing Cellpose Model ...")
cp_model = models.CellposeModel(
    gpu=args.use_gpu,
    pretrained_model='cpsam'
)
for index, sample in enumerate(samples.itertuples(), start=1):
    print(f"Processing sample {index}/{len(samples)} ...")
    print(f"sample: {sample}")
    image_path = Path(sample.path)
    image = cv2.imread(image_path )

    if image is None:
        raise RuntimeError(f"Unable to load {image_path}!")

    # convert to float32
    if image.dtype == np.uint8:
        print("Image type is uint8, converting to float32 ...")
        image = image.astype(np.float32) / 255.0
    elif image.dtype == np.uint16:
        print("Image type is uint16, converting to float32 ...")
        image = image.astype(np.float32) / 65535.0
    elif np.issubdtype(image.dtype, np.floating):
        print("Image type is floating, ensures is float32 ...")
        image = image.astype(np.float32)
    else:
        raise ValueError(f"Unsupported image dtype: {image.dtype}, cannot convert to float32.")

    if (args.normalize):
        print(f"Normalizing at percentiles: min={args.percentile_min}, max={args.percentile_max} ...")
        image = normalize_at_percentile(image, args.percentile_min, args.percentile_max)
        if (args.save_normalized):
            normalized_image_path = output / f"{image_path.stem}_normalized.tif"
            normalized_image_path.parent.mkdir(parents=True, exist_ok=True)
            print(f"Writing {normalized_image_path} ...")
            cv2.imwrite(normalized_image_path, image, [cv2.IMWRITE_TIFF_COMPRESSION, cv2.IMWRITE_TIFF_COMPRESSION_LZMA])

    print("Running cellpose ...")
    try:
        mask, flows, styles = cp_model.eval(
            image,
            diameter=args.diameter,  # None = auto-estimate
            flow_threshold=args.flow_threshold,
            cellprob_threshold=args.cellprob_threshold,
            normalize=False, # We do normalize if --normalize is set outside cellpose
        )
    except Exception as e:
        print(f"An error occurred during cp_model.eval(): {e}")
    
    cell_count = int(mask.max())
    results.loc[index, 'cell_count'] = cell_count
    print(f"Cellpose found {cell_count} cell(s).")

    def random_label_cmap_image(mask, seed=None):
        range          = np.random.default_rng(seed)
        colors         = range.integers(50, 256, size=(mask.max()+1, 3), dtype=np.uint8) # min is 50, we don't want dark colors, background is dark too
        colors[0]      = (0,0,0) # black bg!
        return colors[mask]
    
    mask_colorized  = random_label_cmap_image(mask)
    cp_masks_suffix = "_cp_masks"
    mask_colorized_path = output / f"{image_path.stem}{cp_masks_suffix}_colorized.tif"
    mask_colorized_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Writing {mask_colorized_path} ...")
    cv2.imwrite(mask_colorized_path, mask_colorized, [cv2.IMWRITE_TIFF_COMPRESSION, cv2.IMWRITE_TIFF_COMPRESSION_LZMA])

    # Save masks (using cellpose method)
    # - precise method, it uses 16 or 32bits when needed, cellpose code switches from PNG to TGA when necessary.
    # - default image viewers won't display well 16/32bits images, open with FiJi or other softwares.
    io.save_masks(
        images=[image], masks=[mask], flows=[flows],
        file_names=[image_path.stem],
        suffix=cp_masks_suffix,
        savedir=str(output),
        tif=True, png=False, # we always want the same format
        )
    
    print(f"Processing sample {index}/{len(samples)} DONE")

# Write result as CSV
results_path = output / "segmentation.csv"
results_path.parent.mkdir(exist_ok=True, parents=True)
print(f"Writting results in {results_path} ...")
results.to_csv(results_path, index=None)
