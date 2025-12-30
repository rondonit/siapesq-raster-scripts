#!/usr/bin/env bash
set -euo pipefail

INPUT_DIR="04_dist_map_masked"
OUTPUT_DIR="05_dist_map_masked_regridded_1km"
mkdir -p "${OUTPUT_DIR}"

resample_to_1km() {
    local stem="$1"
    local input_path="${INPUT_DIR}/${stem}_dist_masked.tif"
    local output_path="${OUTPUT_DIR}/${stem}_dist_masked_1km.tif"

    if [[ ! -f "${input_path}" ]]; then
        echo "Aviso: ${input_path} não encontrado. Pulando..."
        return
    fi

    echo "Reamostrando ${input_path} -> ${output_path}"
    gdalwarp -overwrite -of GTiff \
        --config GDAL_CACHEMAX 1024 -wm 1024 \
        -multi -r near \
        -tr 1000 1000 \
        "${input_path}" "${output_path}"
}

resample_to_1km "estradas_rs_final"
resample_to_1km "estradas_sc_final"
resample_to_1km "estradas_parana_final"
resample_to_1km "rios_rs_final"
resample_to_1km "rios_sc_final"
resample_to_1km "rios_parana_final"
