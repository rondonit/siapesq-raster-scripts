# Fluxo para gerar rasters de distância (estradas e rios)

Objetivo: transformar os TIFFs binários fornecidos (estradas_* e rios_*) em mapas de distância (metros até o pixel “1” mais próximo), recortá-los pelas UFs correspondentes e alinhar os resultados finais em uma grade de 1 km × 1 km, mantendo todo o histórico organizado e com CRS consistente (EPSG:31997).

## Estrutura atual do repositório

A própria raiz do projeto funciona como checklist do fluxo. A saída real do `tree -L 2` está abaixo:

```bash
.
├── 00_inputs_binary_ready
│   ├── estradas_parana_final.tif
│   ├── estradas_rs_final.tif
│   ├── estradas_sc_final.tif
│   ├── rios_parana_final.tif
│   ├── rios_rs_final.tif
│   ├── rios_rs_final.tif.aux.xml
│   └── rios_sc_final.tif
├── 00_inputs_tiffs
│   ├── estradas_parana_final.tif
│   ├── estradas_rs_final.tif
│   ├── estradas_sc_final.tif
│   ├── rios_parana_final.tif
│   ├── rios_rs_final.tif
│   └── rios_sc_final.tif
├── 01_shapefiles_orig
│   ├── PR_UF_2024
│   ├── RS_UF_2024
│   └── SC_UF_2024
├── 02_shapefiles_epsg31997
│   ├── PR_UF_2024_epsg31997.dbf
│   ├── PR_UF_2024_epsg31997.prj
│   ├── PR_UF_2024_epsg31997.shp
│   ├── PR_UF_2024_epsg31997.shx
│   ├── RS_UF_2024_epsg31997.dbf
│   ├── RS_UF_2024_epsg31997.prj
│   ├── RS_UF_2024_epsg31997.shp
│   ├── RS_UF_2024_epsg31997.shx
│   ├── SC_UF_2024_epsg31997.dbf
│   ├── SC_UF_2024_epsg31997.prj
│   ├── SC_UF_2024_epsg31997.shp
│   └── SC_UF_2024_epsg31997.shx
├── 03_dist_map_tiles
│   ├── estradas_parana_final_dist.tif
│   ├── estradas_rs_final_dist.tif
│   ├── estradas_sc_final_dist.tif
│   ├── rios_parana_final_dist.tif
│   ├── rios_rs_final_dist.tif
│   └── rios_sc_final_dist.tif
├── 04_dist_map_masked
│   ├── estradas_parana_final_dist_masked.tif
│   ├── estradas_rs_final_dist_masked.tif
│   ├── estradas_sc_final_dist_masked.tif
│   ├── rios_parana_final_dist_masked.tif
│   ├── rios_rs_final_dist_masked.tif
│   └── rios_sc_final_dist_masked.tif
├── 05_dist_map_masked_regridded_1km
│   ├── estradas_parana_final_dist_masked_1km.tif
│   ├── estradas_rs_final_dist_masked_1km.tif
│   ├── estradas_sc_final_dist_masked_1km.tif
│   ├── rios_parana_final_dist_masked_1km.tif
│   ├── rios_rs_final_dist_masked_1km.tif
│   ├── rios_rs_final_dist_masked_1km.tif.aux.xml
│   └── rios_sc_final_dist_masked_1km.tif
├── 06_dist_map_mosaics
│   ├── estradas_dist_regiao_sul.tif
│   ├── estradas_dist_regiao_sul.tif.aux.xml
│   ├── estradas_dist_regiao_sul.vrt
│   ├── estradas_dist_regiao_sul_1km.tif
│   ├── estradas_dist_regiao_sul_1km.vrt
│   ├── rios_dist_regiao_sul.tif
│   ├── rios_dist_regiao_sul.tif.aux.xml
│   ├── rios_dist_regiao_sul.vrt
│   ├── rios_dist_regiao_sul_1km.tif
│   └── rios_dist_regiao_sul_1km.vrt
├── 07_qgis_projects
│   └── rios_estradas_dist_sul_qgis.qgz
├── prep_binary_inputs.py
├── run_dist_maps.sh
├── run_clip_masks.sh
├── run_regrid_1km.sh
├── run_mosaics.sh
├── run_mosaics_1km.sh
└── show_crs.py
```

Tabela rápida dos diretórios numerados:

| Diretório | Papel |
| --- | --- |
| `00_inputs_tiffs/` | GeoTIFFs brutos recebidos do colega (1 = feição, restante armazenado como NoData). |
| `00_inputs_binary_ready/` | GeoTIFFs binários limpos, 1/0 sem NoData, prontos para o `dist_map.py`. |
| `01_shapefiles_orig/` | Shapefiles originais das UFs (CRS geográfico `EPSG:4674`). |
| `02_shapefiles_epsg31997/` | Shapefiles reprojetados para `EPSG:31997`, um arquivo por UF. |
| `03_dist_map_tiles/` | Saídas diretas do `dist_map.py` (antes do recorte). |
| `04_dist_map_masked/` | Rasters de distância recortados por UF (`gdalwarp -cutline`). |
| `05_dist_map_masked_regridded_1km/` | (Opcional) Versões reamostradas para pixels de 1 km para análises que exijam essa grade. |
| `06_dist_map_mosaics/` | Mosaicos finais estradas/rios cobrindo os três estados (`*_dist_regiao_sul.tif`) e variantes `_1km` caso o regrid tenha sido executado. |
| `07_qgis_projects/` | Espaço reservado para projetos do QGIS usados apenas para visualização manual. |

## Diagnóstico dos TIFFs brutos

Os arquivos em `00_inputs_tiffs/` têm apenas duas “classes”: `1` para estrada/rio e NoData = `0`. Isso significa que:

- Visualizar direto no QGIS mostra apenas o traçado porque o resto é transparente (NoData).
- Operações de distância/máscara que dependem do valor `0` não funcionam corretamente sem limpar o NoData.

Snip de validação usado (rodado dentro do repo):

```bash
python3 - <<'PY'
import rasterio
from pathlib import Path
root = Path("00_inputs_tiffs")
for tif in sorted(root.glob("*.tif")):
    with rasterio.open(tif) as src:
        nodata = src.nodata
        arr = src.read(1, window=((0, min(512, src.height)), (0, min(512, src.width))), masked=True)
        vals = sorted(set(arr.compressed().tolist()))
        print(f"{tif.name}: crs={src.crs}, nodata={nodata}, valores_amostrados={vals[:5]}")
PY
```

Saída observada (resumida): todos os rasters possuem CRS `EPSG:31997`, `nodata=0.0` e valores apenas `[1]` na área com feições – não há “0 válido”. Com isso justificamos a etapa adicional de normalização.

## Estágios detalhados

### 0. Ambiente Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 1. Normalizar os GeoTIFFs (NoData → 0 real)

Script: `prep_binary_inputs.py`.

```bash
source .venv/bin/activate
python prep_binary_inputs.py --source-dir 00_inputs_tiffs --dest-dir 00_inputs_binary_ready
```

O script percorre cada arquivo, substitui NoData por 0, garante dtype `uint8`, remove o flag `nodata` e mantém o CRS original. O resultado tem exatamente dois valores:

| Valor | Significado |
| --- | --- |
| `1` | Há estrada/rio naquele pixel. |
| `0` | Não há estrada/rio (pixel válido). |

Esses arquivos são os únicos aceitos pelo `run_dist_maps.sh`.

### 2. Shapefiles originais × reprojetados

- Os subdiretórios dentro de `01_shapefiles_orig/` guardam o pacote completo entregue (com `.shp/.prj/.dbf` etc).
- Use `ogr2ogr` para reprojetar para `EPSG:31997` (o padrão métrico adotado no Sul do Brasil quando precisamos de distâncias em metros). Exemplo para o RS:

  ```bash
  ogr2ogr -t_srs EPSG:31997 \
    02_shapefiles_epsg31997/RS_UF_2024_epsg31997.shp \
    01_shapefiles_orig/RS_UF_2024/RS_UF_2024.shp
  ```

- Repita para PR e SC. Esse comando lê direto o `.prj` original, cria um novo shapefile já em metros e mantém o atributo UF. Como estamos usando SIRGAS/UTM, o CRS fica coerente com os rasters.

### 3. Como garantir que o CRS está correto?

Ferramentas:

- `python show_crs.py --file <caminho>` → imprime o EPSG ou WKT de TIFFs e shapefiles.
- `gdalinfo arquivo.tif | grep -E 'Coordinate System|Pixel Size'` → confirma o CRS e a resolução.
- Dentro do QGIS, abra `Layer Properties → Information` para ver o EPSG.

Checklist rápido antes de avançar:

1. `python show_crs.py --file 00_inputs_binary_ready/estradas_rs_final.tif` → deve retornar `EPSG:31997`.
2. `python show_crs.py --file 02_shapefiles_epsg31997/RS_UF_2024_epsg31997.shp` → idem.
3. Se algum arquivo vier em outro CRS, reprojete antes de gerar as distâncias para evitar distorção.

### 4. Gerar mapas de distância em tiles

Script: `run_dist_maps.sh`.

```
source .venv/bin/activate
bash run_dist_maps.sh
```

O script percorre automaticamente todos os rasters binários de `00_inputs_binary_ready/` e grava os `_dist.tif` dentro de `03_dist_map_tiles/`, sempre com `--tile-size 4096 --tile-padding 1024`. `dist_map.py` imprime o CRS lido e garante que o CRS/perfil seja copiado para a saída.

Se precisar rodar manualmente:

```bash
python dist_map.py --in 00_inputs_binary_ready/estradas_rs_final.tif \
    --out 03_dist_map_tiles/estradas_rs_final_dist.tif \
    --tile-size 4096 --tile-padding 1024
```

### 5. Recortar usando os shapefiles reprojetados

Script: `run_clip_masks.sh` (usa `gdalwarp` com limites de cache para não estourar memória).

```bash
bash run_clip_masks.sh
```

Detalhes:

- `INPUT_DIR=03_dist_map_tiles`
- `MASK_DIR=02_shapefiles_epsg31997`
- `OUTPUT_DIR=04_dist_map_masked`
- `gdalwarp` roda com `--config GDAL_CACHEMAX 1024 -wm 1024 -multi`, corta usando `-cutline ... -crop_to_cutline` e define `-dstnodata -9999`.

Se preferir CLI direta, adapte:

```bash
gdalwarp -overwrite -of GTiff \
  --config GDAL_CACHEMAX 1024 -wm 1024 -multi \
  -cutline 02_shapefiles_epsg31997/RS_UF_2024_epsg31997.shp -cl RS_UF_2024_epsg31997 \
  -crop_to_cutline -dstnodata -9999 \
  03_dist_map_tiles/estradas_rs_final_dist.tif \
  04_dist_map_masked/estradas_rs_final_dist_masked.tif
```

### 6. (Opcional) Reamostrar para grade de 1 km

NOVA etapa `05_dist_map_masked_regridded_1km/` — mantenha o script disponível, mas só rode quando realmente precisar alinhar com uma grade de 1 km. Para rodar:

```bash
bash run_regrid_1km.sh
```

Internamente, `gdalwarp` roda com `-tr 1000 1000` e `-r near`, preservando valores de distância sem interpolação pesada. Se a perda de precisão for indesejada, pule essa etapa (como estamos fazendo agora) e siga diretamente para o mosaico.

### 7. Mosaicar os três estados (sem regrid)

Script: `run_mosaics.sh`.

```bash
bash run_mosaics.sh
```

O script gera dois arquivos em `06_dist_map_mosaics/`:

- `estradas_dist_regiao_sul.tif`
- `rios_dist_regiao_sul.tif`

Ele usa `gdalbuildvrt` + `gdal_translate` com `-srcnodata/-vrtnodata/-a_nodata -9999` para garantir que as bordas irregulares das UFs se encaixem corretamente, sempre a partir dos rasters já recortados (`04_dist_map_masked`). O VRT intermediário fica no mesmo diretório.

Se quiser rodar manualmente:

```bash
gdalbuildvrt \
  06_dist_map_mosaics/estradas_dist_regiao_sul.vrt \
  04_dist_map_masked/estradas_rs_final_dist_masked.tif \
  04_dist_map_masked/estradas_sc_final_dist_masked.tif \
  04_dist_map_masked/estradas_parana_final_dist_masked.tif

gdal_translate \
  -of GTiff -co COMPRESS=LZW -a_nodata -9999 \
  06_dist_map_mosaics/estradas_dist_regiao_sul.vrt \
  06_dist_map_mosaics/estradas_dist_regiao_sul.tif
```

Repita trocando os arquivos para os rasters de rios.

### 8. (Opcional) Mosaico na grade de 1 km

Caso a etapa de regrid tenha sido executada, gere o mosaico correspondente para manter a mesma resolução. Script: `run_mosaics_1km.sh`.

```bash
bash run_mosaics_1km.sh
```

Ele replica o fluxo `gdalbuildvrt + gdal_translate`, porém lendo de `05_dist_map_masked_regridded_1km/` e escrevendo `*_dist_regiao_sul_1km.(vrt|tif)` em `06_dist_map_mosaics/`. Útil para análises que esperam rasters já na malha de 1 km.

## Pipeline completo (bash)

1. Preparar ambiente (uma vez):
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Normalizar os inputs:
   ```bash
   python prep_binary_inputs.py --source-dir 00_inputs_tiffs --dest-dir 00_inputs_binary_ready
   ```
3. Confirmar CRS quando necessário:
   ```bash
   python show_crs.py --file 00_inputs_binary_ready/estradas_rs_final.tif
   python show_crs.py --file 02_shapefiles_epsg31997/RS_UF_2024_epsg31997.shp
   ```
4. Gerar mapas de distância:
   ```bash
   bash run_dist_maps.sh
   ```
5. Recortar por UF:
   ```bash
   bash run_clip_masks.sh
   ```
6. (Opcional) Reamostrar para 1 km:
   ```bash
   bash run_regrid_1km.sh
   ```
7. Mosaicar Sul (sem regrid):
   ```bash
   bash run_mosaics.sh
   ```
8. (Opcional) Mosaico na grade de 1 km:
   ```bash
   bash run_mosaics_1km.sh
   ```

Durante qualquer etapa, monitore o CRS com `show_crs.py` e abra amostras no QGIS para validar visualmente.

## Observações

- `EPSG:31997 (SIRGAS 2000 / UTM zone 21S)` foi adotado como padrão métrico. Permaneça nele salvo instrução expressa em contrário.
- `prep_binary_inputs.py` documenta a suposição “1 = feição” diretamente no código, conforme diretriz do `AGENTS.md`.
- `run_clip_masks.sh` e `run_regrid_1km.sh` já controlam o uso de RAM limitando o cache e usando `-multi`. Caso ainda fique pesado, reduza `GDAL_CACHEMAX` ou rode UF por UF.
- Futuro `clip_with_mask.py`: se criarmos a versão Python do recorte, basta encapsular o `rasterio.mask.mask` seguindo as mesmas máscaras do diretório `02_shapefiles_epsg31997`. Por enquanto, a automação via `gdalwarp` cobre a necessidade.

## TODO

1. **Automatizar recorte em Python:** implementar um `clip_with_mask.py` que leia diretamente os shapefiles da etapa 02 para evitar depender do `gdalwarp` externo (útil para ambientes sem GDAL).
2. **Validação pós-processamento:** criar um checklist/CLI simples que inspecione cada arquivo em `05_dist_map_masked_regridded_1km` e confirme CRS, NoData e estatísticas antes de seguir para análises.
3. **Estender mosaicos:** adicionar variantes que combinem estradas+rios em um único arquivo (com regras claras de prioridade) e versões compatíveis com o regrid de 1 km quando ele voltar a ser necessário.

## Recorte por máscara no QGIS

- Abra o QGIS Firenze.
- Vá ao menu `Settings → Options… → CRS` e marque `Enable on-the-fly CRS transformation`. Clique em `OK`.
- No canto inferior direito da janela principal, clique no indicador de CRS do projeto, abra `Project Properties → CRS`, filtre por `31997`, selecione `SIRGAS 2000 / UTM zone 21S (EPSG:31997)` e confirme em `OK`.
- Menu `Layer → Add Layer → Add Raster Layer…`, carregando `03_dist_map_tiles/…_dist.tif`.
- Menu `Layer → Add Layer → Add Vector Layer…`, carregando `02_shapefiles_epsg31997/…_epsg31997.shp`.
- Menu `Raster → Extraction → Clip Raster by Mask Layer`:
  - `Input layer`: raster de distâncias.
  - `Mask layer`: shapefile da UF.
  - Marque `Match the extent of the mask layer (clipping)` e `Keep resolution of input raster`.
  - `Assign a specified nodata value to output bands`: use `-9999` (ou deixe em branco).
  - `Clipped (mask)`: salve em `04_dist_map_masked/<nome>_dist_masked.tif`.
  - Clique em `Run` e depois `Close`.
- Verifique o resultado no painel “Layers”: desligue o raster de entrada, abra `Properties → Information` do novo raster para conferir CRS, extent e estatísticas.
- Repita para cada UF/raster trocando o layer de entrada, máscara e arquivo de saída conforme necessário.
