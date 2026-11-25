# Cell Segmentation Pipeline

This is a Nextflow pipeline for segmentation of cell microscopy images (*.czi or *.tif only) using Cellpose v4.

# Usage

## Prerequisites

- Nextflow v26+

## Data Preparation

Requires an excel file listing the samples with the following columns: `path`, `C1`, `C2`, `C3`, `C4`.
- `path`: should contain the path to the image (relative to `image_dir`)
- `C1`, `C2`, `C3`, `C4`: should contain the name of the marker (ex: `DAPI`) for that channel, or nothing.

Example:

|path|C1|C2|C3|C4|
| :--- | :--- | :--- | :--- | :--- 
|folder1/imageB.czi|CRX|KI67|DAPI|
|folder2/imageA.czi|KI67|DAPI|

Note: it's fine if cells are empty, default name will be the column (C1, C2, etc.)
## Run


```
nextflow run berdal84/cell-segmentation-pipeline [-r <tag/branch>] \
    --sample_file="path/to/your/samples.(xslx|csv)" \
    --image_dir="path/to/your/images" \
    --marker="DAPI"
```

Note: in case your samples header is not in the first row, you can specify it using `--sample_file_header_row=<header-row>`.

## Results

Pipeline will output its results in the `./results` folder, relative to the directory you launched it.

# Notes:

I do not plan to accept any contribution.

Things I plan to do:

- [x] Handle *.csv directly (would skip XLSX_to_CSV step)
- [x] Handle *.tif directly (would skip CZI_to_TIF step)
- [x] Generate a *.csv file to summarize the results.
- [ ] SPLIT_CHANNELS should process N images, it is quite fast, so I should give a file list (ex: split-channels.csv).
