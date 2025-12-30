# Repository Guidelines

## Project Approach
- Mantenha o repositório simples: apenas os scripts essenciais (`dist_map.py`, `plot_tiff.py`, `clip_bbox.py`) e dados de exemplo mínimos.
- Sem suíte de testes ou automações pesadas por enquanto; priorize iteração rápida e arquivos pequenos.
- Documente diretamente nos scripts as suposições importantes (por exemplo, necessidade de CRS projetado).

## Plotagens e BBox
- Sempre visualize e depure usando recortes menores para não estourar a RAM.
- Use `plot_tiff.py --bbox MIN_LON MIN_LAT MAX_LON MAX_LAT ...` para gerar PNGs apenas da área de interesse.
- Caso precise de um arquivo físico menor, recorte antes com `clip_bbox.py` reutilizando o mesmo bbox.

## Execução Básica
- Ambiente sugerido: `python3 -m venv .venv && source .venv/bin/activate`.
- Dependências mínimas: `pip install numpy rasterio scipy matplotlib`.
- Scripts principais:
  - `python prep_binary_inputs.py --source-dir 00_inputs_tiffs --dest-dir 00_inputs_binary_ready`
  - `python dist_map.py --in rios.tif --out dist_m.tif`
  - `bash run_clip_masks.sh` + `bash run_regrid_1km.sh` após gerar os `*_dist.tif`
  - `bash run_mosaics.sh` para juntar os três estados (sem depender do regrid)
  - `bash run_mosaics_1km.sh` caso o regrid de 1 km seja executado
  - `python plot_tiff.py --file dist_m.tif --bbox ...`
  - `python clip_bbox.py --file rios.tif --min_lon ... --min_lat ... --max_lon ... --max_lat ...`

## Estilo e Organização
- Python 3.10+, PEP 8, snake_case, type hints nas funções expostas em CLI.
- Se precisar de helpers, use módulos planos como `utils_*.py`; evite criar estruturas sofisticadas enquanto não forem necessárias.
- Prefira CLIs curtos com poucas flags, seguindo o padrão já existente (`--in`, `--out`, `--bbox`).

## Segurança & Dados
- Trabalhe com CRS projetados quando a métrica importam (distâncias em metros).
- Não suba arquivos grandes ou sensíveis; os TIFFs no repositório devem ser recortes pequenos.
- Normalize sempre os rasters binários para 1/0 sem NoData antes de qualquer distância para evitar distorções nas máscaras.
- Limite o cache do GDAL (`--config GDAL_CACHEMAX 1024 -wm 1024`) ao recortar/reamostrar para não estourar a RAM das máquinas mais simples.
