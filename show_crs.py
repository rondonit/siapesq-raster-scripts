#!/usr/bin/env python3
"""Exibe o CRS de um GeoTIFF ou shapefile informado via --file."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import rasterio
from rasterio.crs import CRS


def format_crs(crs: Optional[CRS]) -> str:
    if crs is None or not crs:
        return "CRS não definido"
    epsg = crs.to_epsg()
    if epsg:
        return f"EPSG:{epsg}"
    return crs.to_string() or crs.to_wkt()


def read_raster_crs(path: Path) -> Optional[CRS]:
    with rasterio.open(path) as src:
        return src.crs


def read_shapefile_crs(path: Path) -> Optional[CRS]:
    prj_path = path.with_suffix(".prj")
    if not prj_path.exists():
        raise FileNotFoundError(f"Arquivo .prj não encontrado para {path}")
    wkt = prj_path.read_text().strip()
    if not wkt:
        return None
    try:
        return CRS.from_wkt(wkt)
    except Exception:
        print("Aviso: CRS não pôde ser interpretado, exibindo WKT cru abaixo:")
        print(wkt)
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Mostra o CRS de um arquivo raster (.tif) ou shapefile (.shp).")
    parser.add_argument("--file", required=True, help="Caminho do arquivo a ser inspecionado.")
    args = parser.parse_args()
    path = Path(args.file)
    if not path.exists():
        raise SystemExit(f"Arquivo não encontrado: {path}")

    suffix = path.suffix.lower()
    if suffix in (".tif", ".tiff"):
        crs = read_raster_crs(path)
        print(f"{path}: {format_crs(crs)}")
    elif suffix == ".shp":
        try:
            crs = read_shapefile_crs(path)
        except FileNotFoundError as exc:
            raise SystemExit(str(exc))
        print(f"{path}: {format_crs(crs)}")
    else:
        raise SystemExit("Tipo de arquivo não suportado. Use shapefiles (.shp) ou GeoTIFFs (.tif).")


if __name__ == "__main__":
    main()
