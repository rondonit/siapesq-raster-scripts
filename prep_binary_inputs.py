#!/usr/bin/env python3
"""Normaliza os GeoTIFFs de entrada para binário puro (1 = feição, 0 = fundo)."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import rasterio


def nodata_is_nan(value: float | int | None) -> bool:
    return isinstance(value, float) and math.isnan(value)


def to_binary_block(block: np.ndarray, nodata: float | int | None) -> np.ndarray:
    clean = np.zeros_like(block, dtype=np.uint8)
    if nodata is None or nodata_is_nan(nodata):
        clean[block > 0] = 1
    else:
        mask_valid = block != nodata
        clean[mask_valid & (block > 0)] = 1
    return clean


def normalize_file(src_path: Path, dst_path: Path) -> None:
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(src_path) as src:
        profile = src.profile
        profile.update(dtype="uint8", count=1, nodata=None, compress="deflate", predictor=2)
        profile.pop("blockxsize", None)
        profile.pop("blockysize", None)

        nodata = src.nodata
        print(f"Normalizando {src_path.name} (NoData={nodata}) -> {dst_path}")

        with rasterio.open(dst_path, "w", **profile) as dst:
            for _, window in src.block_windows(1):
                block = src.read(1, window=window, masked=False)
                dst.write(to_binary_block(block, nodata), 1, window=window)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Converte GeoTIFFs de estradas/rios para binário puro (1/0 sem NoData)."
    )
    parser.add_argument(
        "--source-dir",
        default="00_inputs_tiffs",
        help="Diretório com os GeoTIFFs originais enviados pelo colega.",
    )
    parser.add_argument(
        "--dest-dir",
        default="00_inputs_binary_ready",
        help="Diretório onde os TIFFs binários limpos serão gravados.",
    )
    args = parser.parse_args()

    src_dir = Path(args.source_dir)
    dst_dir = Path(args.dest_dir)
    if not src_dir.exists():
        raise SystemExit(f"Diretório fonte {src_dir} não existe.")

    tiffs = sorted(src_dir.glob("*.tif"))
    if not tiffs:
        raise SystemExit(f"Nenhum TIFF encontrado em {src_dir}")

    for tif in tiffs:
        normalize_file(tif, dst_dir / tif.name)


if __name__ == "__main__":
    main()
