#!/usr/bin/env bash
set -euo pipefail

INPUT_DIR="04_dist_map_masked"
OUTPUT_DIR="06_dist_map_mosaics"
mkdir -p "${OUTPUT_DIR}"

build_mosaic() {
    local output_stem="$1"
    shift
    local vrt_path="${OUTPUT_DIR}/${output_stem}.vrt"
    local tif_path="${OUTPUT_DIR}/${output_stem}.tif"

    for src in "$@"; do
        if [[ ! -f "${src}" ]]; then
            echo "Erro: arquivo ${src} não encontrado."
            exit 1
        fi
    done

    echo "Montando VRT ${vrt_path}"
    gdalbuildvrt -overwrite -srcnodata -9999 -vrtnodata -9999 "${vrt_path}" "$@"

    echo "Convertendo para GeoTIFF ${tif_path}"
    gdal_translate -of GTiff -co COMPRESS=LZW -a_nodata -9999 "${vrt_path}" "${tif_path}"
}

build_mosaic "estradas_dist_regiao_sul" \
    "${INPUT_DIR}/estradas_rs_final_dist_masked.tif" \
    "${INPUT_DIR}/estradas_sc_final_dist_masked.tif" \
    "${INPUT_DIR}/estradas_parana_final_dist_masked.tif"

build_mosaic "rios_dist_regiao_sul" \
    "${INPUT_DIR}/rios_rs_final_dist_masked.tif" \
    "${INPUT_DIR}/rios_sc_final_dist_masked.tif" \
    "${INPUT_DIR}/rios_parana_final_dist_masked.tif"
