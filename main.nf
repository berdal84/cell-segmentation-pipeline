nextflow.enable.types = true

process XLSX_TO_CSV {
    publishDir 'results', mode: 'copy'

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

process CZI_TO_TIF {
    publishDir 'results/images', mode: 'copy'

    input:
    tuple (czi_path: Path, channel_names: Iterable<String>)

    output:
    tifs: Set<Path> = files("${czi_path.baseName}*.tif")

    script:
    """
    CZI_TO_TIF.py "${czi_path.name}" "${czi_path.baseName}" ${channel_names.join(" ")}
    """
}

process SEGMENTATION {
    publishDir 'results/images', mode: 'copy'
    maxForks 1 // cellpose is GPU intensive
    
    input:
    tif_path: Path

    output:
    cellpose_files: Set<Path> = files("${tif_path.baseName}_cp*")

    script:
    """
    # documentation: https://cellpose.readthedocs.io/en/latest/cli.html
    python -m cellpose \
        --image_path "${tif_path.name}" \
        --output_name="${tif_path.name}_cp" \
        --diameter ${50*10} \
        --save_tif \
        --verbose \
        --use_gpu
    """
}

params {
    sample_file: Path
    sample_file_header_row: Integer
    image_dir: Path
    marker_to_segmentize: String
}

workflow {
    log.info "params.sample_file = ${params.sample_file}"
    log.info "params.image_dir   = ${params.image_dir}"

    ch_samples_xslx = channel.of(params.sample_file)
    // ch_samples_xslx.view()

    ch_samples_csv = XLSX_TO_CSV(ch_samples_xslx, params.sample_file_header_row)
    // ch_samples_csv.view()

    // prepare inputs for CZI_to_TIF
    ch_samples = ch_samples_csv
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

    ch_tifs = CZI_TO_TIF(ch_samples)
    
    ch_dapi_tifs = ch_tifs.flatMap { paths ->
        paths.findAll { path -> path.name.contains(params.marker_to_segmentize) }
    }
    // ch_dapi_tifs.view()

    SEGMENTATION(ch_dapi_tifs)
}
