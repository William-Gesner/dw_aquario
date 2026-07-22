"""
Carga da dimensão de produtos do BI Produção -- camada Prata.

Origem  : DW_BRONZE.E075PRO, E075DER, E013AGP, E012FAM (todas
          compartilhadas com o Comercial -- mantidas por
          comercial/bronze/extrator.py, ver Regra 8 do
          doc_nova_arquitetura.md)
Destino : DW_PRATA.DIM_PRODUTO_PRODUCAO (era
          BIAQUARIO.USU_VBIAPROD_PRODUTO no legado)
Carga   : upsert (MERGE por CODEMP + CODPRO) -- mesma estratégia e
          mesma chave do legado (producao/extract/vbiproduto.py).

Classificação: DIMENSÃO -- sem corte de data (Regra 2 da Fase 2).

DIFERENTE de DIM_PRODUTO (Comercial): campos específicos de manufatura
(CODORI, CODAGE, CURABC, DEPPAD) que não existem na dimensão do
Comercial -- sufixo `_PRODUCAO` evita colisão de nome no schema DW_PRATA
compartilhado.

Lógica de negócio idêntica ao legado -- só a origem mudou de SAPIENS
para DW_BRONZE. Exclui produtos de origem 'SER' (serviços), mesmo filtro
do legado.
"""

# ----- IMPORTS -----

from time import perf_counter

import pandas as pd
from sqlalchemy import text

from core.db import get_engine_prata
from core.dtype_map import build_dtype_map
from core.loader import upsert
from producao.config.settings import schema_bronze, schema_prata

# ----- CONFIGURAÇÃO DA TABELA DESTINO -----

tabela_destino = "DIM_PRODUTO_PRODUCAO"

# ----- QUERY DE EXTRAÇÃO (lendo da Bronze) -----

query = f"""
SELECT
    T0.CODEMP,
    T0.CODPRO,
    T0.DESPRO,
    T1.CODDER,
    T0.CODFAM,
    T3.DESFAM,
    T0.UNIMED,
    T0.TIPPRO,
    T0.CODORI,
    T0.CODAGE,
    T1.CODAGT,
    T2.DESAGP,
    T0.SITPRO,
    T1.CURABC,
    T0.DEPPAD,
    NVL(CASE WHEN T0.USU_INDFDL = ' ' THEN 'N' ELSE T0.USU_INDFDL END, 'N') AS USU_INDFDL

FROM {schema_bronze}.E075PRO T0

LEFT JOIN {schema_bronze}.E075DER T1
    ON  T1.CODEMP = T0.CODEMP
    AND T1.CODPRO = T0.CODPRO

LEFT JOIN {schema_bronze}.E013AGP T2
    ON  T2.CODEMP = T0.CODEMP
    AND T2.CODAGP = T1.CODAGT

LEFT JOIN {schema_bronze}.E012FAM T3
    ON  T3.CODEMP = T0.CODEMP
    AND T3.CODFAM = T0.CODFAM

WHERE T0.CODEMP = 1
  AND T0.CODORI NOT IN ('SER')
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
    chaves_merge=["CODEMP", "CODPRO"],
    coluna_ordem="CODPRO ASC",
    dtype_map=dtype_map,
)
print(f"  Tempo carga: {perf_counter() - inicio_carga:.1f}s")

print(f"  Tempo total {tabela_destino}: {perf_counter() - inicio_total:.1f}s")
