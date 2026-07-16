"""
Carga da dimensão de condição de pagamento do BI Comercial -- camada Prata.

Origem  : DW_BRONZE.E028CPG (mantida pela camada Bronze do Comercial)
Destino : DW_PRATA.DIM_CONDICAO_PAGAMENTO
          (era BIAQUARIO.USU_VBIACONDPGTO no projeto legado)
Carga   : upsert (MERGE por CODCPG) -- mesma estratégia do legado
          (comercial/extract/vbicondpgto.py), fixa, sem decisão
          automática full x incremental (isso é só da Bronze).

Lógica de negócio idêntica ao legado -- nenhuma coluna, filtro ou
transformação foi alterada. Só a origem mudou de SAPIENS para DW_BRONZE.
Classificação: DIMENSÃO -- sem corte de data (universo completo e atual
das condições de pagamento cadastradas).

PRÉ-REQUISITO DE BANCO: o usuário DW_PRATA precisa ter GRANT SELECT em
DW_BRONZE.E028CPG -- a query abaixo roda inteira dentro do MERGE,
executado pela conexão Prata (mesmo padrão que a Bronze já usa pra ler
do SAPIENS estando conectada como DW_BRONZE).
"""

# ----- IMPORTS -----

import pandas as pd
from sqlalchemy import text

from comercial.config.settings import schema_bronze, schema_prata
from core.db import get_engine_prata
from core.dtype_map import build_dtype_map
from core.loader import upsert

# ----- CONFIGURAÇÃO DA TABELA DESTINO -----

tabela_destino = "DIM_CONDICAO_PAGAMENTO"

# ----- QUERY DE EXTRAÇÃO (lendo da Bronze) -----

# CODEMP=1 mantido explicitamente mesmo a Bronze já contendo só Aquário --
# defesa extra, mesma prática já usada em outras validações do projeto
# (custa nada e protege contra um eventual bug na extração da Bronze).
query = f"""
SELECT
    CP.CODCPG AS CODCPG,
    TRIM(UPPER(CP.DESCPG)) AS DESCPG,
    CP.PRZMED || ' PM - ' || TRIM(UPPER(CP.DESCPG)) AS DESCPGTO,
    CP.ABRCPG AS ABREVCPG,
    CP.PRZMED AS PRZMED,
    CP.QTDPAR AS QTDPARC,
    CP.SITCPG,
    CASE
        WHEN CP.SITCPG = 'A' THEN 'ATIVA'
        ELSE 'INATIVA'
    END AS SITCPG_DESC,
    TO_CHAR(CP.DATGER, 'DD/MM/YYYY') AS DATCAD,
    TO_CHAR(CP.DATATU, 'DD/MM/YYYY') AS ULTATU
FROM {schema_bronze}.E028CPG CP
WHERE CP.CODEMP = 1
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
    chaves_merge=["CODCPG"],
    coluna_ordem="ULTATU DESC",
    dtype_map=dtype_map,
)
