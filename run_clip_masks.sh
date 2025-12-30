#!/usr/bin/env bash
set -euo pipefail

INPUT_DIR="03_dist_map_tiles"
MASK_DIR="02_shapefiles_epsg31997"
OUTPUT_DIR="04_dist_map_masked"
mkdir -p "${OUTPUT_DIR}"

clip_raster() {
    local base_name="$1"
    local mask_file="$2"
    local layer_name="$3"
    local input_path="${INPUT_DIR}/${base_name}_dist.tif"
    local output_path="${OUTPUT_DIR}/${base_name}_dist_masked.tif"

    if [[ ! -f "${input_path}" ]]; then
        echo "Aviso: ${input_path} não encontrado. Pulando..."
        return
    fi

    echo "Recortando ${input_path} com ${mask_file}"
    gdalwarp -overwrite -of GTiff \
        --config GDAL_CACHEMAX 1024 -wm 1024 -multi \
        -cutline "${mask_file}" -cl "${layer_name}" \
        -crop_to_cutline -dstnodata -9999 \
        "${input_path}" "${output_path}"
}

# Estradas
clip_raster "estradas_rs_final" "${MASK_DIR}/RS_UF_2024_epsg31997.shp" "RS_UF_2024_epsg31997"
clip_raster "estradas_sc_final" "${MASK_DIR}/SC_UF_2024_epsg31997.shp" "SC_UF_2024_epsg31997"
clip_raster "estradas_parana_final" "${MASK_DIR}/PR_UF_2024_epsg31997.shp" "PR_UF_2024_epsg31997"

# Rios
clip_raster "rios_rs_final" "${MASK_DIR}/RS_UF_2024_epsg31997.shp" "RS_UF_2024_epsg31997"
clip_raster "rios_sc_final" "${MASK_DIR}/SC_UF_2024_epsg31997.shp" "SC_UF_2024_epsg31997"
clip_raster "rios_parana_final" "${MASK_DIR}/PR_UF_2024_epsg31997.shp" "PR_UF_2024_epsg31997"
