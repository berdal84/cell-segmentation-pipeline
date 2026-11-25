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
    tuple (czi_path: Path, channel_names: Iterable<String>)

    output:
    tifs: Set<Path> = files("${czi_path.baseName}*.tif")

    script:
    """
    SPLIT_CHANNELS.py "${czi_path.name}" "${czi_path.baseName}" ${channel_names.join(" ")}
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

    percentile_min: float       = 1
    percentile_max: float       = 100

    // https://cellpose.readthedocs.io/en/latest/settings.html#diameter
    diameter:       float       = 30

    // https://cellpose.readthedocs.io/en/latest/settings.html#flow-threshold
    flow_threshold: float       = 0

    // https://cellpose.readthedocs.io/en/latest/settings.html#cellprob-threshold
    cellprob_threshold: float   = 0
}

workflow {
    log.info "params.sample_file = ${params.sample_file}"
    log.info "params.image_dir   = ${params.image_dir}"

    ch_sample_file = channel.of(params.sample_file)
    // ch_samples_xslx.view()

    if( params.sample_file.extension == "xlsx")
    {
        ch_sample_file = XLSX_TO_CSV(ch_sample_file, params.sample_file_header_row)
    }
    
    // ch_samples_csv.view()

    // prepare inputs for SPLIT_CHANNELS
    ch_samples = ch_sample_file
        .flatMap { csv -> csv.splitCsv(header: true, strip: true, sep: ',') }
        .filter{ row -> !row.skip }
        .map { row ->

            def channel_names: Iterable<String> = [row.C1, row.C2, row.C3, row.C4]
                .withIndex()
                .collect { m, idx -> (m?.trim() ?: "C${idx + 1}").toString() }

            tuple(
                params.image_dir.resolve(row.path),
                channel_names
            )
        }

    ch_tifs = SPLIT_CHANNELS(ch_samples)
    
    ch_dapi_tifs = ch_tifs.flatMap { paths ->
        paths.findAll { path -> path.name.contains(params.marker) }
    }

    ch_segmentation_input_csv = ch_dapi_tifs
        .map { path -> "${path.name}" }
        .collectFile(
            name: 'segmentation-input.csv',
            storeDir: './results/tmp',
            seed: 'path',
            newLine: true
        )

    ch_segmentation_inputs = ch_segmentation_input_csv.combine(
        ch_dapi_tifs.collect()
    )
    SEGMENTATION(ch_segmentation_inputs)
}
