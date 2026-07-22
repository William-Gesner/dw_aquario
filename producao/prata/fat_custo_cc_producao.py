"""
Carga do custo orçado x realizado por centro de custo do BI Produção --
camada Prata.

Origem  : DW_BRONZE.E626ORC, E047NTG, E621MTC (todas exclusivas do
          catálogo da Produção)
Destino : DW_PRATA.FAT_CUSTO_CC_PRODUCAO (era
          BIAQUARIO.USU_VBIAPROD_CUSTOCC no legado)
Carga   : full_reload (DROP + recarga completa) -- mesma estratégia do
          legado (producao/extract/vbicustocc.py).

Classificação: FATO -- valores orçado/realizado por centro de custo da
produção (CC entre 4000 e 4300), a partir da tabela 1600 em diante.
Mesma classificação TIPORC do legado (TIPMTC='31' -> REALIZADO, demais
-> ORCADO).

CORTE DE DATA (NOVO -- não existe no legado): 01/01/2021
(DATA_CORTE_PRODUCAO, config), aplicado em T2.DATINI (início de vigência
do mapa de cálculo). O legado (`vbicustocc.py`) não tinha NENHUM corte
de data nesta tabela -- decisão explícita do usuário em 21/07/2026 de
aplicar o padrão único de 2021 em toda tabela FATO com grão de data da
área, mesmo nas que o legado nunca cortou. Diferente da Regra 2 padrão
da Fase 2 (que só aplica corte novo quando o legado não tinha nenhum --
aqui foi pedido explicitamente o oposto). ATENÇÃO: isso muda o volume
visível no Power BI em relação ao legado (esconde registros com
DATINI < 2021) -- mudança de escopo consciente, não bug.

Lógica de negócio idêntica ao legado -- só a origem mudou de SAPIENS
para DW_BRONZE, e o corte de data é uma adição nova.
"""

# ----- IMPORTS -----

from time import perf_counter

import pandas as pd
from sqlalchemy import text

from core.db import get_engine_prata
from core.dtype_map import build_dtype_map
from core.loader import full_reload
from producao.config.settings import DATA_CORTE_PRODUCAO, schema_bronze, schema_prata

# ----- CONFIGURAÇÃO DA TABELA DESTINO -----

tabela_destino = "FAT_CUSTO_CC_PRODUCAO"

# ----- QUERY DE EXTRAÇÃO (lendo da Bronze) -----

query = f"""
SELECT
    T0.CODEMP,
    T0.NUMMTC,
    T2.TIPMTC,
    CASE WHEN T2.TIPMTC = '31' THEN 'REALIZADO' ELSE 'ORCADO' END AS TIPORC,
    T2.CODMTC,
    T2.DESMTC,
    T0.CODCCU,
    T0.CODNTG,
    T1.DESNTG,
    T2.DATINI,
    T2.DATFIM

FROM {schema_bronze}.E626ORC T0

JOIN {schema_bronze}.E047NTG T1
    ON  T0.CODEMP = T1.CODEMP
    AND T0.CODNTG = T1.CODNTG

JOIN {schema_bronze}.E621MTC T2
    ON  T0.CODEMP = T2.CODEMP
    AND T0.NUMMTC = T2.NUMMTC

WHERE T0.CODCCU > '4000'
  AND T0.CODCCU < '4300'
  AND T0.NUMMTC > '1600'
  AND T2.DATINI >= TO_DATE('{DATA_CORTE_PRODUCAO}', 'DD/MM/YYYY')

ORDER BY T0.NUMMTC DESC, T2.TIPMTC DESC, T2.CODMTC DESC
"""

# ----- EXTRAÇÃO -----

inicio_total = perf_counter()

engine = get_engine_prata()

inicio_extracao = perf_counter()
with engine.connect() as conn:
    df = pd.read_sql(text(query), conn)
print(f"  Tempo extração: {perf_counter() - inicio_extracao:.1f}s")

df.columns = [col.upper() for col in df.columns]
print(f"  Linhas extraídas: {len(df):,}")

# ----- CARGA -----

dtype_map = build_dtype_map(df)

inicio_carga = perf_counter()
full_reload(engine, df, schema_prata, tabela_destino, chunksize=10000, dtype_map=dtype_map)
print(f"  Tempo carga: {perf_counter() - inicio_carga:.1f}s")

print(f"  Tempo total {tabela_destino}: {perf_counter() - inicio_total:.1f}s")
