"""
Carga do fato central do BI Produção -- camada Prata.

Origem  : DW_BRONZE.E900EOQ, E900COP, E900OOP, E900QDO, E210MVP, E075PRO
          (compartilhada com o Comercial), E626ORC, E047NTG, E621MTC,
          E930MPR, E093ETG, E725CRE, E044CCU, E630SPE, E626TAX
Destino : DW_PRATA.FAT_DESEMPENHO_PRODUCAO (era
          BIAQUARIO.USU_VBIAPROD_DESEMPENHO no legado)
Carga   : full_reload (DROP + recarga completa) -- mesma estratégia do
          legado (producao/extract/vbidesempenho.py).

Classificação: FATO CENTRAL da área. Consolida 4 tipos de registro
identificados pela coluna TIPTAB, via UNION ALL (mesmo padrão do
FAT_FATURAMENTO no Comercial -- naturezas diferentes de dado
denormalizadas numa única tabela, com NULL nas colunas que não se
aplicam a cada bloco):

    TIPTAB 1 | DESTAB='DESEMPENHO' : Apontamentos de processo por OP/estágio/data
    TIPTAB 2 | DESTAB='CONSUMO'    : Consumo de matéria-prima por OP
    TIPTAB 3 | DESTAB='PARADAS'    : Horas de parada por centro de custo e data
    TIPTAB 4 | DESTAB='CUSTO_CC'   : Valores orçado/realizado por centro de custo

CORTE DE DATA: 01/01/2021 (DATA_CORTE_PRODUCAO, config) nos blocos 1/2/3
-- o legado cortava em 01/01/2018 (DATA_INICIO_HISTORICO); decisão
explícita do usuário em 21/07/2026 de usar 2021 como padrão único pra
toda a área. Bloco 4 (CUSTO_CC) ganhou um corte NOVO (T2.DATINI >=
2021) que não existia no legado -- mesma decisão aplicada em
fat_custo_cc_producao.py (ver docstring de lá pro detalhe completo).

----------------------------------------------------------------------
MOTIVO DE full_reload
----------------------------------------------------------------------
UNION ALL de 4 naturezas de dado diferentes, sem chave única que sirva
pra todos os blocos ao mesmo tempo -- mesmo motivo do FAT_FATURAMENTO no
Comercial. Redesenhar pra incremental exigiria separar os 4 blocos em
tabelas próprias (mudança de modelo, fora de escopo desta migração).

Nota: o docstring do legado (`vbidesempenho.py`) justificava full_reload
citando "Ds_Prazo... laudos em aberto mudam a qualquer ciclo" -- essa
frase é terminologia do Laudos RMA (parece um comentário copiado do
template errado durante o desenvolvimento original), não se aplica à
Produção. Não é bug funcional (só o comentário) -- corrigido aqui com a
justificativa real.

----------------------------------------------------------------------
COLUNAS REINCORPORADAS NO LEGADO (Junho/2026) -- mantidas
----------------------------------------------------------------------
O legado já tinha uma correção de campos que existiam no Qlik Sense mas
não tinham sido trazidos originalmente pra query SQL (CODFAM/
CD_TIPO_MP_PERSONALIZADO no bloco CONSUMO; SITORP/DTRINI/DTRFIM no bloco
DESEMPENHO). Mantidos exatamente como estavam -- ver comentários inline.

TMPLIQ permanece NULL -- EW909MVO não existe neste ambiente
Sapiens/Senior (mesma nota do legado; tabela nem chegou a entrar no
catálogo da Bronze, ver producao/bronze/tabelas.py).

----------------------------------------------------------------------
BUG CORRIGIDO (23/07/2026): corte de negócio vazou pra dentro de uma
busca técnica no bloco CONSUMO
----------------------------------------------------------------------
O bloco TIPTAB=2 (CONSUMO) calcula DATREA com um fallback: se não achar
apontamento (E900EOQ) na data EXATA do movimento, procura "o apontamento
mais próximo dessa OP" numa segunda subconsulta, sem exigir data exata.
Essas 2 subconsultas tinham um filtro de janela PRÓPRIO, historicamente
igual ao corte geral (2018 no legado, porque lá os dois eram o mesmo
valor por coincidência) -- ao trocar o corte geral pra 2021
(DATA_CORTE_PRODUCAO), esse filtro interno foi trocado junto, sem querer.

Consequência: registros de CONSUMO logo após 01/01/2021 (ex.: 05/01/2021)
que só tinham apontamento de referência em dezembro/2020 passaram a
achar NULL na Prata (a busca não enxergava nada antes de 2021), enquanto
o legado (que usa DATA_INICIO_HISTORICO=2018 nesse mesmo ponto) achava o
valor certo -- 4 divergências confirmadas na conferência, todas com essa
assinatura (DATREA nulo na Prata, preenchido no legado, mesma
CODORI+NUMORP+CODETG).

Corrigido separando as duas janelas: DATA_CORTE_PRODUCAO (2021) continua
decidindo quais REGISTROS entram no histórico (WHERE externo dos 4
blocos); DATA_MINIMA_APONTAMENTO_CONSUMO (2018, nova constante em
config/settings.py) passou a ser usada só nessas 2 subconsultas -- mesmo
valor que o legado sempre usou aí, preservando o alcance original da
busca técnica. Ver settings.py pro detalhe completo.

LIÇÃO GERAL: ao trocar um valor de corte de data que aparece em vários
lugares da mesma query, conferir se TODOS os usos são realmente a mesma
decisão de negócio -- um valor pode aparecer repetido só porque, no
legado, coincidia por acaso (mesmo corte geral usado em 2 propósitos
diferentes), não porque são a mesma coisa.
"""

# ----- IMPORTS -----

from time import perf_counter

import pandas as pd
from sqlalchemy import text

from core.db import get_engine_prata
from core.dtype_map import build_dtype_map
from core.loader import full_reload
from producao.config.settings import (
    DATA_CORTE_PRODUCAO,
    DATA_MINIMA_APONTAMENTO_CONSUMO,
    schema_bronze,
    schema_prata,
)

# ----- CONFIGURAÇÃO DA TABELA DESTINO -----

tabela_destino = "FAT_DESEMPENHO_PRODUCAO"

# ----- QUERY DE EXTRAÇÃO (lendo da Bronze) -----

query = f"""
SELECT
    1                                                                   AS TIPTAB,
    'DESEMPENHO'                                                        AS DESTAB,
    Z1.CODEMP,
    NULL                                                                AS DATMOV,
    Z1.DATREA,
    Z1.NUMORP,
    CASE WHEN X2.CODCCU = ' ' THEN X1.CODCCU ELSE X2.CODCCU END        AS CC_EXE,
    T2.CODOPR,
    Z1.CODETG,
    Z1.CODCRE,
    Z1.CODORI,
    Z1.CODPRO,
    NULL                                                                AS PROCON,
    NULL                                                                AS TIPCON,
    NULL                                                                AS NUMMTC,
    NULL                                                                AS CODNTG,
    SUM(T3.QTDPRV)                                                      AS QTDPRV,
    AVG((SELECT SUM(Z0.QTDRE1)
           FROM {schema_bronze}.E900EOQ Z0
          WHERE Z0.CODEMP  = Z1.CODEMP
            AND Z0.CODORI  = Z1.CODORI
            AND Z0.NUMORP  = Z1.NUMORP
            AND Z0.CODETG  = Z1.CODETG
            AND Z0.SEQROT  = Z1.SEQROT
            AND Z0.DATREA  = Z1.DATREA))                                AS QTDREA,
    NULL                                                                AS QTDTOP,
    NULL                                                                AS QTDCOR,
    AVG(CASE WHEN TO_CHAR(T0.DTRFIM,'MM') = TO_CHAR(Z1.DATREA,'MM')
             THEN 0
             ELSE (SELECT SUM(Z2.SDOATU)
                     FROM {schema_bronze}.E630SPE Z2
                    WHERE Z2.CODEMP = T0.CODEMP
                      AND Z2.CODORI = T0.CODORI
                      AND Z2.NUMORP = T0.NUMORP
                      AND Z2.CODPRO = T0.CODPRO
                      AND Z2.CODETG IN ('99','50'))
        END)                                                            AS QTDAND,
    SUM(T3.QTDRFG)                                                      AS QTDRFG,
    CASE WHEN T2.UNICRE = 'M' THEN SUM(T2.TMPPRP)
         WHEN T2.UNICRE = 'D' THEN SUM(T2.TMPPRP) * 1440
         WHEN T2.UNICRE = 'H' THEN SUM(T2.TMPPRP) * 60
         WHEN T2.UNICRE = 'S' THEN SUM(T2.TMPPRP) / 60
         ELSE SUM(T2.TMPPRP)
    END                                                                 AS TMPPRP,
    CASE WHEN T2.UNICRE = 'M' THEN SUM(T2.TMPPRP) * SUM(T3.QTDPRV)
         WHEN T2.UNICRE = 'D' THEN SUM(T2.TMPPRP) * 1440 * SUM(T3.QTDPRV)
         WHEN T2.UNICRE = 'H' THEN SUM(T2.TMPPRP) * 60   * SUM(T3.QTDPRV)
         WHEN T2.UNICRE = 'S' THEN SUM(T2.TMPPRP) / 60   * SUM(T3.QTDPRV)
         ELSE SUM(T2.TMPPRP) * SUM(T3.QTDPRV)
    END                                                                 AS TMPPRV,
    AVG((SELECT SUM(Z0.TMPBRU)
           FROM {schema_bronze}.E900EOQ Z0
          WHERE Z0.CODEMP = Z1.CODEMP
            AND Z0.CODORI = Z1.CODORI
            AND Z0.NUMORP = Z1.NUMORP
            AND Z0.CODETG = Z1.CODETG
            AND Z0.SEQROT = Z1.SEQROT
            AND Z0.CODOPR = Z1.CODOPR
            AND Z0.DATREA = Z1.DATREA))                                 AS TMPBRU,
    -- TMPLIQ: tabela EW909MVO não existe neste ambiente Sapiens/Senior
    -- (mesma nota do legado -- ver producao/bronze/tabelas.py).
    NULL                                                                AS TMPLIQ,
    AVG((SELECT NVL(SUM(Y1.TAXCUS), 0)
           FROM {schema_bronze}.E621MTC Y0
           JOIN {schema_bronze}.E626TAX Y1
             ON Y0.CODEMP  = Y1.CODEMP
            AND Y0.NUMMTC  = Y1.NUMMTC
          WHERE Y0.CODEMP  = T2.CODEMP
            AND Y1.CODCCU  = (CASE WHEN X2.CODCCU = ' ' THEN X1.CODCCU ELSE X2.CODCCU END)
            AND Y0.DATINI <= Z1.DATREA
            AND Y0.DATFIM >= Z1.DATREA
            AND Y0.TIPMTC  = 28))                                       AS TAXREA,
    NULL                                                                AS CUSMOV,
    NULL                                                                AS QTDHOR,
    NULL                                                                AS HORINI,
    NULL                                                                AS VALVIS,
    'Processo'                                                          AS TIPCUS,
    -- ----- CAMPOS REINCORPORADOS (DADOS_OP do Qlik, já no legado) -----
    MAX(T0.SITORP)                                                      AS SITORP,
    MAX(T0.DTRINI)                                                      AS DTRINI,
    MAX(T0.DTRFIM)                                                      AS DTRFIM,
    NULL                                                                AS CODFAM,
    NULL                                                                AS CD_TIPO_MP_PERSONALIZADO

FROM {schema_bronze}.E900EOQ Z1

LEFT JOIN {schema_bronze}.E900COP T0
    ON  T0.CODEMP = Z1.CODEMP
    AND T0.CODORI = Z1.CODORI
    AND T0.NUMORP = Z1.NUMORP

LEFT JOIN {schema_bronze}.E900OOP T2
    ON  T2.CODEMP = Z1.CODEMP
    AND T2.CODORI = Z1.CODORI
    AND T2.NUMORP = Z1.NUMORP
    AND T2.CODETG = Z1.CODETG
    AND T2.SFXETR = '1'
    AND T2.SEQROT = Z1.SEQROT
    AND T2.SFXSEQ = '1'

LEFT JOIN {schema_bronze}.E093ETG X1
    ON  X1.CODEMP = Z1.CODEMP
    AND X1.CODETG = Z1.CODETG

LEFT JOIN {schema_bronze}.E725CRE X2
    ON  X2.CODEMP = Z1.CODEMP
    AND X2.CODCRE = Z1.CODCRE

LEFT JOIN {schema_bronze}.E900QDO T3
    ON  T3.CODEMP = Z1.CODEMP
    AND T3.CODORI = Z1.CODORI
    AND T3.NUMORP = Z1.NUMORP
    AND T3.CODPRO = Z1.CODPRO
    AND T3.CODDER = Z1.CODDER

WHERE Z1.DATREA   > TO_DATE('01/01/2001', 'DD/MM/YYYY')
  AND Z1.CODETG   NOT IN ('99', '50')
  AND T0.DTRINI  >= TO_DATE('{DATA_CORTE_PRODUCAO}', 'DD/MM/YYYY')

GROUP BY
    Z1.CODEMP, Z1.DATREA, Z1.NUMORP, Z1.CODETG, Z1.CODCRE,
    CASE WHEN X2.CODCCU = ' ' THEN X1.CODCCU ELSE X2.CODCCU END,
    T2.CODOPR, Z1.CODORI, Z1.CODPRO, T2.UNICRE

UNION ALL

-- TIPTAB 2 — Consumo de matéria-prima
SELECT
    2                                                                   AS TIPTAB,
    'CONSUMO'                                                           AS DESTAB,
    T0.CODEMP,
    T0.DATMOV,
    -- Fallback de busca do apontamento de referência -- janela TÉCNICA
    -- (DATA_MINIMA_APONTAMENTO_CONSUMO, 2018), NÃO a de negócio (2021).
    -- Ver settings.py, "BUG CORRIGIDO (23/07/2026)".
    MAX(NVL(
        (SELECT MAX(X0.DATREA)
           FROM {schema_bronze}.E900EOQ X0
          WHERE X0.CODEMP = T0.CODEMP
            AND X0.CODORI = T0.ORIORP
            AND X0.NUMORP = T0.NUMDOC
            AND X0.DATREA = T0.DATMOV
            AND X0.DATREA >= TO_DATE('{DATA_MINIMA_APONTAMENTO_CONSUMO}', 'DD/MM/YYYY')
            AND X0.CODETG NOT IN ('99', '50')
            AND X0.HORREA > 0),
        (SELECT MAX(X0.DATREA)
           FROM {schema_bronze}.E900EOQ X0
          WHERE X0.CODEMP = T0.CODEMP
            AND X0.CODORI = T0.ORIORP
            AND X0.NUMORP = T0.NUMDOC
            AND X0.DATREA >= TO_DATE('{DATA_MINIMA_APONTAMENTO_CONSUMO}', 'DD/MM/YYYY')
            AND X0.CODETG NOT IN ('99', '50')
            AND X0.HORREA > 0)
    ))                                                                  AS DATREA,
    T0.NUMDOC                                                           AS NUMORP,
    CASE WHEN X2.CODCCU = ' ' THEN X1.CODCCU ELSE X2.CODCCU END        AS CC_EXE,
    ' '                                                                 AS CODOPR,
    T0.CODETG,
    T3.CODCRE,
    T0.ORIORP                                                           AS CODORI,
    T2.CODPRO,
    T0.CODPRO                                                           AS PROCON,
    T1.TIPPRO                                                           AS TIPCON,
    NULL                                                                AS NUMMTC,
    NULL                                                                AS CODNTG,
    NULL                                                                AS QTDPRV,
    NULL                                                                AS QTDREA,
    AVG((SELECT SUM(Z0.QTDRE1)
           FROM {schema_bronze}.E900EOQ Z0
          WHERE Z0.CODEMP = T3.CODEMP
            AND Z0.CODORI = T3.CODORI
            AND Z0.NUMORP = T3.NUMORP
            AND Z0.CODETG = T3.CODETG
            AND Z0.SEQROT = T3.SEQROT
            AND TO_CHAR(Z0.DATREA, 'MM/YYYY') = TO_CHAR(T0.DATMOV, 'MM/YYYY')
            AND Z0.HORREA > 0
            AND Z0.CODETG NOT IN ('99', '50')))                         AS QTDTOP,
    SUM(T0.QTDMOV)                                                      AS QTDCOR,
    NULL                                                                AS QTDAND,
    NULL                                                                AS QTDRFG,
    NULL                                                                AS TMPPRP,
    NULL                                                                AS TMPPRV,
    NULL                                                                AS TMPBRU,
    NULL                                                                AS TMPLIQ,
    NULL                                                                AS TAXREA,
    SUM(CASE WHEN T0.ESTEOS = 'S' THEN T0.VLRMOV ELSE T0.VLRMOV * -1 END) AS CUSMOV,
    NULL                                                                AS QTDHOR,
    NULL                                                                AS HORINI,
    NULL                                                                AS VALVIS,
    'Consumo'                                                           AS TIPCUS,
    -- ----- CAMPOS REINCORPORADOS (CONSUMOMP do Qlik, já no legado) -----
    NULL                                                                AS SITORP,
    NULL                                                                AS DTRINI,
    NULL                                                                AS DTRFIM,
    T1.CODFAM,
    CASE WHEN T1.TIPPRO = 'P' THEN 'CO' ELSE 'MP' END                   AS CD_TIPO_MP_PERSONALIZADO

FROM {schema_bronze}.E210MVP T0

LEFT JOIN {schema_bronze}.E075PRO T1
    ON  T1.CODEMP = T0.CODEMP
    AND T1.CODPRO = T0.CODPRO

LEFT JOIN {schema_bronze}.E900COP T2
    ON  T2.CODEMP = T0.CODEMP
    AND T2.NUMORP = T0.NUMDOC
    AND T2.CODORI = T0.ORIORP

LEFT JOIN (
    SELECT K0.CODEMP, K0.CODORI, K0.NUMORP, K0.CODETG,
           K0.DATREA, K0.CODCRE, K0.SEQROT, SUM(K0.QTDRE1) AS QTDRE1
      FROM {schema_bronze}.E900EOQ K0
     WHERE K0.HORREA > 0
       AND K0.CODETG NOT IN ('99', '50')
     GROUP BY K0.CODEMP, K0.CODORI, K0.NUMORP, K0.CODETG,
              K0.DATREA, K0.CODCRE, K0.SEQROT
) T3
    ON  T3.CODEMP = T0.CODEMP
    AND T3.CODORI = T0.ORIORP
    AND T3.NUMORP = T0.NUMDOC
    AND T3.CODETG = T0.CODETG
    AND T3.DATREA = T0.DATMOV

LEFT JOIN {schema_bronze}.E093ETG X1
    ON  X1.CODEMP = T0.CODEMP
    AND X1.CODETG = T0.CODETG

LEFT JOIN {schema_bronze}.E725CRE X2
    ON  X2.CODEMP = T0.CODEMP
    AND X2.CODCRE = T3.CODCRE

WHERE T0.DATMOV  >= TO_DATE('{DATA_CORTE_PRODUCAO}', 'DD/MM/YYYY')
  AND T0.CODTNS   IN ('90251', '90202')
  AND T0.CODETG   NOT IN ('99', '50')

GROUP BY
    T0.CODEMP, T0.NUMDOC, T0.DATMOV,
    CASE WHEN X2.CODCCU = ' ' THEN X1.CODCCU ELSE X2.CODCCU END,
    T0.CODETG, T3.CODCRE, T0.ORIORP, T2.CODPRO, T0.CODPRO, T1.TIPPRO,
    T1.CODFAM

UNION ALL

-- TIPTAB 3 — Paradas
SELECT
    3                                                                   AS TIPTAB,
    'PARADAS'                                                           AS DESTAB,
    T0.CODEMP,
    NULL                                                                AS DATMOV,
    T0.DATMPR                                                           AS DATREA,
    NULL                                                                AS NUMORP,
    T2.CODCCU                                                           AS CC_EXE,
    ' '                                                                 AS CODOPR,
    T0.CODETG,
    T0.CODCRE,
    ' '                                                                 AS CODORI,
    ' '                                                                 AS CODPRO,
    NULL                                                                AS PROCON,
    NULL                                                                AS TIPCON,
    NULL                                                                AS NUMMTC,
    NULL                                                                AS CODNTG,
    NULL                                                                AS QTDPRV,
    NULL                                                                AS QTDREA,
    NULL                                                                AS QTDTOP,
    NULL                                                                AS QTDCOR,
    NULL                                                                AS QTDAND,
    NULL                                                                AS QTDRFG,
    NULL                                                                AS TMPPRP,
    NULL                                                                AS TMPPRV,
    NULL                                                                AS TMPBRU,
    NULL                                                                AS TMPLIQ,
    NULL                                                                AS TAXREA,
    NULL                                                                AS CUSMOV,
    T0.QTDHOR,
    T0.HORINI,
    NULL                                                                AS VALVIS,
    NULL                                                                AS TIPCUS,
    -- ----- CAMPOS REINCORPORADOS — não se aplicam a este bloco -----
    NULL                                                                AS SITORP,
    NULL                                                                AS DTRINI,
    NULL                                                                AS DTRFIM,
    NULL                                                                AS CODFAM,
    NULL                                                                AS CD_TIPO_MP_PERSONALIZADO

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

UNION ALL

-- TIPTAB 4 — Custo CC (Orçado x Realizado)
SELECT
    4                                                                   AS TIPTAB,
    'CUSTO_CC'                                                          AS DESTAB,
    T0.CODEMP,
    NULL                                                                AS DATMOV,
    T2.DATINI                                                           AS DATREA,
    NULL                                                                AS NUMORP,
    T0.CODCCU                                                           AS CC_EXE,
    ' '                                                                 AS CODOPR,
    NULL                                                                AS CODETG,
    ' '                                                                 AS CODCRE,
    ' '                                                                 AS CODORI,
    ' '                                                                 AS CODPRO,
    NULL                                                                AS PROCON,
    NULL                                                                AS TIPCON,
    T0.NUMMTC,
    T0.CODNTG,
    NULL                                                                AS QTDPRV,
    NULL                                                                AS QTDREA,
    NULL                                                                AS QTDTOP,
    NULL                                                                AS QTDCOR,
    NULL                                                                AS QTDAND,
    NULL                                                                AS QTDRFG,
    NULL                                                                AS TMPPRP,
    NULL                                                                AS TMPPRV,
    NULL                                                                AS TMPBRU,
    NULL                                                                AS TMPLIQ,
    NULL                                                                AS TAXREA,
    NULL                                                                AS CUSMOV,
    NULL                                                                AS QTDHOR,
    NULL                                                                AS HORINI,
    T0.VALVIS,
    NULL                                                                AS TIPCUS,
    -- ----- CAMPOS REINCORPORADOS — não se aplicam a este bloco -----
    NULL                                                                AS SITORP,
    NULL                                                                AS DTRINI,
    NULL                                                                AS DTRFIM,
    NULL                                                                AS CODFAM,
    NULL                                                                AS CD_TIPO_MP_PERSONALIZADO

FROM {schema_bronze}.E626ORC T0

LEFT JOIN {schema_bronze}.E047NTG T1
    ON  T1.CODEMP = T0.CODEMP
    AND T1.CODNTG = T0.CODNTG

LEFT JOIN {schema_bronze}.E621MTC T2
    ON  T2.CODEMP = T0.CODEMP
    AND T2.NUMMTC = T0.NUMMTC

WHERE T0.CODCCU > '4000'
  AND T0.CODCCU < '4300'
  AND T0.NUMMTC > '1600'
  AND T2.DATINI >= TO_DATE('{DATA_CORTE_PRODUCAO}', 'DD/MM/YYYY')

ORDER BY 1 ASC, 4 DESC
"""

# ----- EXTRAÇÃO -----

inicio_total = perf_counter()

engine = get_engine_prata()

print(f"  Corte de data: {DATA_CORTE_PRODUCAO}")

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
