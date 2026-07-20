"""
Carga do fato de metas de vendas do BI Comercial -- camada Prata.

Origem  : DW_BRONZE.USU_T101MET, USU_T101TIP, USU_T101CRI, USU_T017RVR,
          E090REP, E013AGP, E075PRO
Destino : DW_PRATA.FAT_METAS (era BIAQUARIO.USU_VBIMETAS no legado)
Carga   : upsert (MERGE por CODEMP+MESANO+CODTIP+SEQREG) -- mesma
          estratégia e mesma chave (PK física de USU_T101MET) do legado
          (comercial/extract/vbimetas.py).

Lógica de negócio idêntica ao legado -- só a origem mudou de SAPIENS
para DW_BRONZE. Classificação: FATO (valor de meta por período/critério/
dimensão).

SEM CORTE DE DATA: a query original não tem nenhum filtro de data (só
WHERE M.USU_CODEMP = 1) -- diferente do padrão de 2021 combinado pra
fatos com grão de data. Mantido assim de propósito: meta é um fato de
"planejamento", não de transação, e não está confirmado se faz sentido
esconder metas anteriores a 2021 do Power BI. Não aplicar nenhum corte
aqui sem alinhar antes com o usuário -- ver observação no
doc_nova_arquitetura.md.
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

tabela_destino = "FAT_METAS"

# ----- QUERY DE EXTRAÇÃO (lendo da Bronze) -----

query = f"""
SELECT
    -- ----- CHAVE (PK física de USU_T101MET) -----
    M.USU_CODEMP                            AS CODEMP,
    M.USU_MESANO                            AS MESANO,
    M.USU_CODTIP                            AS CODTIP,
    M.USU_SEQREG                            AS SEQREG,

    -- ----- TIPO DE META -----
    TRIM(UPPER(TIP.USU_DESTIP))             AS DESC_TIPO,

    -- ----- CRITÉRIO -----
    M.USU_CODCRI                            AS CODCRI,
    TRIM(UPPER(CRI.USU_DESCRI))             AS DESC_CRITERIO,
    CRI.USU_UNICRI                          AS UNICRI,
    CASE CRI.USU_UNICRI
        WHEN 1 THEN 'QUANTIDADE'
        WHEN 2 THEN 'VALOR'
        WHEN 3 THEN 'PERCENTUAL'
        ELSE 'NÃO DEFINIDO'
    END                                     AS DESC_UNICRI,
    CRI.USU_DIRCRI                          AS DIRCRI,
    CASE CRI.USU_DIRCRI
        WHEN 1 THEN 'MAXIMIZAR'
        WHEN 2 THEN 'MINIMIZAR'
        ELSE 'NÃO DEFINIDO'
    END                                     AS DESC_DIRCRI,

    -- ----- CHAVES DE DIMENSÃO (preenchidas conforme o tipo) -----
    M.USU_CODRVR                            AS CODRVR,
    TRIM(UPPER(RVR.USU_NOMRVR))             AS NOME_REGIONAL,
    M.USU_CODREP                            AS CODREP,
    TRIM(UPPER(REP.NOMREP))                 AS NOME_REP,
    M.USU_CODAGP                            AS CODAGP,
    TRIM(UPPER(AGP.DESAGP))                 AS DESC_MIX,
    M.USU_CODPRO                            AS CODPRO,
    TRIM(UPPER(PRO.DESPRO))                 AS DESC_PRODUTO,

    -- ----- VALORES DA META -----
    M.USU_VLRMET                            AS VLR_META,
    M.USU_PESCRI                            AS PESO_CRITERIO,

    -- ----- AUDITORIA -----
    M.USU_DATGER                            AS DT_CRIACAO,
    TRIM(UPPER(M.USU_NOMUSU))              AS USUARIO

FROM {schema_bronze}.USU_T101MET M

LEFT JOIN {schema_bronze}.USU_T101TIP TIP
    ON M.USU_CODTIP = TIP.USU_CODTIP

LEFT JOIN {schema_bronze}.USU_T101CRI CRI
    ON M.USU_CODCRI = CRI.USU_CODCRI

LEFT JOIN {schema_bronze}.USU_T017RVR RVR
    ON M.USU_CODRVR = RVR.USU_CODRVR

LEFT JOIN {schema_bronze}.E090REP REP
    ON M.USU_CODREP = REP.CODREP

LEFT JOIN {schema_bronze}.E013AGP AGP
    ON M.USU_CODEMP = AGP.CODEMP
   AND M.USU_CODAGP = AGP.CODAGP

LEFT JOIN {schema_bronze}.E075PRO PRO
    ON M.USU_CODEMP = PRO.CODEMP
   AND M.USU_CODPRO = PRO.CODPRO

WHERE M.USU_CODEMP = 1
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
    chaves_merge=["CODEMP", "MESANO", "CODTIP", "SEQREG"],
    coluna_ordem="MESANO DESC",
    dtype_map=dtype_map,
)
print(f"  Tempo carga: {perf_counter() - inicio_carga:.1f}s")

print(f"  Tempo total {tabela_destino}: {perf_counter() - inicio_total:.1f}s")
