"""
Carga do fato de faturamento do BI Comercial -- camada Prata.

Origem  : DW_BRONZE.E120IPD, E120PED, E140IPV, E140ISV, E140IDE,
          E001TNS, E140NFV, E140PVD, E440IPC, E440NFC, E095FOR,
          E085CLI, E069GRE, E085HCL, E090REP
Destino : DW_PRATA.FAT_FATURAMENTO (era BIAQUARIO.USU_VBIAFATURAMENTO
          no legado)
Carga   : full_reload (DROP + recarga completa) -- MESMA estratégia do
          legado (comercial/extract/vbifaturamento.py), decisão
          confirmada com o usuário em 17/07/2026.

Classificação: FATO. Corte de data: DATA_CORTE_FATURAMENTO (config,
"01/01/2021") -- mesmo corte que o legado já tinha, não é mudança de
resultado.

----------------------------------------------------------------------
POR QUE full_reload (decisão confirmada, não é "provisório")
----------------------------------------------------------------------
Essa é a única das 7 tabelas do Comercial que mistura 2 naturezas
diferentes de dado debaixo de um único UNION ALL:
    - Bloco PED: pedido em aberto -- QTDABE muda conforme o pedido
      avança, ou seja, a MESMA linha muda de valor ao longo do tempo
      (precisa de UPDATE, não é append-only).
    - Blocos VENPRO/VENSER/DEV: transações já emitidas -- imutáveis
      uma vez criadas.
Além disso, a query não expõe uma chave 100% confiável pra MERGE (os
SEQIPD/SEQIPV/SEQISV/SEQIPC de origem foram descartados do SELECT no
legado -- adicionados de volta aqui, ver observação abaixo, mas isso
sozinho não resolve a mistura de naturezas). full_reload resolve as
duas coisas de uma vez (a parte mutável sempre reflete o estado atual,
e exclusão na origem também é resolvida de graça, sem lógica de órfão
própria). Redesenhar pra incremental exigiria separar PED do resto --
mudança de modelo que afeta o Power BI, fora de escopo desta migração.

----------------------------------------------------------------------
MELHORIAS APLICADAS (seguras, não mudam nenhum resultado)
----------------------------------------------------------------------
1. Colunas de sequência de origem (SEQIPD/SEQIPV/SEQISV/SEQIPC)
   adicionadas ao SELECT -- aditivo, cada bloco preenche a sua e NULL
   nas demais. Não estava no legado, não substitui nem remove nenhuma
   coluna existente -- só destrava um futuro redesenho incremental sem
   precisar reabrir esta query inteira de novo.
2. O hint manual do Oracle (`/*+ LEADING... USE_NL... USE_HASH... */`)
   que existia no bloco DEV foi removido -- ele foi calibrado pro plano
   de execução contra o Sapiens (tabelas muito maiores); contra a
   Bronze (só a fatia da Aquário, bem menor) pode não fazer sentido, ou
   até forçar um plano pior. Hint só afeta desempenho, nunca o
   resultado -- removível com segurança. Se a query ficar lenta contra
   a Bronze, vale medir o plano de execução real antes de adicionar um
   hint novo (não reaproveitar o antigo às cegas).

----------------------------------------------------------------------
MELHORIA CONSIDERADA E **NÃO** APLICADA (decisão consciente)
----------------------------------------------------------------------
O cálculo de rateio do FUNDPOB (bloco DEV) aparece duplicado no legado
-- calculado 2x, uma vez pra VLR_FUNDPOB e de novo dentro do cálculo de
VLR_SLI (mesma subquery correlacionada, escrita duas vezes). Cheguei a
tentar deduplicar isso (reestruturar em 2 camadas de SELECT, calculando
uma vez só) -- mas a reestruturação de um bloco com JOINs profundos
numa query financeira, sem conseguir testar contra um Oracle real antes
de entregar, tem mais risco real do que o ganho de performance justifica
aqui. Mantido EXATAMENTE como no legado (duplicado) nesta versão --
fica registrado como candidato a uma otimização futura, feita com tempo
pra testar direito, não forçada agora.
"""

# ----- IMPORTS -----

from time import perf_counter

import pandas as pd
from sqlalchemy import text

from comercial.config.settings import DATA_CORTE_FATURAMENTO, schema_bronze, schema_prata
from core.db import get_engine_prata
from core.dtype_map import build_dtype_map
from core.loader import full_reload

# ----- CONFIGURAÇÃO DA TABELA DESTINO -----

tabela_destino = "FAT_FATURAMENTO"

# ----- QUERY DE EXTRAÇÃO (lendo da Bronze) -----

query = f"""
SELECT

	TRUNC(P.DATPRV) AS DATAREF,
	'PED' AS TIPOREG,
	0 AS VENDA,
	IPED.CODFIL AS CODFILIAL,
	P.USU_CLIBAS AS CODCLIBASE,
	P.CODCLI AS CODCLI,
	IPED.NUMPED AS NUMPED,
	0 AS NUMNFV,
	0 AS NUMNFD,
	CASE
		WHEN IPED.CODDER = ' ' THEN IPED.CODPRO ||'-'
		ELSE IPED.CODPRO ||'-'||IPED.CODDER
	END AS CHAVE_ITEM,
	IPED.CODDEP AS CODDEP,
	P.CODTRA AS CODTRANSP,
	P.CODCPG AS CODCPG,
	P.CODFPG AS CODFPG,

	IPED.QTDABE AS QTDITEM,
	IPED.PREUNI AS PRECOUNIT,
	IPED.VLRLIQ AS VLR_LIQ,
	IPED.PEROFE AS PERC_OFF,
	IPED.VLROFE AS VLR_OFF,
	IPED.VLRIPI AS VLR_IPI,
	IPED.VLRICM AS VLR_ICMS,
	IPED.VLRICS AS VLR_ST,
	IPED.VSTFCP AS VLR_FUNDPOB,
	IPED.VLROUT AS VLR_OUT,
	IPED.VLRLIQ - (IPED.VLRIPI + IPED.VLRICS + IPED.VSTFCP + IPED.VLROUT) AS VLR_SLI,
	(IPED.QTDABE * IPED.PREUNI) AS VLRBRUTO_TOTAL,
	(IPED.QTDABE * IPED.VLROFE) AS VLRDESC_TOTAL,
	0 AS MOTIVODEV,

	IPED.CODREP AS CODREP,
	P.USU_CODRVRREP AS CODREGREP,
	P.USU_CODRVRCLI AS CODREGCLI,

	IPED.SEQIPD AS SEQIPD,
	NULL AS SEQIPV,
	NULL AS SEQISV,
	NULL AS SEQIPC

FROM {schema_bronze}.E120IPD IPED
LEFT JOIN {schema_bronze}.E120PED P
    ON IPED.CODEMP = P.CODEMP
    AND IPED.CODFIL = P.CODFIL
    AND IPED.NUMPED = P.NUMPED

WHERE IPED.CODEMP = 1
	AND P.SITPED IN (1, 2)
	AND IPED.TNSPRO IN ('90100', '90101', '90120', '90170')
	AND P.DATPRV >= TO_DATE('{DATA_CORTE_FATURAMENTO}', 'DD/MM/YYYY')

UNION ALL

SELECT

	TRUNC(I.DATGER) AS DATAREF,
	'VENPRO' AS TIPOREG,
	1 AS VENDA,
	I.CODFIL AS CODFILIAL,
	N.USU_CLIBAS AS CODCLIBASE,
	N.CODCLI AS CODCLI,
	I.NUMPED AS NUMPED,
	I.NUMNFV AS NUMNFV,
	0 AS NUMNFD,
	CASE
		WHEN I.CODDER = ' ' THEN I.CODPRO
		ELSE I.CODPRO ||'-'||I.CODDER
	END AS CHAVE_ITEM,
	I.CODDEP AS CODDEP,
	N.CODTRA AS CODTRANSP,
	N.CODCPG AS CODCPG,
	N.CODFPG AS CODFPG,

	I.QTDFAT AS QTDITEM,
   	I.PREUNI AS PRECOUNIT,
	I.VLRLIQ AS VLR_LIQ,
	I.PEROFE AS PERC_OFF,
	I.VLROFE AS VLR_OFF,
	I.VLRIPI AS VLR_IPI,
	I.VLRICM AS VLR_ICMS,
	I.VLRICS AS VLR_ST,
	P.VSTFCP AS VLR_FUNDPOB,
	I.VLROUT AS VLR_OUT,
	I.VLRLIQ - (I.VLRIPI + I.VLRICS + P.VSTFCP + I.VLROUT) AS VLR_SLI,
	(I.QTDFAT * I.PREUNI) AS VLRBRUTO_TOTAL,
	(I.QTDFAT * I.VLROFE) AS VLRDESC_TOTAL,
	0 AS MOTIVODEV,

	N.CODREP AS CODREP,
	N.USU_CODRVRREP AS CODREGREP,
	N.USU_CODRVRCLI AS CODREGCLI,

	NULL AS SEQIPD,
	I.SEQIPV AS SEQIPV,
	NULL AS SEQISV,
	NULL AS SEQIPC

FROM {schema_bronze}.E140IPV I
LEFT JOIN {schema_bronze}.E140IDE IDE
    ON I.CODEMP = IDE.CODEMP
    AND I.CODFIL = IDE.CODFIL
    AND I.NUMNFV = IDE.NUMNFV
LEFT JOIN {schema_bronze}.E001TNS T
    ON I.CODEMP = T.CODEMP
    AND I.TNSPRO = T.CODTNS
LEFT JOIN {schema_bronze}.E140NFV N
    ON I.CODEMP = N.CODEMP
    AND I.CODFIL = N.CODFIL
    AND I.NUMNFV = N.NUMNFV
LEFT JOIN {schema_bronze}.E140PVD P
    ON I.CODEMP = P.CODEMP
    AND I.CODFIL = P.CODFIL
    AND I.NUMNFV = P.NUMNFV
	AND I.SEQIPV = P.SEQIPV

WHERE I.CODEMP = 1
	AND N.TIPNFS IN (1, 9)
	AND N.SITNFV = 2
	AND T.VENFAT = 'S'
	AND IDE.SITDOE = 3
	AND I.DATGER >= TO_DATE('{DATA_CORTE_FATURAMENTO}', 'DD/MM/YYYY')

UNION ALL

SELECT

	TRUNC(I.DATGER) AS DATAREF,
	'VENSER' AS TIPOREG,
	1 AS VENDA,
	I.CODFIL AS CODFILIAL,
	N.USU_CLIBAS AS CODCLIBASE,
	N.CODCLI AS CODCLI,
	I.NUMPED AS NUMPED,
	I.NUMNFV AS NUMNFV,
	0 AS NUMNFD,
	I.CODSER AS CHAVE_ITEM,
	'' AS CODDEP,
	N.CODTRA AS CODTRANSP,
	N.CODCPG AS CODCPG,
	N.CODFPG AS CODFPG,

	I.QTDFAT AS QTDITEM,
	I.PREUNI AS PRECOUNIT,
	I.VLRLIQ AS VLR_LIQ,
	0 AS PERC_OFF,
	0 AS VLR_OFF,
	NVL(I.VLRIPI, 0) AS VLR_IPI,
	NVL(I.VLRICM, 0) AS VLR_ICMS,
	NVL(I.VLRICS, 0) AS VLR_ST,
	NVL(P.VSTFCP, 0) AS VLR_FUNDPOB,
	I.VLROUT AS VLR_OUT,
	I.VLRLIQ - (NVL(I.VLRIPI, 0) + NVL(I.VLRICS, 0) + NVL(P.VSTFCP, 0) + NVL(I.VLROUT, 0)) AS VLR_SLI,
	(I.QTDFAT * I.PREUNI) AS VLRBRUTO_TOTAL,
	(I.QTDFAT * 0) AS VLRDESC_TOTAL,
	0 AS MOTIVODEV,

	N.CODREP AS CODREP,
	N.USU_CODRVRREP AS CODREGREP,
	N.USU_CODRVRCLI AS CODREGCLI,

	NULL AS SEQIPD,
	NULL AS SEQIPV,
	I.SEQISV AS SEQISV,
	NULL AS SEQIPC

FROM {schema_bronze}.E140ISV I
LEFT JOIN {schema_bronze}.E140IDE IDE
    ON I.CODEMP = IDE.CODEMP
    AND I.CODFIL = IDE.CODFIL
    AND I.CODSNF = IDE.CODSNF
    AND I.NUMNFV = IDE.NUMNFV
LEFT JOIN {schema_bronze}.E001TNS T
    ON I.CODEMP = T.CODEMP
    AND I.TNSSER = T.CODTNS
LEFT JOIN {schema_bronze}.E140NFV N
    ON I.CODEMP = N.CODEMP
    AND I.CODFIL = N.CODFIL
    AND I.CODSNF = N.CODSNF
    AND I.NUMNFV = N.NUMNFV
LEFT JOIN {schema_bronze}.E140PVD P
    ON I.CODEMP = P.CODEMP
    AND I.CODFIL = P.CODFIL
    AND I.NUMNFV = P.NUMNFV
	AND I.SEQIPV = P.SEQIPV

WHERE I.CODEMP = 1
	AND N.TIPNFS IN (1, 9)
	AND N.SITNFV = 2
	AND T.VENFAT = 'S'
	AND IDE.SITDOE = 3
	AND I.DATGER >= TO_DATE('{DATA_CORTE_FATURAMENTO}', 'DD/MM/YYYY')

UNION ALL

SELECT

    TRUNC(N.DATENT) AS DATAREF,
	'DEV' AS TIPOREG,
	0 AS VENDA,
    I.CODFIL AS CODFILIAL,
    NVL(NF.USU_CLIBAS,COALESCE(G.CLIBAS, C.CODCLI)) AS CODCLIBASE,
    NVL(NF.CODCLI, F.CODCLI) AS CODCLI,
    I.NUMPED AS NUMPED,
    I.NUMNFV AS NUMNFV,
    I.NUMNFC AS NUMNFD,
	CASE
		WHEN I.CODDER = ' ' THEN I.CODPRO ||'-'|| I.CODFIL
		ELSE I.CODPRO ||'-'||I.CODDER||I.CODFIL
	END AS CHAVE_ITEM,
    I.CODDEP AS CODDEP,
	N.CODTRA AS CODTRANSP,
	N.CODCPG AS CODCPG,
	N.CODFPG AS CODFPG,

    I.QTDREC * -1 AS QTDITEM,
    I.PREUNI * -1 AS PRECOUNIT,
    I.VLRLIQ * -1 AS VLR_LIQ,
    0 AS PERC_OFF,
    0 AS VLR_OFF,
    I.VECIPI * -1 AS VLR_IPI,
    I.VLRICM * -1 AS VLR_ICMS,
    I.VLRICS * -1 AS VLR_ST,
    CASE
        WHEN NVL(I.ICMVFC, 0) = 0 THEN

            (N.VSTFCP / NULLIF((
                SELECT COUNT(*)
                FROM {schema_bronze}.E440IPC X
                WHERE X.CODEMP = I.CODEMP
                  AND X.CODFIL = I.CODFIL
                  AND X.CODFOR = I.CODFOR
                  AND X.CODSNF = I.CODSNF
                  AND X.NUMNFC = I.NUMNFC
            ), 0)) * -1
        ELSE
            I.ICMVFC * -1
    END AS VLR_FUNDPOB,
    I.VLROUT * -1 AS VLR_OUT,
    (I.VLRLIQ - (I.VECIPI + I.VLRICS +
        CASE
            WHEN NVL(I.ICMVFC, 0) = 0 THEN
                (N.VSTFCP / NULLIF((
                    SELECT COUNT(*)
                    FROM {schema_bronze}.E440IPC X
                    WHERE X.CODEMP = I.CODEMP
                      AND X.CODFIL = I.CODFIL
                      AND X.CODFOR = I.CODFOR
                      AND X.CODSNF = I.CODSNF
                      AND X.NUMNFC = I.NUMNFC
                ), 0))
            ELSE
                I.ICMVFC
        END
      + I.VLROUT)) * -1 AS VLR_SLI,
    (I.QTDREC * I.PREUNI) * -1 AS VLRBRUTO_TOTAL,
    (I.QTDREC * 0) * -1 AS VLRDESC_TOTAL,
    N.USU_MOTDEV AS MOTIVODEV,

	H.CODREP AS CODREP,
	R.USU_CODRVR AS CODREGREP,
	NVL(NF.USU_CODRVRCLI, C.USU_CODRVR) AS CODREGCLI,

	NULL AS SEQIPD,
	NULL AS SEQIPV,
	NULL AS SEQISV,
	I.SEQIPC AS SEQIPC

FROM {schema_bronze}.E440IPC I
LEFT JOIN {schema_bronze}.E440NFC N
    ON I.CODEMP = N.CODEMP
    AND I.CODFIL = N.CODFIL
    AND I.SNFNFV = N.CODSNF
    AND I.NUMNFC = N.NUMNFC
    AND I.CODFOR = N.CODFOR
LEFT JOIN {schema_bronze}.E140NFV NF
    ON I.CODEMP = NF.CODEMP
    AND I.CODFIL = NF.CODFIL
    AND I.SNFNFV = NF.CODSNF
    AND I.NUMNFV = NF.NUMNFV
LEFT JOIN {schema_bronze}.E001TNS T
    ON I.CODEMP = T.CODEMP
    AND I.TNSPRO = T.CODTNS
LEFT JOIN {schema_bronze}.E095FOR F
	ON I.CODFOR = F.CODFOR
LEFT JOIN {schema_bronze}.E085CLI C
	ON F.CODCLI = C.CODCLI
LEFT JOIN {schema_bronze}.E085HCL H
	ON I.CODEMP = H.CODEMP
    AND I.CODFIL = H.CODFIL
    AND F.CODCLI = H.CODCLI
LEFT JOIN {schema_bronze}.E069GRE G
	ON C.CODGRE = G.CODGRE
LEFT JOIN {schema_bronze}.E090REP R
	ON H.CODREP = R.CODREP

WHERE N.CODEMP = 1
    AND N.SITNFC = '2'
    AND T.CPRTCF IN ('D', 'A')
    AND ((T.COMNAT IN ('1201','2201',
                        '1202','2202',
                        '1203','2203',
                        '1503','2503',
                        '1410','2410',
                        '1411','2411') AND N.TIPNFE IN (2, 3)) OR
         (T.COMNAT IN ('1603', '2603') AND N.TIPNFE IN (9, 10)))
    AND N.DATENT >= TO_DATE('{DATA_CORTE_FATURAMENTO}', 'DD/MM/YYYY')

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
full_reload(engine, df, schema_prata, tabela_destino, chunksize=10000)
print(f"  Tempo carga: {perf_counter() - inicio_carga:.1f}s")

print(f"  Tempo total {tabela_destino}: {perf_counter() - inicio_total:.1f}s")
