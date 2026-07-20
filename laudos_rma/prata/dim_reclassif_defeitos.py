"""
Carga da dimensão de reclassificação de defeitos do BI Laudos RMA -- camada Prata.

Origem  : Excel manual -- DefeitosProdutosRMA.xlsx, aba 'DescDefeitos'
          (Z:\\Dados\\ -- NÃO passa pela Bronze, não existe origem Oracle
          equivalente; lida direto do Excel, igual o legado sempre fez)
Destino : DW_PRATA.DIM_RECLASSIF_DEFEITOS
          (era BIAQUARIO.USU_VBIARMA_RECLASSIF_DEFEITOS no legado)
Carga   : full_reload (DROP + recarga completa) -- mesma estratégia do
          legado (aquario/laudos_rma/extract/vbireclassif_defeitos.py).

Lógica de negócio idêntica ao legado -- nenhuma coluna, filtro ou
transformação foi alterada. Classificação: DIMENSÃO -- sem corte de data
(reclassificação vale pro cadastro inteiro).

A chave PROD_COD_DEF replica o @ProdCodDef do Qlik (Produto|Código) --
usada para JOIN com FAT_LAUDOS no modelo semântico do Power BI, não
dentro desta extração.
"""

# ----- IMPORTS -----

from time import perf_counter

import pandas as pd

from core.db import get_engine_prata
from core.dtype_map import build_dtype_map
from core.loader import full_reload
from laudos_rma.config.settings import EXCEL_DEFEITOS_PRODUTOS, schema_prata

# ----- CONFIGURAÇÃO DA TABELA DESTINO -----

tabela_destino = "DIM_RECLASSIF_DEFEITOS"

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
    sheet_name="DescDefeitos",
    dtype=str,   # lê tudo como string -- colunas CÓDIGO e NOVO CÓDIGO têm tipo misto no Excel
)

# ----- NORMALIZAÇÃO -----

df.columns = [col.strip().upper() for col in df.columns]

# Limpa espaços e quebras de linha em todas as colunas string
for col in df.columns:
    df[col] = df[col].astype(str).str.strip()

# Remove linhas sem produto ou código
df = df[df["PRODUTO"].notna()]
df = df[~df["PRODUTO"].isin(["", "nan"])]
df = df[df["CÓDIGO"].notna()]
df = df[~df["CÓDIGO"].isin(["", "nan"])]

# Chave de relacionamento -- replica @ProdCodDef do Qlik: Produto|Código
df["PROD_COD_DEF"] = df["PRODUTO"] + "|" + df["CÓDIGO"]

# Remove linhas com chave inválida -- PRODUTO ou CÓDIGO vazios resultam em '|' ou ' | '
df = df[df["PROD_COD_DEF"].str.replace("|", "", regex=False).str.strip() != ""]

print(f"  Tempo extração: {perf_counter() - inicio_extracao:.1f}s")
print(f"  Linhas lidas do Excel (DescDefeitos): {len(df):,}")

# ----- CARGA -----

engine    = get_engine_prata()
dtype_map = build_dtype_map(df)

inicio_carga = perf_counter()
full_reload(engine, df, schema_prata, tabela_destino, chunksize=5000)
print(f"  Tempo carga: {perf_counter() - inicio_carga:.1f}s")

print(f"  Tempo total {tabela_destino}: {perf_counter() - inicio_total:.1f}s")
