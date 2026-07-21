"""
Carga do fato de orçamento x realizado do BI OPEX -- camada Prata.

Origem  : DW_BRONZE.USU_T650ORC (orçamento), USU_T650CUS (realizado),
          E044CCU (centro de custo), E043PCM (plano de contas), R910USU
          (usuários -- join duplo, dono e coordenador do centro de custo)
Destino : DW_PRATA.FAT_ORCAMENTO_OPEX (era BIAQUARIO.USU_VBIAOPEX_ORCAMENTO
          no legado)
Carga   : full_reload (DROP + recarga completa) -- MESMA estratégia do
          legado (aquario/opex/extract/vbiopex.py). Motivo: FULL OUTER
          JOIN entre orçamento e realizado, sem chave natural 100%
          confiável para MERGE (a combinação de colunas do GROUP BY não é
          PK física de nenhum dos dois lados -- ver observação de PK em
          opex/bronze/tabelas.py).

Classificação: FATO (ORÇADO/REALIZADO mensurável por período x centro de
custo x despesa). Única tabela desta área -- o legado nunca teve
dimensão separada (tudo já vem denormalizado no resultado, ver
dw_aquario/doc_nova_arquitetura.md, seção "OPEX").

SEM CORTE DE DATA: a query original não filtra USU_MESANO -- mesma
decisão já tomada para FAT_METAS (comercial/prata/fat_metas.py). Não
aplicar corte de 01/01/2021 aqui sem alinhar antes com o usuário --
orçamento/realizado é fato de planejamento/fechamento contábil, não de
transação; esconder períodos antigos sem confirmar mudaria o resultado
em produção.

MUDANÇA REAL DE ARQUITETURA NESTA MIGRAÇÃO: o legado lê direto do Sapiens
Controladoria (servidor separado, 172.16.0.123/dbprod) a cada execução,
via engine_cont (ver vbiopex.py). Este script lê só da DW_BRONZE (já
alimentada por opex/bronze/extrator.py a partir da Controladoria) --
usa só get_engine_prata(), sem precisar mais da engine de Controladoria
aqui. O resto da lógica de negócio (JOINs, filtros, CASE de PROD/QUARTER)
é idêntico ao legado.

PARTICULARIDADE MANTIDA: CODEMP_AQUARIO_OPEX = (1, 50) -- o OPEX
consolida 2 razões sociais do grupo Aquário (exceção documentada em
opex/config/settings.py, diferente do resto do projeto que é sempre
CODEMP = 1). USU_CODMPC = '801' também mantido, igual ao legado.

PONTO JÁ INVESTIGADO (não é bug -- ver doc_nova_arquitetura.md, seção
"OPEX"): a PK real de USU_T650CUS na Bronze tem 6 colunas (inclui
USU_CTAEMP), mas o JOIN abaixo usa só 5 (sem USU_CTAEMP), igual o
legado sempre fez. Isso não causa duplicação de ORÇADO (que não é
somado, só carregado como atributo agrupado) nem soma errada de
REALIZADO (SUM(USU_SALMES) agrega corretamente todas as linhas de
USU_T650CUS com USU_CTAEMP diferente para a mesma chave de 5 colunas,
via GROUP BY) -- confirmar na conferência.

NOTA SOBRE O FULL OUTER JOIN + WHERE (comportamento do legado, mantido
como está): o WHERE filtra T1.USU_CODEMP IN (...) -- como T1 é o lado
esquerdo do FULL OUTER JOIN (USU_T650ORC), qualquer linha de
USU_T650CUS sem orçamento correspondente (T1 NULL) é descartada pelo
WHERE, porque NULL IN (...) nunca é verdadeiro. Ou seja, na prática o
FULL OUTER JOIN se comporta como um JOIN a partir do orçamento (mesmo
efeito de um LEFT JOIN de T1 para T0) -- comportamento herdado
literalmente do legado, não alterado aqui.
"""

# ----- IMPORTS -----

from time import perf_counter

import pandas as pd
from sqlalchemy import text

from opex.config.settings import CODEMP_AQUARIO_OPEX, schema_bronze, schema_prata
from core.db import get_engine_prata
from core.dtype_map import build_dtype_map
from core.loader import full_reload

# ----- CONFIGURAÇÃO DA TABELA DESTINO -----

tabela_destino = "FAT_ORCAMENTO_OPEX"

# ----- QUERY DE EXTRAÇÃO (lendo da Bronze) -----

_codemp_valores = ", ".join(str(v) for v in CODEMP_AQUARIO_OPEX)

query = f"""
SELECT
    T1.USU_CODEMP                                   AS EMP,
    T1.USU_MESANO                                   AS COMP,
    T1.USU_CODCCU                                   AS CC,
    T1.USU_CTADRE                                   AS CDESP,
    T1.USU_ORCMES                                   AS ORCADO,
    SUM(T0.USU_SALMES)                              AS REALIZADO,
    T2.DESCCU                                       AS CCUSTO,
    T2.TIPCCU                                       AS TPCC,
    T3.DESCTA                                       AS DESPESA,
    CASE
        WHEN T2.TIPCCU = 1 OR T2.TIPCCU = 2
        THEN 'Produtivo'
        ELSE 'Não Produtivo'
    END                                             AS PROD,
    T2.USU_CODRES                                   AS CODDONO,
    T4.NOMCOM                                       AS DONO,
    CASE
        WHEN TO_NUMBER(TO_CHAR(T1.USU_MESANO, 'MM')) BETWEEN 1 AND 3  THEN 'Q1'
        WHEN TO_NUMBER(TO_CHAR(T1.USU_MESANO, 'MM')) BETWEEN 4 AND 6  THEN 'Q2'
        WHEN TO_NUMBER(TO_CHAR(T1.USU_MESANO, 'MM')) BETWEEN 7 AND 9  THEN 'Q3'
        ELSE 'Q4'
    END                                             AS QUARTER,
    T2.USU_CODCOR                                   AS CODCOORD,
    T5.NOMCOM                                       AS COORD

FROM {schema_bronze}.USU_T650ORC T1

FULL OUTER JOIN {schema_bronze}.USU_T650CUS T0
    ON  T0.USU_CODEMP = T1.USU_CODEMP
    AND T0.USU_MESANO = T1.USU_MESANO
    AND T0.USU_CODMPC = T1.USU_CODMPC
    AND T0.USU_CTADRE = T1.USU_CTADRE
    AND T0.USU_CODCCU = T1.USU_CODCCU

LEFT JOIN {schema_bronze}.E044CCU T2
    ON  T1.USU_CODEMP = T2.CODEMP
    AND T1.USU_CODCCU = T2.CODCCU

LEFT JOIN {schema_bronze}.R910USU T4
    ON  T2.USU_CODRES = T4.CODENT

LEFT JOIN {schema_bronze}.R910USU T5
    ON  T2.USU_CODCOR = T5.CODENT

LEFT JOIN {schema_bronze}.E043PCM T3
    ON  T1.USU_CTADRE = T3.CTARED
    AND T1.USU_CODMPC = T3.CODMPC

WHERE T1.USU_CODEMP IN ({_codemp_valores})
  AND T1.USU_CODMPC  = '801'

GROUP BY
    T1.USU_CODEMP,
    T1.USU_MESANO,
    T1.USU_CODCCU,
    T1.USU_CTADRE,
    T1.USU_ORCMES,
    T2.DESCCU,
    T2.TIPCCU,
    T3.DESCTA,
    T2.USU_CODRES,
    T4.NOMCOM,
    T2.USU_CODCOR,
    T5.NOMCOM
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
full_reload(engine, df, schema_prata, tabela_destino, chunksize=10000, dtype_map=dtype_map)
print(f"  Tempo carga: {perf_counter() - inicio_carga:.1f}s")

print(f"  Tempo total {tabela_destino}: {perf_counter() - inicio_total:.1f}s")
