#!/usr/bin/env python3
"""Gera um raster de distância aos rios (pixels == 1) usando pouca RAM."""

from __future__ import annotations

import argparse
import math
import tempfile
from pathlib import Path
from typing import Iterator, Tuple

import numpy as np
import rasterio
from rasterio.transform import Affine
from rasterio.windows import Window
from rasterio.crs import CRS
from scipy.ndimage import distance_transform_edt


def window_slices(window: Window) -> tuple[slice, slice]:
    return (
        slice(window.row_off, window.row_off + window.height),
        slice(window.col_off, window.col_off + window.width),
    )


def allocate_memmap(tmpdir: Path, name: str, dtype: np.dtype, shape: tuple[int, int]) -> np.memmap:
    path = tmpdir / name
    return np.memmap(path, dtype=dtype, mode="w+", shape=shape)


class ProgressPrinter:
    """Minimal stdout progress helper to avoid verbose logs on large rasters."""

    def __init__(self, label: str, total_steps: int, mode: str = "percent") -> None:
        self.label = label
        self.total = max(total_steps, 1)
        self.current = 0
        self.mode = mode
        self.last_value = -1
        self._print_status(force=True)

    def _print_status(self, force: bool = False) -> None:
        if self.mode == "count":
            value = min(self.current, self.total)
            if force or value != self.last_value:
                print(f"{self.label}: {value}/{self.total}")
                self.last_value = value
        else:
            percent = int(self.current * 100 / self.total)
            if force or percent != self.last_value:
                print(f"{self.label}: {percent}%")
                self.last_value = percent

    def increment(self, steps: int = 1) -> None:
        self.current += steps
        self._print_status()

    def finish(self) -> None:
        self.current = self.total
        target = self.total if self.mode == "count" else 100
        already_reported = self.last_value == target
        self._print_status(force=not already_reported)


def format_crs(crs: CRS | None) -> str:
    if crs is None or not crs:
        return "CRS não definido"
    epsg = crs.to_epsg()
    if epsg:
        return f"EPSG:{epsg}"
    return crs.to_string() or crs.to_wkt()


def estimate_total_blocks(src: rasterio.io.DatasetReader) -> int:
    block_shapes = src.block_shapes
    if not block_shapes:
        return 1
    block_h, block_w = block_shapes[0]
    block_h = block_h or src.height
    block_w = block_w or src.width
    rows = math.ceil(src.height / block_h)
    cols = math.ceil(src.width / block_w)
    return max(rows * cols, 1)


def build_binary_arrays(
    src: rasterio.io.DatasetReader,
    tmpdir: Path,
    progress: ProgressPrinter | None = None,
) -> tuple[np.memmap, np.memmap]:
    """Converte o raster em duas matrizes memmap: binária (rios=0) e máscara de válidos."""
    shape = (src.height, src.width)
    rivers_zero = allocate_memmap(tmpdir, "rivers.uint8", np.uint8, shape)
    valid_mask = allocate_memmap(tmpdir, "valid.bool", np.bool_, shape)
    nodata = src.nodata

    for _, window in src.block_windows(1):
        row_slice, col_slice = window_slices(window)
        block = src.read(1, window=window, masked=False)

        if nodata is None or nodata in (0, 1):
            mask = np.ones(block.shape, dtype=bool)
        else:
            mask = block != nodata

        valid_mask[row_slice, col_slice] = mask

        rivers_zero[row_slice, col_slice] = np.where((block == 1) & mask, 0, 1).astype(np.uint8, copy=False)
        if progress is not None:
            progress.increment()

    rivers_zero.flush()
    valid_mask.flush()
    if progress is not None:
        progress.finish()
    return rivers_zero, valid_mask


def write_distance_raster(
    src: rasterio.io.DatasetReader,
    distance_mm: np.memmap,
    out_path: Path,
    progress: ProgressPrinter | None = None,
) -> None:
    if out_path.exists():
        out_path.unlink()
    profile = src.profile
    profile.update(
        dtype="float32",
        count=1,
        nodata=np.nan,
        compress="deflate",
        predictor=3,
        tiled=False,
    )
    profile.pop("blockxsize", None)
    profile.pop("blockysize", None)
    profile["crs"] = src.crs

    with rasterio.open(out_path, "w", **profile) as dst:
        for _, window in src.block_windows(1):
            row_slice, col_slice = window_slices(window)
            block = np.asarray(distance_mm[row_slice, col_slice], dtype=np.float32)
            dst.write(block, 1, window=window)
            if progress is not None:
                progress.increment()

    if progress is not None:
        progress.finish()


def iter_tile_windows(height: int, width: int, tile_size: int) -> Iterator[Window]:
    for row_off in range(0, height, tile_size):
        for col_off in range(0, width, tile_size):
            yield Window(
                col_off=col_off,
                row_off=row_off,
                width=min(tile_size, width - col_off),
                height=min(tile_size, height - row_off),
            )


def pad_window(window: Window, pad_rows: int, pad_cols: int, height: int, width: int) -> Window:
    col_off = max(window.col_off - pad_cols, 0)
    row_off = max(window.row_off - pad_rows, 0)
    col_end = min(window.col_off + window.width + pad_cols, width)
    row_end = min(window.row_off + window.height + pad_rows, height)
    return Window(
        col_off=col_off,
        row_off=row_off,
        width=col_end - col_off,
        height=row_end - row_off,
    )


def process_tiles(
    src: rasterio.io.DatasetReader,
    out_path: Path,
    tile_size: int,
    tile_padding: int,
    px: float,
    py: float,
) -> None:
    profile = src.profile
    profile.update(
        dtype="float32",
        count=1,
        nodata=np.nan,
        compress="deflate",
        predictor=3,
        tiled=False,
    )
    profile.pop("blockxsize", None)
    profile.pop("blockysize", None)
    profile["crs"] = src.crs

    if out_path.exists():
        out_path.unlink()

    total_rows = math.ceil(src.height / tile_size)
    total_cols = math.ceil(src.width / tile_size)
    total_tiles = max(total_rows * total_cols, 1)
    progress = ProgressPrinter("Processando tiles", total_tiles, mode="count")
    nodata = src.nodata

    with rasterio.open(out_path, "w", **profile) as dst:
        for window in iter_tile_windows(src.height, src.width, tile_size):
            padded = pad_window(window, tile_padding, tile_padding, src.height, src.width)
            block = src.read(1, window=padded, masked=False)

            if nodata is None or nodata in (0, 1):
                mask = np.ones(block.shape, dtype=bool)
            else:
                mask = block != nodata

            binary = np.where((block == 1) & mask, 0, 1).astype(np.uint8, copy=False)
            distance = distance_transform_edt(
                binary,
                sampling=(py, px),
                return_indices=False,
            ).astype(np.float32, copy=False)
            distance[~mask] = np.nan

            row_start = window.row_off - padded.row_off
            col_start = window.col_off - padded.col_off
            row_slice = slice(row_start, row_start + window.height)
            col_slice = slice(col_start, col_start + window.width)

            dst.write(distance[row_slice, col_slice], 1, window=window)
            progress.increment()

    progress.finish()


def process_full_raster(
    src: rasterio.io.DatasetReader,
    out_path: Path,
    tmp_path: Path,
    px: float,
    py: float,
) -> None:
    total_blocks = estimate_total_blocks(src)
    rivers_zero, valid_mask = build_binary_arrays(
        src, tmp_path, ProgressPrinter("Preparando raster binário", total_blocks)
    )

    distance_mm = allocate_memmap(tmp_path, "distance.float64", np.float64, (src.height, src.width))
    print("Calculando distância (transformada EDT)...")
    distance_transform_edt(
        rivers_zero,
        sampling=(py, px),
        return_distances=True,
        return_indices=False,
        distances=distance_mm,
    )
    print("Transformada EDT concluída.")

    distance_mm[~valid_mask] = np.nan
    distance_mm.flush()

    write_distance_raster(src, distance_mm, out_path, ProgressPrinter("Gravando GeoTIFF", total_blocks))


def main(
    in_tif: str,
    out_tif: str,
    tile_size: int,
    tile_padding: int,
) -> None:
    with rasterio.open(in_tif) as src, tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        transform: Affine = src.transform
        crs = src.crs

        print(f"CRS de entrada: {format_crs(crs)}")
        if crs is None or not crs.is_projected:
            print(
                "ATENÇÃO: CRS não projetado. As distâncias sairão nas unidades originais."
                " Idealmente reprojete para um CRS métrico."
            )

        px = abs(transform.a)
        py = abs(transform.e)

        if tile_size > 0:
            print(
                f"Processando em tiles de {tile_size}px com borda extra de {tile_padding}px."
                " Certifique-se de usar padding >= distância máxima que precisa preservar."
            )
            process_tiles(src, Path(out_tif), tile_size, tile_padding, px, py)
        else:
            process_full_raster(src, Path(out_tif), tmp_path, px, py)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mapa de distâncias até os pixels com valor 1 (rios).")
    parser.add_argument("--in", dest="in_tif", required=True, help="TIFF binário (1=rio, 0=terra).")
    parser.add_argument("--out", dest="out_tif", required=True, help="TIFF de saída com distâncias em metros.")
    parser.add_argument(
        "--tile-size",
        dest="tile_size",
        type=int,
        default=0,
        help="Opcional: processa o raster em tiles quadrados (pixels) para economizar RAM.",
    )
    parser.add_argument(
        "--tile-padding",
        dest="tile_padding",
        type=int,
        default=512,
        help="Borda extra por tile (pixels). Deve ser >= à distância máxima que precisa ser considerada.",
    )
    args = parser.parse_args()
    main(args.in_tif, args.out_tif, max(0, args.tile_size), max(0, args.tile_padding))
