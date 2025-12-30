"""Recorta um GeoTIFF em um bounding box especificado."""

from pathlib import Path

import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds


def build_output_path(input_path: Path, min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> Path:
    base = input_path.stem
    suffix = f"bbox_{min_lon:.4f}_{min_lat:.4f}_{max_lon:.4f}_{max_lat:.4f}"
    return input_path.with_name(f"{base}_{suffix}.tif")


def main(file: Path, min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> None:
    with rasterio.open(file) as src:
        if src.crs is None:
            raise rasterio.errors.CRSError("Fonte sem CRS definido.")

        target_bounds = transform_bounds(
            "EPSG:4326",
            src.crs,
            min_lon,
            min_lat,
            max_lon,
            max_lat,
            densify_pts=21,
        )

        window = from_bounds(*target_bounds, src.transform)
        window = window.round_offsets().round_lengths()
        profile = src.profile
        profile.update(
            width=window.width,
            height=window.height,
            transform=rasterio.windows.transform(window, src.transform),
        )

        output_path = build_output_path(file, min_lon, min_lat, max_lon, max_lat)
        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(src.read(window=window))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Recorta um TIFF em um bbox dados.")
    parser.add_argument("--file", type=Path, required=True, help="Caminho do TIFF de entrada.")
    parser.add_argument("--min_lon", type=float, required=True, help="Longitude mínima do bbox.")
    parser.add_argument("--min_lat", type=float, required=True, help="Latitude mínima do bbox.")
    parser.add_argument("--max_lon", type=float, required=True, help="Longitude máxima do bbox.")
    parser.add_argument("--max_lat", type=float, required=True, help="Latitude máxima do bbox.")
    args = parser.parse_args()

    main(args.file, args.min_lon, args.min_lat, args.max_lon, args.max_lat)
