"""
Carga da dimensão de classificação de produtos do BI Laudos RMA -- camada Prata.

Origem  : Excel manual -- DefeitosProdutosRMA.xlsx, aba 'ClassifProdutos'
          (Z:\\Dados\\ -- NÃO passa pela Bronze, lida direto do Excel,
          igual o legado sempre fez)
Destino : DW_PRATA.DIM_RECLASSIF_PRODUTOS
          (era BIAQUARIO.USU_VBIARMA_RECLASSIF_PRODUTOS no legado)
Carga   : full_reload (DROP + recarga completa) -- mesma estratégia do
          legado (aquario/laudos_rma/extract/vbireclassif_produtos.py).

Lógica de negócio idêntica ao legado -- nenhuma coluna, filtro ou
transformação foi alterada. Classificação: DIMENSÃO -- sem corte de data.

A chave CD_PRODUTO replica o @Cd_Produto do Qlik -- usada para JOIN com
FAT_LAUDOS no modelo semântico do Power BI, não dentro desta extração.
"""

# ----- IMPORTS -----

from time import perf_counter

import pandas as pd

from core.db import get_engine_prata
from core.dtype_map import build_dtype_map
from core.loader import full_reload
from laudos_rma.config.settings import EXCEL_DEFEITOS_PRODUTOS, schema_prata

# ----- CONFIGURAÇÃO DA TABELA DESTINO -----

tabela_destino = "DIM_RECLASSIF_PRODUTOS"

# ----- EXTRAÇÃO DO EXCEL -----

inicio_total = perf_counter()

if not EXCEL_DEFEITOS_PRODUTOS.exists():
    raise FileNotFoundError(
        f"Arquivo não encontrado: {EXCEL_DEFEITOS_PRODUTOS}\n"
        f"Verifique se o drive Z:\\ está acessível e o arquivo existe em Z:\\Dados\\"
    )

inicio_extracao = perf_counter()

df = pd.read_excel(
    EXCEL_DEFEITOS_PRODUTOS,
    sheet_name="ClassifProdutos",
    dtype=str,   # lê tudo como string -- CD_PRODUTO tem tipo misto (int e str) no Excel
)

# ----- NORMALIZAÇÃO -----

df.columns = [col.strip().upper() for col in df.columns]

# Limpa espaços em todas as colunas
for col in df.columns:
    df[col] = df[col].astype(str).str.strip()

# Remove linhas sem código de produto
df = df[df["CÓD. PRODUTO"].notna()]
df = df[~df["CÓD. PRODUTO"].isin(["", "nan"])]

# Renomeia para nomes sem caracteres especiais -- compatível com Oracle
# Inclui colunas extras encontradas no Excel (CÓD. SITUAÇÃO 2, SITUAÇÃO 2)
rename_map = {
    "CÓD. PRODUTO":       "CD_PRODUTO",
    "NOVO CÓDIGO":        "CD_PRODUTO_NOVO",
    "CÓD. CLASSIFICAÇÃO": "CD_CLASSIF_PROD",
    "CLASSIFICAÇÃO":      "DS_CLASSIF_PROD",
    "CÓD. SITUAÇÃO":      "CD_SIT_INDICADOR",
    "SITUAÇÃO":           "DS_SIT_INDICADOR",
    "CÓD. SITUAÇÃO 2":    "CD_SIT_INDICADOR_2",
    "SITUAÇÃO 2":         "DS_SIT_INDICADOR_2",
}
df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

print(f"  Tempo extração: {perf_counter() - inicio_extracao:.1f}s")
print(f"  Linhas lidas do Excel (ClassifProdutos): {len(df):,}")

# ----- CARGA -----

engine    = get_engine_prata()
dtype_map = build_dtype_map(df)

inicio_carga = perf_counter()
full_reload(engine, df, schema_prata, tabela_destino, chunksize=5000)
print(f"  Tempo carga: {perf_counter() - inicio_carga:.1f}s")

print(f"  Tempo total {tabela_destino}: {perf_counter() - inicio_total:.1f}s")
