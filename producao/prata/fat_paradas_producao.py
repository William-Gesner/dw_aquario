"""
Carga do histórico de paradas do BI Produção -- camada Prata.

Origem  : DW_BRONZE.E930MPR, E018MTV, E093ETG, E044CCU (todas exclusivas
          do catálogo da Produção)
Destino : DW_PRATA.FAT_PARADAS_PRODUCAO (era
          BIAQUARIO.USU_VBIAPROD_PARADAS no legado)
Carga   : full_reload (DROP + recarga completa) -- mesma estratégia do
          legado (producao/extract/vbiparadas.py).

Classificação: FATO -- horas de parada por equipamento/centro de
recurso/data, com tipo (programado/não programado) e classificação
(Operacional/Manutenção/Utilidades/TI/Externo).

CORTE DE DATA: 01/01/2021 (DATA_CORTE_PRODUCAO, config) -- o legado
cortava em 01/01/2018 (DATA_INICIO_HISTORICO); decisão explícita do
usuário em 21/07/2026 de usar 2021 como padrão único pra toda a área,
diferente da Regra 2 padrão da Fase 2 (que manteria o corte do legado).

Lógica de negócio idêntica ao legado -- só a origem mudou de SAPIENS
para DW_BRONZE, e o corte de data mudou de 2018 para 2021.
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

tabela_destino = "FAT_PARADAS_PRODUCAO"

# ----- QUERY DE EXTRAÇÃO (lendo da Bronze) -----

query = f"""
SELECT
    T0.CODETG,
    T0.CODCRE,
    T2.CODCCU,
    T3.DESCCU,
    T0.IDEBEM,
    T0.DATMPR,
    T0.CODMTV,
    T1.DESMTV,
    T1.ABRMTV,
    T1.USU_TIPMTV                                   AS TIPMTV,
    CASE WHEN T1.USU_TIPMTV = 1
         THEN 'Programado'
         ELSE 'Nao Programado'
    END                                             AS DESTIP,
    T1.USU_CLAMTV                                   AS CLAMTV,
    CASE WHEN T1.USU_CLAMTV = 1 THEN 'Operacional'
         WHEN T1.USU_CLAMTV = 2 THEN 'Manutencao'
         WHEN T1.USU_CLAMTV = 3 THEN 'Utilidades'
         WHEN T1.USU_CLAMTV = 4 THEN 'TI'
         WHEN T1.USU_CLAMTV = 5 THEN 'Externo'
         ELSE '*** VAZIO ***'
    END                                             AS DESCLA,
    T0.SEQMPR,
    T0.HORINI                                       AS HORCHA,
    ROUND(T0.HORINI / 60, 2)                        AS HORINI,
    ROUND(T0.HORFIM / 60, 2)                        AS HORFIM

FROM {schema_bronze}.E930MPR T0

LEFT JOIN {schema_bronze}.E018MTV T1
    ON  T1.CODEMP = T0.CODEMP
    AND T1.CODMTV = T0.CODMTV

LEFT JOIN {schema_bronze}.E093ETG T2
    ON  T2.CODEMP = T0.CODEMP
    AND T2.CODETG = T0.CODETG

LEFT JOIN {schema_bronze}.E044CCU T3
    ON  T3.CODEMP = T0.CODEMP
    AND T3.CODCCU = T2.CODCCU

WHERE T0.DATMPR > TO_DATE('{DATA_CORTE_PRODUCAO}', 'DD/MM/YYYY')
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
