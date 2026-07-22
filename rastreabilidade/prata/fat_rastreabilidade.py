"""
Carga do fato de rastreabilidade (bipagem de código de barras/QR) do BI
Rastreabilidade -- camada Prata.

Origem  : DW_BRONZE.E140IPV, E140NFV, E085CLI, E090REP, E026RAM, E075PRO,
          E120IPD, USU_T140QRC (exclusiva desta área) + USU_VZRASLAU
          (compartilhada com o Laudos RMA) -- todas já cobertas pelo
          catálogo da Bronze, nenhuma extraída aqui.
          Externo: Z:\\Dados\\MetaMix.xlsx (aba Cadastro) -- fora da
          Bronze por decisão de 07/07/2026 (mesma exceção do Laudos RMA),
          lido direto pela Prata igual o legado.
Destino : DW_PRATA.FAT_RASTREABILIDADE (era
          BIAQUARIO.USU_VBIARAST_RASTREABILIDADE no legado)
Carga   : full_reload (DROP + recarga completa) -- MESMA estratégia do
          legado (aquario/rastreabilidade/extract/vbirastreabilidade.py).

Classificação: FATO (grão = 1 código de barras/QR gerado por item de nota
fiscal -- QTDFAT como medida, USU_T140QRC é a âncora real do grão).
Única tabela desta área, igual o OPEX -- sem dimensão separada, o legado
sempre denormalizou tudo num resultado só.

CORTE DE DATA: mantido em 01/01/2023 (DATA_CORTE_RASTREABILIDADE, config)
-- mesmo corte que o legado já tinha, aplicado tanto em NFV.DATEMI quanto
em QRC.USU_DATGER. Regra 2 da Fase 2: só trocamos pelo padrão de 2021
quando o legado não tinha corte nenhum; aqui já tinha, então mantido.

----------------------------------------------------------------------
MELHORIA APLICADA: JOIN modernizado para sintaxe ANSI
----------------------------------------------------------------------
O legado escreve o JOIN no estilo antigo do Oracle (tabelas separadas por
vírgula no FROM + condições de igualdade no WHERE, com o operador (+)
emulando o LEFT JOIN de USU_VZRASLAU). Reescrito aqui como INNER JOIN /
LEFT JOIN explícitos -- tradução mecânica, mesmo plano de execução
(otimizador do Oracle trata as duas formas de forma idêntica), mesmo
resultado. Ganho é só legibilidade/manutenção, não performance -- mesmo
tipo de limpeza segura já aplicada no FAT_FATURAMENTO (remoção do hint).

----------------------------------------------------------------------
DECISÃO: manter full_reload, sem redesenho incremental (21/07/2026)
----------------------------------------------------------------------
USU_T140QRC (a tabela-âncora do grão) é insert-only ("log de geração",
nunca é alterada -- ver rastreabilidade/bronze/tabelas.py) e tem PK real
estável, o que a tornaria candidata a upsert incremental (mesmo padrão já
usado em FAT_VENDAS_RMA/FAT_LAUDOS). Cheguei a desenhar essa alternativa,
mas ela exigiria resincronizar separadamente TODAS as colunas
descritivas embutidas na linha (produto, cliente, representante, região,
MIX/ORIGEM do Excel) a cada ciclo -- essas vêm de cadastros que podem
mudar depois que a linha já foi carregada (ex.: correção de cidade de um
cliente), e o legado sempre mostra o valor ATUAL desses cadastros pra
QUALQUER linha histórica, porque recalcula tudo do zero sempre. Um
upsert simples (só a parte transacional) quebraria essa garantia.
Resolver isso direito exigiria múltiplas passadas de resync (produto,
cliente, representante+região, MIX/ORIGEM), bem mais código e mais
superfície pra esconder um bug sutil -- decisão consciente de NÃO fazer
isso agora, sem antes medir se o full_reload simples (lendo da Bronze,
que é bem mais rápido que o Sapiens ao vivo) já resolve o problema de
performance sozinho. Mesmo caso do FAT_FATURAMENTO: a causa de lentidão
lá era só um índice faltando na Bronze, não a estratégia de carga.
Candidato a otimização futura, só se o full_reload realmente se mostrar
lento na prática.
"""

# ----- IMPORTS -----

from time import perf_counter

import pandas as pd
from sqlalchemy import text

from core.db import get_engine_prata
from core.dtype_map import build_dtype_map
from core.loader import full_reload
from rastreabilidade.config.settings import (
    DATA_CORTE_RASTREABILIDADE,
    EXCEL_METAMIX,
    schema_bronze,
    schema_prata,
)

# ----- CONFIGURAÇÃO DA TABELA DESTINO -----

tabela_destino = "FAT_RASTREABILIDADE"

# ----- QUERY DE EXTRAÇÃO (lendo da Bronze) -----

query = f"""
SELECT
    IPV.NUMNFV,
    IPV.NUMPED,
    IPV.CODPRO,
    PRO.DESPRO,
    IPV.QTDFAT,
    NFV.CODCLI,
    NFV.CODREP,
    NFV.DATEMI,
    CLI.NOMCLI,
    CLI.APECLI,
    CLI.TIPCLI,
    CLI.SIGUFS,
    CLI.CIDCLI,
    CLI.CODRAM,
    REP.NOMREP,
    REP.APEREP,
    REP.TIPREP,
    REP.USU_CODRAM  AS CANREP,
    RAM.DESRAM,
    QRC.USU_CODBAR  AS CODBAR,
    QRC.USU_DATGER  AS DATGER,
    PVD.CODFOR,
    PVD.NOMFOR,
    PVD.NUMOCP,
    PVD.USU_NUMINV  AS NUMINV,
    PVD.NUMNFC,
    PVD.DATEMIOCP   AS DATOCP,
    PVD.USU_DATEMB  AS DATEMB,
    PVD.DATEMINFC,
    PVD.DATENTNFC

FROM {schema_bronze}.E140IPV IPV

INNER JOIN {schema_bronze}.E140NFV NFV
    ON  IPV.NUMNFV = NFV.NUMNFV
    AND IPV.CODSNF = NFV.CODSNF
    AND IPV.CODEMP = NFV.CODEMP
    AND IPV.CODFIL = NFV.CODFIL

INNER JOIN {schema_bronze}.E085CLI CLI
    ON NFV.CODCLI = CLI.CODCLI

INNER JOIN {schema_bronze}.E090REP REP
    ON NFV.CODREP = REP.CODREP

INNER JOIN {schema_bronze}.E026RAM RAM
    ON REP.USU_CODRAM = RAM.CODRAM

INNER JOIN {schema_bronze}.E075PRO PRO
    ON  IPV.CODEMP = PRO.CODEMP
    AND IPV.CODPRO = PRO.CODPRO

INNER JOIN {schema_bronze}.E120IPD IPD
    ON  IPV.NUMPED = IPD.NUMPED
    AND IPV.SEQIPD = IPD.SEQIPD
    AND IPV.CODEMP = IPD.CODEMP
    AND IPV.CODFIL = IPD.CODFIL

INNER JOIN {schema_bronze}.USU_T140QRC QRC
    ON  IPV.CODEMP = QRC.USU_CODEMP
    AND IPV.CODFIL = QRC.USU_CODFIL
    AND IPV.CODSNF = QRC.USU_CODSNF
    AND IPV.NUMNFV = QRC.USU_NUMNFV
    AND IPV.SEQIPV = QRC.USU_SEQIPV

LEFT JOIN {schema_bronze}.USU_VZRASLAU PVD
    ON  QRC.USU_CODBAR = PVD.USU_CODBAR
    AND QRC.USU_CODEMP = PVD.EMPNFV
    AND QRC.USU_CODFIL = PVD.FILNFV

WHERE IPV.CODEMP = 1
  AND IPV.CODFIL = 1
  AND IPV.CODDEP IN ('EXP', 'E-COMMERCE')
  AND TO_CHAR(NFV.DATEMI, 'RRRR/MM/DD') >= '{DATA_CORTE_RASTREABILIDADE}'
  AND IPD.TNSPRO IN ('90100','90101','90120','90170','90171')
  AND TO_CHAR(QRC.USU_DATGER, 'RRRR/MM/DD') >= '{DATA_CORTE_RASTREABILIDADE}'
"""

# ----- EXTRAÇÃO -----

inicio_total = perf_counter()

engine = get_engine_prata()

inicio_extracao = perf_counter()
with engine.connect() as conn:
    df = pd.read_sql(text(query), conn)
print(f"  Tempo extração Oracle: {perf_counter() - inicio_extracao:.1f}s")

df.columns = [col.upper() for col in df.columns]
print(f"  Linhas extraídas: {len(df):,}")

# ----- MERGE COM METAMIX -----

# Replica o LEFT JOIN do legado (transformacao.qvs do Qlik Sense) --
# mesma lógica, mesmo arquivo, mesma aba/colunas.
# MetaMix.xlsx, aba 'Cadastro': Cd_Item -> CODPRO, Cd_Com_Mix -> MIX, Cd_Com_Ori -> ORIGEM

if not EXCEL_METAMIX.exists():
    print(f"  [AVISO] MetaMix.xlsx não encontrado em {EXCEL_METAMIX}")
    print(f"  Os campos MIX e ORIGEM serão carregados como NULL.")
    df["MIX"]    = None
    df["ORIGEM"] = None
else:
    df_mix = pd.read_excel(
        EXCEL_METAMIX,
        sheet_name="Cadastro",
        usecols=["Cd_Item", "Cd_Com_Mix", "Cd_Com_Ori"],
    )
    df_mix.columns = ["CODPRO", "MIX", "ORIGEM"]
    df_mix["CODPRO"] = df_mix["CODPRO"].astype(str).str.strip()
    df["CODPRO"]     = df["CODPRO"].astype(str).str.strip()

    # LEFT JOIN: mantém todos os registros do Oracle, enriquece com MIX e ORIGEM
    df = df.merge(df_mix, on="CODPRO", how="left")
    print(f"  Merge com MetaMix concluído. Linhas após merge: {len(df):,}")

# ----- CARGA -----

dtype_map = build_dtype_map(df)

inicio_carga = perf_counter()
full_reload(engine, df, schema_prata, tabela_destino, chunksize=10000, dtype_map=dtype_map)
print(f"  Tempo carga: {perf_counter() - inicio_carga:.1f}s")

print(f"  Tempo total {tabela_destino}: {perf_counter() - inicio_total:.1f}s")
