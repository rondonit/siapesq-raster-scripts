#!/usr/bin/env bash
set -euo pipefail

source .venv/bin/activate

INPUT_DIR="00_inputs_binary_ready"
OUTPUT_DIR="03_dist_map_tiles"
mkdir -p "${OUTPUT_DIR}"

run_dist() {
    local stem="$1"
    local input_path="${INPUT_DIR}/${stem}.tif"
    local output_path="${OUTPUT_DIR}/${stem}_dist.tif"

    if [[ ! -f "${input_path}" ]]; then
        echo "Aviso: ${input_path} não encontrado. Execute prep_binary_inputs.py antes."
        return 1
    fi

    python dist_map.py --in "${input_path}" --out "${output_path}" \
        --tile-size 4096 --tile-padding 1024
}

run_dist "estradas_rs_final"
run_dist "estradas_sc_final"
run_dist "estradas_parana_final"
run_dist "rios_rs_final"
run_dist "rios_sc_final"
run_dist "rios_parana_final"
