"""
Carga da meta de utilização do BI Produção -- camada Prata.

Origem  : Excel manual -- Z:\\Dados\\TempoDisponivelCC.xlsx, aba 'BD'
          (mesmo arquivo usado por dim_custo_padrao_producao.py, aba
          diferente)
Destino : DW_PRATA.FAT_UTILIZACAO_META_PRODUCAO (era
          BIAQUARIO.USU_VBIAPROD_UTILIZACAO_META no legado)
Carga   : full_reload (DROP + recarga completa) -- mesma estratégia do
          legado (producao/extract/vbiutilizacaometa.py).

Classificação: FATO -- meta de utilização diária por centro de custo
(minutos disponíveis, dias úteis, limite superior), medida por período
(Data) x dimensão (centro de custo).

CORTE DE DATA (NOVO -- não existe no legado): 01/01/2021
(DATA_CORTE_PRODUCAO, config), aplicado em DATA. O legado
(`vbiutilizacaometa.py`) não tinha nenhum corte -- decisão explícita do
usuário em 21/07/2026 de aplicar o padrão único de 2021 em toda tabela
FATO com grão de data da área. Na prática, como é um arquivo de meta
mantido manualmente pelo time de engenharia/produção (normalmente com
datas correntes/futuras, não um histórico profundo), o corte tende a não
remover nada -- mas fica aplicado por consistência com o restante da
área.

Fora da Bronze -- mesma exceção já usada nas dimensões de Excel do
Laudos RMA (07/07/2026). Lê o Excel direto, igual o legado.
"""

# ----- IMPORTS -----

from datetime import datetime
from time import perf_counter

import pandas as pd

from core.db import get_engine_prata
from core.dtype_map import build_dtype_map
from core.loader import full_reload
from producao.config.settings import DATA_CORTE_PRODUCAO, EXCEL_TEMPO_DISPONIVEL, schema_prata

# ----- CONFIGURAÇÃO DA TABELA DESTINO -----

tabela_destino = "FAT_UTILIZACAO_META_PRODUCAO"

# ----- EXTRAÇÃO DO EXCEL -----

inicio_total = perf_counter()

if not EXCEL_TEMPO_DISPONIVEL.exists():
    raise FileNotFoundError(
        f"Arquivo não encontrado: {EXCEL_TEMPO_DISPONIVEL}\n"
        f"Verifique se o drive Z:\\ está acessível e o arquivo existe em Z:\\Dados\\"
    )

df = pd.read_excel(
    EXCEL_TEMPO_DISPONIVEL,
    sheet_name="BD",
)

# ----- NORMALIZAÇÃO (idêntica ao legado) -----

df.columns = [col.strip().upper() for col in df.columns]

# Remove linhas sem data ou centro de custo
df = df.dropna(subset=["DATA", "CD_CENTROCUSTO"])

# Garante tipos corretos
df["CD_CENTROCUSTO"] = df["CD_CENTROCUSTO"].astype(str).str.strip()
df["MIN_DIA"]        = pd.to_numeric(df["MIN_DIA"],        errors="coerce").fillna(0)
df["DIAS_UTEIS"]     = pd.to_numeric(df["DIAS_UTEIS"],     errors="coerce").fillna(0)
df["LIMITE_SUPERIOR"]= pd.to_numeric(df["LIMITE_SUPERIOR"],errors="coerce").fillna(0)

# ----- CORTE DE DATA -----

corte = datetime.strptime(DATA_CORTE_PRODUCAO, "%d/%m/%Y")
df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce")
df = df[df["DATA"] >= corte]

print(f"  Linhas extraídas (após corte {DATA_CORTE_PRODUCAO}): {len(df):,}")

# ----- CARGA -----

engine    = get_engine_prata()
dtype_map = build_dtype_map(df)

inicio_carga = perf_counter()
full_reload(engine, df, schema_prata, tabela_destino, chunksize=5000, dtype_map=dtype_map)
print(f"  Tempo carga: {perf_counter() - inicio_carga:.1f}s")

print(f"  Tempo total {tabela_destino}: {perf_counter() - inicio_total:.1f}s")
