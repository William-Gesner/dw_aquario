"""
Carga do custo padrão por produto do BI Produção -- camada Prata.

Origem  : Excel manual -- Z:\\Dados\\TempoDisponivelCC.xlsx, aba 'CP'
          (mesmo arquivo usado pelo módulo Estoque -- tabelas separadas
          por módulo, mesma decisão do legado)
Destino : DW_PRATA.DIM_CUSTO_PADRAO_PRODUCAO (era
          BIAQUARIO.USU_VBIAPROD_CUSTO_PADRAO no legado)
Carga   : full_reload (DROP + recarga completa) -- mesma estratégia do
          legado (producao/extract/vbicustopadrao.py).

Classificação: DIMENSÃO -- confirmado com o usuário em 21/07/2026 via
consulta direta no legado (BIAQUARIO.USU_VBIAPROD_CUSTO_PADRAO):
324 linhas = 324 produtos distintos, sem duplicidade -- é 1 valor fixo
por produto (atributo atual, sem grão de período), não fato. Sem corte
de data (Regra 2 da Fase 2 -- dimensão nunca tem corte).

Fora da Bronze -- mesma exceção já usada nas dimensões de Excel do
Laudos RMA (07/07/2026): arquivo mantido manualmente pelo time de
negócio, sem fonte Oracle equivalente. Lê o Excel direto, igual o
legado.
"""

# ----- IMPORTS -----

from time import perf_counter

import pandas as pd

from core.db import get_engine_prata
from core.dtype_map import build_dtype_map
from core.loader import full_reload
from producao.config.settings import EXCEL_TEMPO_DISPONIVEL, schema_prata

# ----- CONFIGURAÇÃO DA TABELA DESTINO -----

tabela_destino = "DIM_CUSTO_PADRAO_PRODUCAO"

# ----- EXTRAÇÃO DO EXCEL -----

inicio_total = perf_counter()

if not EXCEL_TEMPO_DISPONIVEL.exists():
    raise FileNotFoundError(
        f"Arquivo não encontrado: {EXCEL_TEMPO_DISPONIVEL}\n"
        f"Verifique se o drive Z:\\ está acessível e o arquivo existe em Z:\\Dados\\"
    )

df = pd.read_excel(
    EXCEL_TEMPO_DISPONIVEL,
    sheet_name="CP",
    dtype=str,
)

# ----- NORMALIZAÇÃO (idêntica ao legado) -----

df.columns = [col.strip().upper() for col in df.columns]

df["CUSTO_PADRAO"] = (
    df["CUSTO_PADRAO"]
    .str.replace(",", ".", regex=False)
    .str.strip()
    .astype(float)
)

df["CODEMPRESA"] = pd.to_numeric(df["CODEMPRESA"], errors="coerce").astype("Int64")

df = df.dropna(subset=["PRODUTO", "CUSTO_PADRAO"])
df = df[df["PRODUTO"].str.strip() != ""]

print(f"  Linhas extraídas: {len(df):,}")

# ----- CARGA -----

engine    = get_engine_prata()
dtype_map = build_dtype_map(df)

inicio_carga = perf_counter()
full_reload(engine, df, schema_prata, tabela_destino, chunksize=5000, dtype_map=dtype_map)
print(f"  Tempo carga: {perf_counter() - inicio_carga:.1f}s")

print(f"  Tempo total {tabela_destino}: {perf_counter() - inicio_total:.1f}s")
