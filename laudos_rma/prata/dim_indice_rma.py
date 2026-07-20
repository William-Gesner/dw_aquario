"""
Carga da dimensão de hierarquia do Índice RMA do BI Laudos RMA -- camada Prata.

Origem  : Excel manual -- IndiceRMA.xlsx, aba 'Planilha1'
          (Z:\\Dados\\ -- NÃO passa pela Bronze, lida direto do Excel,
          igual o legado sempre fez)
Destino : DW_PRATA.DIM_INDICE_RMA
          (era BIAQUARIO.USU_VBIARMA_INDICE_RMA no legado)
Carga   : full_reload (DROP + recarga completa) -- mesma estratégia do
          legado (aquario/laudos_rma/extract/vbiindice_rma.py).

Lógica de negócio idêntica ao legado -- nenhuma coluna, filtro ou
transformação foi alterada. Classificação: DIMENSÃO -- sem corte de data
(hierarquia completa e atual do índice).
"""

# ----- IMPORTS -----

from time import perf_counter

import pandas as pd

from core.db import get_engine_prata
from core.dtype_map import build_dtype_map
from core.loader import full_reload
from laudos_rma.config.settings import EXCEL_INDICE_RMA, schema_prata

# ----- CONFIGURAÇÃO DA TABELA DESTINO -----

tabela_destino = "DIM_INDICE_RMA"

# ----- EXTRAÇÃO DO EXCEL -----

inicio_total = perf_counter()

if not EXCEL_INDICE_RMA.exists():
    raise FileNotFoundError(
        f"Arquivo não encontrado: {EXCEL_INDICE_RMA}\n"
        f"Verifique se o drive Z:\\ está acessível e o arquivo existe em Z:\\Dados\\"
    )

inicio_extracao = perf_counter()

df = pd.read_excel(
    EXCEL_INDICE_RMA,
    sheet_name="Planilha1",
)

# ----- NORMALIZAÇÃO -----

df.columns = [col.strip().upper() for col in df.columns]

# Remove linhas sem ID
df = df.dropna(subset=["ID"])

print(f"  Tempo extração: {perf_counter() - inicio_extracao:.1f}s")
print(f"  Linhas lidas do Excel (IndiceRMA): {len(df):,}")

# ----- CARGA -----

engine    = get_engine_prata()
dtype_map = build_dtype_map(df)

inicio_carga = perf_counter()
full_reload(engine, df, schema_prata, tabela_destino, chunksize=1000)
print(f"  Tempo carga: {perf_counter() - inicio_carga:.1f}s")

print(f"  Tempo total {tabela_destino}: {perf_counter() - inicio_total:.1f}s")
