# Passo a passo resumido

1. **Ativar ambiente** – cria/ativa o virtualenv e instala dependências mínimas:
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Normalizar os TIFFs** – converte os rasters brutos (1/NoData) em binário puro 1/0:
   ```bash
   python prep_binary_inputs.py --source-dir 00_inputs_tiffs --dest-dir 00_inputs_binary_ready
   ```
3. **Gerar mapas de distância** – processa todos os TIFFs limpos em tiles 4096/1024:
   ```bash
   bash run_dist_maps.sh
   ```
4. **Recortar por UF** – aplica as máscaras reprojetadas em EPSG:31997 com limite de RAM:
   ```bash
   bash run_clip_masks.sh
   ```
5. **(Opcional) Reamostrar para 1 km** – apenas se precisar alinhar com uma grade fixa:
   ```bash
   bash run_regrid_1km.sh
   ```
6. **Mosaico Sul (sem regrid)** – usa diretamente os rasters de `04_dist_map_masked`:
   ```bash
   bash run_mosaics.sh
   ```

7. **(Opcional extra)** – mantém um mosaico sincronizado com a grade de 1 km:
   ```bash
   bash run_mosaics_1km.sh
   ```

## TODO (resumo)

- Criar um `clip_with_mask.py` leve para quando o GDAL não estiver disponível.
- Adicionar uma checagem rápida dos rasters finais (CRS, NoData, estatísticas) antes de liberar para análise.
- Explorar mosaicos combinados (estradas + rios) e variantes alinhadas ao regrid, caso a etapa de 1 km volte a ser usada.
