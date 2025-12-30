# proj-dist-tif

Pipeline minimalista para transformar rasters binários (estradas/rios) em mapas de distância por estado do Sul do Brasil, recortar por máscara, opcionalmente reamostrar e mosaicar tudo em um único GeoTIFF com CRS métrico consistente (EPSG:31997).

## Requisitos

- Python 3.10+ com virtualenv
- GDAL/OGR CLI (`gdalwarp`, `gdalbuildvrt`, `ogr2ogr`)
- Bibliotecas Python listadas em `requirements.txt` (principalmente `numpy`, `rasterio`, `scipy`, `matplotlib`)

## Estrutura de diretórios

Os diretórios numerados representam cada etapa do fluxo:

| Diretório | Conteúdo |
| --- | --- |
| `00_inputs_tiffs/` | TIFFs brutos fornecidos (1 = feição, demais NoData). |
| `00_inputs_binary_ready/` | TIFFs limpos (1/0) gerados por `prep_binary_inputs.py`. |
| `01_shapefiles_orig/` | Shapefiles originais das UFs (CRS geográfico). |
| `02_shapefiles_epsg31997/` | Shapefiles reprojetados para EPSG:31997. |
| `03_dist_map_tiles/` | Saídas diretas do `dist_map.py`. |
| `04_dist_map_masked/` | Rasters de distância recortados por UF (`gdalwarp`). |
| `05_dist_map_masked_regridded_1km/` | (Opcional) Versões reamostradas para pixels de 1 km. |
| `06_dist_map_mosaics/` | Mosaicos finais estradas/rios (`*_dist_regiao_sul.tif`) + variantes `_1km`. |
| `07_qgis_projects/` | Projetos do QGIS usados apenas para visualização manual. |

Scripts auxiliares vivem na raiz (`prep_binary_inputs.py`, `dist_map.py`, `run_*.sh`, `show_crs.py`, etc.).

## Fluxo rápido

```bash
# 1) Ambiente
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2) Normalizar rasters (NoData -> 0)
python prep_binary_inputs.py --source-dir 00_inputs_tiffs --dest-dir 00_inputs_binary_ready

# 3) Mapas de distância em tiles
bash run_dist_maps.sh

# 4) Recorte por UF (usa shapefiles reprojetados)
bash run_clip_masks.sh

# 5) (Opcional) Regrid 1 km
bash run_regrid_1km.sh

# 6) Mosaicos finais (sem regrid)
bash run_mosaics.sh

# 7) (Opcional) Mosaicos já reamostrados
bash run_mosaics_1km.sh
```

Ferramentas úteis:

- `python show_crs.py --file <.tif/.shp>` para auditar rapidamente o CRS.
- `plot_tiff.py` e `clip_bbox.py` para depuração/preview em recortes menores.
- Scripts `run_*` usam GDAL com `--config GDAL_CACHEMAX 1024 -wm 1024` para evitar picos de RAM.

## Documentação

- **Fluxo detalhado:** `fluxo_dist_map.md` (explica cada etapa, exemplos de CLI, diagnóstico dos rasters, instruções de QGIS e TODO expandido).
- **Passo a passo resumido:** `passo_a_passo_resumido.md` (checklist rápido com comandos).
- **Guidelines gerais:** `AGENTS.md` (estilo de código, dependências mínimas, boas práticas de CRS e uso de memória).

## TODO resumido

- Criar um `clip_with_mask.py` simples em Python para ambientes sem GDAL.
- Automatizar verificações pós-processamento (CRS, NoData, estatísticas) antes de liberar os rasters finais.
- Investigar mosaicos combinando estradas + rios e garantir variantes compatíveis com o regrid de 1 km quando a etapa voltar a ser usada.

Consulte `fluxo_dist_map.md` para o histórico completo, exemplos de comandos avançados (incluindo QGIS) e as próximas evoluções planejadas.
