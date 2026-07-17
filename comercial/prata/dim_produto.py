"""
Carga da dimensão de produto do BI Comercial -- camada Prata.

Origem  : DW_BRONZE.E075DER, E075PRO, E012FAM, E013AGP, E022CLF
Destino : DW_PRATA.DIM_PRODUTO (era BIAQUARIO.USU_BVIPRODUTOS no legado)
Carga   : upsert (MERGE por CHAVE_ITEM) -- mesma estratégia do legado
          (comercial/extract/vbiproduto.py).

Lógica de negócio idêntica ao legado -- só a origem mudou de SAPIENS
para DW_BRONZE. Classificação: DIMENSÃO -- sem corte de data (catálogo
completo e atual de produtos/derivações).

Observação herdada do legado: o JOIN com E012FAM (alias F) existe na
query original mas nenhuma coluna dele é selecionada -- mantido
exatamente como estava (join sem uso não muda nenhum resultado, e não
é objetivo desta migração alterar comportamento nem "limpar" o que já
está validado em produção).
"""

# ----- IMPORTS -----

import pandas as pd
from sqlalchemy import text

from comercial.config.settings import schema_bronze, schema_prata
from core.db import get_engine_prata
from core.dtype_map import build_dtype_map
from core.loader import upsert

# ----- CONFIGURAÇÃO DA TABELA DESTINO -----

tabela_destino = "DIM_PRODUTO"

# ----- QUERY DE EXTRAÇÃO (lendo da Bronze) -----

query = f"""
SELECT
    D.CODAGT AS CATEGORIAID,
    TRIM(M.DESAGP) AS CATEGORIA,

    CASE
        WHEN D.CODDER IS NULL OR TRIM(D.CODDER) = '' OR D.CODDER = ' ' THEN D.CODPRO
        ELSE D.CODPRO || '-' || D.CODDER
    END AS CHAVE_ITEM,

    P.CODPRO AS CODITEM,
    TRIM(UPPER(P.DESPRO)) AS DESCITEM,
    N.CLAFIS AS CODNCM,
    D.CODGTN AS CODEAN,
    N.CODCES AS CODCEST,
    (P.PERIPI / 100) AS PERIPI,

    CASE
        WHEN D.SITDER = 'A' THEN 'ATIVO'
        ELSE 'INATIVO'
    END AS SITITEM,

    P.USU_INDFDL AS FORALINHA,
    D.COMDER AS COMPRIMENTO,
    D.ALTDER AS ALTURA,
    D.LARDER AS LARGURA,
    D.PESBRU AS PESOBRUTO,
    D.PESLIQ AS PESOLIQ

FROM {schema_bronze}.E075DER D

LEFT JOIN {schema_bronze}.E075PRO P
    ON D.CODEMP = P.CODEMP
   AND D.CODPRO = P.CODPRO

LEFT JOIN {schema_bronze}.E012FAM F
    ON P.CODEMP = F.CODEMP
   AND P.CODFAM = F.CODFAM

LEFT JOIN {schema_bronze}.E013AGP M
    ON P.CODEMP = M.CODEMP
   AND D.CODAGT = M.CODAGP

LEFT JOIN {schema_bronze}.E022CLF N
    ON P.CODCLF = N.CODCLF

WHERE D.CODEMP = 1
"""

# ----- EXTRAÇÃO -----

engine = get_engine_prata()

with engine.connect() as conn:
    df = pd.read_sql(text(query), conn)

df.columns = [col.upper() for col in df.columns]

# ----- CARGA -----

dtype_map = build_dtype_map(df)

upsert(
    engine,
    df,
    schema_prata,
    tabela_destino,
    query=query,
    chaves_merge=["CHAVE_ITEM"],
    coluna_ordem="CODITEM DESC",
    dtype_map=dtype_map,
)
