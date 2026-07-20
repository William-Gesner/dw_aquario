"""
Carga do fato de vendas (denominador do Índice RMA) do BI Laudos RMA -- camada Prata.

Origem  : DW_BRONZE.E140NFV, E140IPV, E140IDE, E001TNS (tabelas
          compartilhadas com o Comercial -- ver
          laudos_rma/bronze/tabelas.py, TABELAS_COMPARTILHADAS_COM_COMERCIAL)
Destino : DW_PRATA.FAT_VENDAS_RMA (era BIAQUARIO.USU_VBIARMA_VENDAS no
          legado)
Carga   : full_reload (DROP + recarga completa) -- mesma estratégia do
          legado (aquario/laudos_rma/extract/vbivendas.py).

Classificação: FATO -- grão mês (LAST_DAY) x produto, não por transação.
Calcula o volume médio de vendas dos últimos 6 meses por produto/mês,
usado como denominador no cálculo do Índice RMA.

Corte de data: DATA_CORTE_LAUDOS (config, "01/01/2023") -- já existia no
legado, mantido sem alteração (Regra 2: só aplicamos corte novo quando o
legado não tinha nenhum).

----------------------------------------------------------------------
MELHORIA APLICADA (20/07/2026): agregação prévia + window function, em
vez de subquery correlacionada por linha
----------------------------------------------------------------------
A query original (legado e nossa 1ª versão) calculava QTDMED com uma
SUBQUERY CORRELACIONADA no SELECT -- reexecutada uma vez PARA CADA LINHA
do JOIN principal, antes do GROUP BY agrupar por mês/produto. Contra a
Bronze, o JOIN principal (E140NFV x E140IPV x E140IDE x E001TNS, com os
filtros do WHERE) produz ~210 mil linhas -- ou seja, a subquery rodava
~210 mil vezes, mesmo o resultado final tendo só 1 linha por mês x
produto (grão real da tabela). Isso travou por mais de 1h30 na VM (contra
190s do legado no Sapiens), mesmo depois de confirmar índice e
estatística atualizada nas 4 tabelas -- não era falta de índice, era o
número de vezes que a subquery precisava rodar.

Reescrita em 2 passos, mesmo resultado matemático:
    1. Agrega vendas por mês x produto UMA VEZ (CTE VENDAS_MES_PRODUTO)
       -- sem o corte de 01/01/2023 aqui de propósito, porque o cálculo
       de QTDMED de um mês de referência de janeiro/2023 precisa olhar
       pra vendas de meses ANTERIORES a 2023 (mesmo comportamento do
       legado, que também não aplicava corte dentro da subquery).
    2. Usa SUM(...) OVER (PARTITION BY CODPRO ORDER BY MES RANGE BETWEEN
       INTERVAL '6' MONTH PRECEDING AND INTERVAL '1' MONTH PRECEDING)
       pra calcular a soma móvel dos 6 meses anteriores a cada mês --
       calculado uma vez por combinação (mês, produto) já agregada, não
       mais por linha de venda. RANGE (não ROWS) porque lida
       corretamente com meses sem venda de um produto (não quebra a
       janela de 6 meses corridos).
    3. O corte de DATA_CORTE_LAUDOS só é aplicado no final, filtrando
       quais (mês, produto) entram no resultado -- igual o legado só
       cortava o T0 externo, nunca o universo usado pra calcular QTDMED.

Resultado esperado idêntico ao legado -- validado pela
conferencia_fat_vendas_rma.py (MINUS dado a dado) antes de considerar
esta tabela pronta. Se divergir, a conferência pega.
"""

# ----- IMPORTS -----

from time import perf_counter

import pandas as pd
from sqlalchemy import text

from core.db import get_engine_prata
from core.dtype_map import build_dtype_map
from core.loader import full_reload
from laudos_rma.config.settings import DATA_CORTE_LAUDOS, schema_bronze, schema_prata

# ----- CONFIGURAÇÃO DA TABELA DESTINO -----

tabela_destino = "FAT_VENDAS_RMA"

# ----- QUERY DE EXTRAÇÃO (lendo da Bronze) -----

# Ver "MELHORIA APLICADA" no docstring do módulo -- agrega por mês x
# produto uma vez (VENDAS_MES_PRODUTO) e calcula a soma móvel de 6 meses
# com window function (COM_ROLLING), em vez de subquery correlacionada
# por linha.
query = f"""
WITH VENDAS_MES_PRODUTO AS (
    SELECT
        TRUNC(T0.DATEMI, 'MM') AS MES,
        T1.CODPRO              AS CODPRO,
        SUM(T1.QTDFAT)         AS QTD_MES

    FROM {schema_bronze}.E140NFV T0

    LEFT JOIN {schema_bronze}.E140IPV T1
        ON  T0.CODEMP = T1.CODEMP
        AND T0.CODFIL = T1.CODFIL
        AND T0.CODSNF = T1.CODSNF
        AND T0.NUMNFV = T1.NUMNFV

    LEFT JOIN {schema_bronze}.E140IDE T2
        ON  T0.CODEMP = T2.CODEMP
        AND T0.CODFIL = T2.CODFIL
        AND T0.CODSNF = T2.CODSNF
        AND T0.NUMNFV = T2.NUMNFV

    LEFT JOIN {schema_bronze}.E001TNS T3
        ON  T1.CODEMP = T3.CODEMP
        AND T1.TNSPRO = T3.CODTNS

    WHERE T0.CODEMP  = 1
      AND T0.SITNFV  = '2'
      AND T0.TIPNFS  IN (1, 9)
      AND T2.SITDOE  = 3
      AND T3.VENFAT  = 'S'

    GROUP BY TRUNC(T0.DATEMI, 'MM'), T1.CODPRO
),
COM_ROLLING AS (
    SELECT
        MES,
        CODPRO,
        SUM(QTD_MES) OVER (
            PARTITION BY CODPRO
            ORDER BY MES
            RANGE BETWEEN INTERVAL '6' MONTH PRECEDING AND INTERVAL '1' MONTH PRECEDING
        ) AS QTDMED
    FROM VENDAS_MES_PRODUTO
)
SELECT
    1                                AS TIPREG,
    LAST_DAY(MES)                    AS DATREF,
    LAST_DAY(ADD_MONTHS(MES, -1))    AS DATFIM,
    ADD_MONTHS(MES, -6)              AS DATINI,
    1                                AS CODEMP,
    CODPRO,
    QTDMED
FROM COM_ROLLING
WHERE MES >= TO_DATE('{DATA_CORTE_LAUDOS}', 'DD/MM/YYYY')
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

# ----- CHAVE DE RELACIONAMENTO -----

# Replica @VendaMêsAnoProduto do Qlik Sense: MONTH(DATREF)|YEAR(DATREF)|CODPRO
# Usada para JOIN com FAT_LAUDOS no modelo semântico do Power BI, não
# dentro desta extração.
df["DATREF"] = pd.to_datetime(df["DATREF"], errors="coerce")
df["VENDA_MES_ANO_PRODUTO"] = (
    df["DATREF"].dt.month.astype(str) + "|" +
    df["DATREF"].dt.year.astype(str)  + "|" +
    df["CODPRO"].astype(str)
)

# ----- CARGA -----

dtype_map = build_dtype_map(df)

inicio_carga = perf_counter()
full_reload(engine, df, schema_prata, tabela_destino, chunksize=10000)
print(f"  Tempo carga: {perf_counter() - inicio_carga:.1f}s")

print(f"  Tempo total {tabela_destino}: {perf_counter() - inicio_total:.1f}s")
