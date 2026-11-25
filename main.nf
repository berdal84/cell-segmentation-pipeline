nextflow.enable.types = true

process XLSX_TO_CSV {
    publishDir 'results/tmp', mode: 'copy'

    input:
    input_file: Path
    header: Integer
    
    output:
    file("${input_file.baseName}.csv")

    script:
    """
    XLSX_TO_CSV.py "${input_file.name}" "${input_file.baseName}.csv" ${header}
    """
}

process SPLIT_CHANNELS {
    publishDir 'results/tmp/splitted-channels', mode: 'copy'

    input:
    tuple (csv: Path, images: Bag<Path> )

    output:
    tifs: Set<Path> = files("*.tif")

    script:
    """
    SPLIT_CHANNELS.py --samples "${csv.name}" --output ./
    """
}

process SEGMENTATION {
    publishDir 'results/segmentation', mode: 'copy'
    maxForks 1 // cellpose is GPU intensive
    
    input:
    tuple (csv: Path, images: Bag<Path> )

    output:
    result = record(
        cp_masks: files("*_cp_masks"),
        cp_masks_colorized: files("*_cp_masks_colorized"),
        normalized: files("*_normalized"),
        results:  file("results.csv")
    )

    script:
    """
    SEGMENTATION.py \
        --samples "${csv}" \
        --output './' \
        --normalize \
        --percentile_min ${params.percentile_min} \
        --percentile_max ${params.percentile_max}
    """
}

params {
    
    // XLSX or CSV file, requires columns: path, C1, C2, C3, C4
    sample_file: Path

    // Optionnal, just in case your CSV file header is not at index 0
    sample_file_header_row: Integer = 0

    // The folder where you put your images in (their path in the spreadsheet must be relative to it)
    image_dir: Path

    // The marker to use for segmentation, must be a value present in C1, C2, C3 or C4 (ex: DAPI)
    marker: String

    percentile_min: Float = 0.0
    percentile_max: Float = 100.0

    // https://cellpose.readthedocs.io/en/latest/settings.html#diameter
    diameter:       Float = 30.0

    // https://cellpose.readthedocs.io/en/latest/settings.html#flow-threshold
    flow_threshold: Float = 0.0

    // https://cellpose.readthedocs.io/en/latest/settings.html#cellprob-threshold
    cellprob_threshold: Float = 0.0
}

workflow {
    ch_spreadsheet = channel.of(params.sample_file)

    if( params.sample_file.extension == "xlsx")
    {
        ch_spreadsheet = XLSX_TO_CSV(ch_spreadsheet, params.sample_file_header_row)
    }
    ch_spreadsheet.view()

    ch_images_to_split = ch_spreadsheet
        .flatMap { csv -> csv.splitCsv(header: true, strip: true, sep: ',') }
        .filter{ row -> !row.skip }
        .map { row -> params.image_dir.resolve(row.path) }
        .collect()
    ch_images_to_split.view()

    ch_split_channels = SPLIT_CHANNELS(
        ch_spreadsheet.combine(ch_images_to_split)
    )
    ch_split_channels.view()
    
    ch_images_to_segment = ch_split_channels
        .flatMap { paths ->
            paths.findAll {
                path -> path.name.contains(params.marker)
            }
    }
    ch_images_to_segment.view()

    ch_csv_to_segment = ch_images_to_segment
        .map { path -> "${path.name}" }
        .collectFile(
            name: 'image-to-segment.csv',
            storeDir: './results/tmp',
            seed: 'path',
            newLine: true
        )
    ch_csv_to_segment.view()

    SEGMENTATION(
        ch_csv_to_segment.combine(
            ch_images_to_segment.collect()
        )
    )
}
