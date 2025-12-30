"""Visualiza rapidamente um TIFF (inteiro ou recortado) sem estourar a RAM."""

from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.errors import CRSError
from rasterio.windows import Window, bounds as window_bounds, from_bounds
from rasterio.warp import transform_bounds


def build_output_path(raster_path: Path, suffix: str) -> Path:
    return raster_path.with_name(f"{raster_path.stem}_{suffix}.png")


def compute_limits(img: np.ndarray, vmin: float | None, vmax: float | None) -> tuple[float, float]:
    valid = np.isfinite(img)
    if not np.any(valid):
        return 0.0, 1.0
    low = float(np.nanmin(img[valid])) if vmin is None else vmin
    high = float(np.nanmax(img[valid])) if vmax is None else vmax
    if low == high:
        high = low + 1.0
    return low, high


def compute_window(src: rasterio.io.DatasetReader, bbox_wgs84: Iterable[float] | None) -> tuple[Window | None, tuple[float, float, float, float]]:
    if bbox_wgs84 is None:
        bounds = src.bounds
        return None, (bounds.left, bounds.right, bounds.bottom, bounds.top)

    if src.crs is None:
        raise CRSError("O raster precisa ter CRS para aplicar um bbox.")

    min_lon, min_lat, max_lon, max_lat = bbox_wgs84
    transformed = transform_bounds("EPSG:4326", src.crs, min_lon, min_lat, max_lon, max_lat, densify_pts=21)
    window = from_bounds(*transformed, src.transform)
    window = window.round_offsets().round_lengths()
    window = window.intersection(Window(0, 0, src.width, src.height))
    if window.width <= 0 or window.height <= 0:
        raise ValueError("BBox não intersecta o raster.")

    extent = window_bounds(window, src.transform)
    left, right, bottom, top = extent
    return window, (left, right, bottom, top)


def plot_preview(
    file: Path,
    band: int,
    cmap: str,
    vmin: float | None,
    vmax: float | None,
    out: Path | None,
    bbox: Iterable[float] | None,
    colorbar_label: str,
) -> None:
    with rasterio.open(file) as src:
        window, extent = compute_window(src, bbox)
        arr = src.read(band, window=window, masked=True).astype("float32")
        filled = arr.filled(np.nan)
        auto_vmin, auto_vmax = compute_limits(filled, vmin, vmax)
        data = np.ma.masked_invalid(filled)

        fig, ax = plt.subplots(figsize=(7, 5))
        im = ax.imshow(
            data,
            cmap=cmap,
            extent=extent,
            origin="upper",
            vmin=auto_vmin,
            vmax=auto_vmax,
        )
        ax.set_title(f"{file.name} (band {band})")
        ax.set_xlabel("Easting")
        ax.set_ylabel("Northing")
        fig.colorbar(im, ax=ax, label=colorbar_label)

        output_path = out or build_output_path(file, "preview")
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Salva uma visualização rápida de um TIFF.")
    parser.add_argument("--file", type=Path, required=True, help="Caminho do TIFF.")
    parser.add_argument("--band", type=int, default=1, help="Banda única para plotar.")
    parser.add_argument("--cmap", default="viridis", help="Colormap do matplotlib.")
    parser.add_argument("--vmin", type=float, help="Valor mínimo do stretch.")
    parser.add_argument("--vmax", type=float, help="Valor máximo do stretch.")
    parser.add_argument(
        "--bbox",
        type=float,
        nargs=4,
        metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"),
        help="Recorta usando EPSG:4326 para não carregar o raster inteiro.",
    )
    parser.add_argument("--out", type=Path, help="Caminho de saída da imagem PNG.")
    parser.add_argument(
        "--cbar-label",
        default="Pixel value",
        help="Texto do rótulo da barra de cores (ex.: 'Distance (m)').",
    )
    args = parser.parse_args()

    plot_preview(
        args.file,
        args.band,
        args.cmap,
        args.vmin,
        args.vmax,
        args.out,
        args.bbox,
        args.cbar_label,
    )
