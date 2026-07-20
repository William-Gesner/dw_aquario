"""
Carga da dimensão de regional do BI Comercial -- camada Prata.

Origem  : DW_BRONZE.USU_T017RVR, R999USU
Destino : DW_PRATA.DIM_REGIONAL (era BIAQUARIO.USU_VBIREGIONAIS no legado)
Carga   : upsert (MERGE por ID_REGIONAL) -- mesma estratégia do legado
          (comercial/extract/vbiregionais.py).

Lógica de negócio idêntica ao legado -- só a origem mudou de SAPIENS
para DW_BRONZE. Classificação: DIMENSÃO -- sem corte de data.

MELHORIA (combinada, resultado idêntico ao legado): a query original
tinha um CASE com 4 exceções manuais embutidas (3 por ID_REGIONAL + 1
por login) misturadas com a regra genérica de formatação de nome. Essas
exceções foram isoladas em 2 CTEs no topo da query
(OVERRIDES_POR_REGIONAL, OVERRIDES_POR_LOGIN) -- mesmo resultado linha a
linha, mas a exceção fica num bloco só, fácil de achar e de estender
(adicionar uma linha de UNION ALL), em vez de enterrada dentro do CASE
principal.

IMPORTANTE: os overrides precisam estar dentro da SQL (não em Python
pós-processando o DataFrame) -- o upsert() reexecuta a query original
como SQL puro dentro do próprio MERGE; qualquer transformação feita só
no DataFrame em Python nunca chegaria no banco (mesma causa raiz do bug
corrigido em core/loader.py para a coluna de metadado).

Prioridade replicada EXATAMENTE como no CASE legado, via COALESCE (o
primeiro valor não-nulo vence): override por ID_REGIONAL (5/7/9) tem
prioridade sobre o override por login (rescudero), que por sua vez tem
prioridade sobre o cálculo genérico (REPLACE do login).
"""

# ----- IMPORTS -----

from time import perf_counter

import pandas as pd
from sqlalchemy import text

from comercial.config.settings import schema_bronze, schema_prata
from core.db import get_engine_prata
from core.dtype_map import build_dtype_map
from core.loader import upsert

# ----- CONFIGURAÇÃO DA TABELA DESTINO -----

tabela_destino = "DIM_REGIONAL"

# ----- QUERY DE EXTRAÇÃO (lendo da Bronze) -----

# Pra adicionar uma nova exceção: só acrescentar uma linha "UNION ALL
# SELECT ..." na CTE correspondente -- não mexe no SELECT principal.
query = f"""
WITH OVERRIDES_POR_REGIONAL AS (
    SELECT 5 AS ID_REGIONAL, 'EDINILDO MAGALHÃES' AS RESPONSAVEL FROM DUAL
    UNION ALL
    SELECT 7, 'JOW SENDESKI' FROM DUAL
    UNION ALL
    SELECT 9, 'MÁRCIO SENDESKI' FROM DUAL
),
OVERRIDES_POR_LOGIN AS (
    SELECT 'rescudero' AS LOGIN, 'RICARDO ESCUDERO' AS RESPONSAVEL FROM DUAL
)
SELECT
    R.USU_CODRVR AS ID_REGIONAL,
    UPPER(R.USU_NOMRVR) AS REGIONAL,
    UPPER('R' || TO_CHAR(R.USU_CODRVR, 'FM00') || ' - ' || R.USU_NOMRVR) AS NOME_REGIONAL,

    COALESCE(
        OR_REG.RESPONSAVEL,
        OR_LOGIN.RESPONSAVEL,
        CASE
            WHEN COORD.NOMUSU IS NULL THEN 'NÃO IDENTIFICADO'
            ELSE UPPER(REPLACE(COORD.NOMUSU, '.', ' '))
        END
    ) AS RESPONSAVEL,

    CASE
        WHEN ASSIST.NOMUSU IS NULL THEN 'NÃO IDENTIFICADO'
        ELSE UPPER(REPLACE(ASSIST.NOMUSU, '.', ' '))
    END AS ASSISTENTE,

    R.USU_DATGER AS DT_CADASTRO

FROM {schema_bronze}.USU_T017RVR R

LEFT JOIN {schema_bronze}.R999USU COORD
    ON R.USU_USUCOR = COORD.CODUSU

LEFT JOIN {schema_bronze}.R999USU ASSIST
    ON R.USU_USUASS = ASSIST.CODUSU

LEFT JOIN OVERRIDES_POR_REGIONAL OR_REG
    ON OR_REG.ID_REGIONAL = R.USU_CODRVR

LEFT JOIN OVERRIDES_POR_LOGIN OR_LOGIN
    ON OR_LOGIN.LOGIN = LOWER(COORD.NOMUSU)
"""

# ----- EXTRAÇÃO -----

inicio_total = perf_counter()

engine = get_engine_prata()

inicio_extracao = perf_counter()
with engine.connect() as conn:
    df = pd.read_sql(text(query), conn)
print(f"  Tempo extração: {perf_counter() - inicio_extracao:.1f}s")

df.columns = [col.upper() for col in df.columns]

# ----- CARGA -----

dtype_map = build_dtype_map(df)

inicio_carga = perf_counter()
upsert(
    engine,
    df,
    schema_prata,
    tabela_destino,
    query=query,
    chaves_merge=["ID_REGIONAL"],
    coluna_ordem="DT_CADASTRO DESC",
    dtype_map=dtype_map,
)
print(f"  Tempo carga: {perf_counter() - inicio_carga:.1f}s")

print(f"  Tempo total {tabela_destino}: {perf_counter() - inicio_total:.1f}s")
