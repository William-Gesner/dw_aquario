"""
Carga da dimensão de representante do BI Comercial -- camada Prata.

Origem  : DW_BRONZE.E090REP, E026RAM, USU_T017RVR
Destino : DW_PRATA.DIM_REPRESENTANTE
          (era BIAQUARIO.USU_VBIREPRESENTANTES no legado)
Carga   : upsert (MERGE por CODREP) -- mesma estratégia do legado
          (comercial/extract/vbirepresentantes.py).

Lógica de negócio idêntica ao legado -- só a origem mudou de SAPIENS
para DW_BRONZE. Classificação: DIMENSÃO -- sem corte de data (cadastro
completo e atual de representantes).
"""

# ----- IMPORTS -----

import pandas as pd
from sqlalchemy import text

from comercial.config.settings import schema_bronze, schema_prata
from core.db import get_engine_prata
from core.dtype_map import build_dtype_map
from core.loader import upsert

# ----- CONFIGURAÇÃO DA TABELA DESTINO -----

tabela_destino = "DIM_REPRESENTANTE"

# ----- QUERY DE EXTRAÇÃO (lendo da Bronze) -----

query = f"""
SELECT
    R.CODREP,

    CASE
        WHEN R.TIPREP = 'F' THEN LPAD(R.CGCCPF, 11, '0')
        ELSE LPAD(R.CGCCPF, 14, '0')
    END AS DOCREP,

    TRIM(UPPER(R.NOMREP)) AS NOMEREP,
    TRIM(UPPER(R.APEREP)) AS APEREP,

    CASE
       WHEN R.USU_TIPREP = 1 THEN 'VENDEDOR'
       WHEN R.USU_TIPREP = 2 THEN 'RCA'
       WHEN R.USU_TIPREP = 3 THEN 'B2C'
       ELSE 'OUTROS'
    END AS TIPOREP,

    CASE
       WHEN R.SITWMW = 'A' THEN 'ATIVO'
       ELSE 'INATIVO'
    END AS SITREP,

    UPPER(R.USU_CODRAM) AS CODRAMO,
    TRIM(UPPER(RAM.DESRAM)) AS RAMO,
    TRIM(UPPER(R.CIDREP)) AS CIDADE,
    TRIM(UPPER(R.SIGUFS)) AS ESTADO,
    REGEXP_REPLACE(R.FONREP, '[^0-9]', '') AS TELEFONE,
    TRIM(LOWER(R.INTNET)) AS EMAIL,
    R.USU_CODRVR AS ID_REGIONAL,
    TRIM(UPPER(REG.USU_NOMRVR)) AS NOME_REGIONAL,
    TRUNC(R.DATCAD) AS DT_CADASTRO

FROM {schema_bronze}.E090REP R

LEFT JOIN {schema_bronze}.E026RAM RAM
    ON R.USU_CODRAM = RAM.CODRAM

LEFT JOIN {schema_bronze}.USU_T017RVR REG
    ON R.USU_CODRVR = REG.USU_CODRVR
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
    chaves_merge=["CODREP"],
    coluna_ordem="DT_CADASTRO DESC",
    dtype_map=dtype_map,
)
