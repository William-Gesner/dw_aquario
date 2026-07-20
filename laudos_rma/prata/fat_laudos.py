"""
Carga do fato central do BI Laudos RMA -- camada Prata.

Origem  : DW_BRONZE.USU_TLAUITE + 13 JOINs (6 exclusivas do Laudos RMA,
          10 compartilhadas com o Comercial -- ver laudos_rma/bronze/tabelas.py)
Destino : DW_PRATA.FAT_LAUDOS (era BIAQUARIO.USU_VBIARMA_LAUDOS no legado)
Carga   : full_reload (DROP + recarga completa) -- MESMA estratégia do
          legado (aquario/laudos_rma/extract/vbilaudos.py).

Classificação: FATO. Grão: item do laudo (1 linha por USU_SEQUNI). Corte
de data: DATA_CORTE_LAUDOS (config, "01/01/2023") -- já existia no
legado, mantido sem alteração (Regra 2: só aplicamos corte novo quando o
legado não tinha nenhum).

----------------------------------------------------------------------
POR QUE full_reload (mesmo motivo do legado, não é "provisório")
----------------------------------------------------------------------
DS_PRAZO e DIAS_PRAZO_LAUDO são calculados em cima da data de hoje
(SYSDATE/date.today()) -- o resultado muda todo dia mesmo sem nenhum
laudo novo ou alterado. Situação e data de finalização dos laudos em
aberto também mudam a qualquer ciclo. Full reload resolve isso de graça
(sempre reflete o estado atual), igual o legado sempre fez.

----------------------------------------------------------------------
MELHORIA APLICADA (1): reincidência via window function, não self-join
----------------------------------------------------------------------
O legado calculava "a entrada anterior mais recente do mesmo número de
série" com um self-join (USU_TLAUITE/E440NFC contra si mesma, via
T1.DATENT > Tz.DATENT + GROUP BY MAX(Tz.DATENT)) -- custo que cresce mal
(O(n²)-like) conforme mais entradas existem pro mesmo número de série.

Substituído por LAG(DATENT) OVER (PARTITION BY USU_SERMAC ORDER BY
DATENT): matematicamente equivalente, porque "o maior valor anterior ao
atual, numa sequência ordenada" É o valor imediatamente anterior (LAG).
As duas versões usam exatamente o mesmo filtro (DATENT > corte e
USU_SERMAC não vazio) tanto na parte "atual" quanto na parte "anterior"
do cálculo original -- por isso dá pra reduzir a um único conjunto
distinto de (DATENT, USU_SERMAC) com uma janela por cima, em vez de duas
varreduras casadas por desigualdade.

Resultado esperado idêntico ao legado -- validado pela
conferencia_fat_laudos.py (MINUS dado a dado) antes de considerar esta
tabela pronta. Se algum caso de borda divergir, a conferência pega.

----------------------------------------------------------------------
MELHORIA APLICADA (2): _int_str() vetorizado, sem .apply() linha a linha
----------------------------------------------------------------------
A versão original convertia NUMBER do Oracle pra string inteira limpa
("14.0" -> "14") chamando uma função Python por linha via .apply() --
lento em volume. Reescrita com pd.to_numeric + Int64 (vetorizado, sem
loop em Python), mesmo resultado nos 3 casos do docstring original:
valor numérico, nulo (NaN/None -> "") e já-texto (mantido como está).

----------------------------------------------------------------------
NÃO ALTERADO
----------------------------------------------------------------------
Toda a lógica de DS_PRAZO, REINCIDENTE, MACRO_REGIAO, DS_ORIGEM_FISCAL,
DIAS_ENTREGA, DS_CLASSIF_ENTREGA, DS_TIPO_TRANSPORTE etc. já usa
np.select/np.where (vetorizado) no legado -- mantida exatamente igual,
sem reescrever para SQL. Reescrever essa parte teria risco maior que o
ganho (mesmo critério usado para rejeitar a deduplicação do FUNDPOB no
FAT_FATURAMENTO do Comercial).
"""

# ----- IMPORTS -----

from datetime import date
from time import perf_counter

import numpy as np
import pandas as pd
from sqlalchemy import text

from core.db import get_engine_prata
from core.dtype_map import build_dtype_map
from core.loader import full_reload
from laudos_rma.config.settings import DATA_CORTE_LAUDOS, schema_bronze, schema_prata

# ----- CONFIGURAÇÃO DA TABELA DESTINO -----

tabela_destino = "FAT_LAUDOS"

# ----- FUNÇÃO AUXILIAR -- conversão vetorizada de NUMBER para string inteira -----

def _int_str(series: pd.Series) -> pd.Series:
    """
    Converte uma coluna numérica (NUMBER do Oracle) para string inteira limpa,
    sem o sufixo decimal ".0" que o pandas produz ao fazer .astype(str) em floats.
    Versão vetorizada (sem .apply() linha a linha) -- mesmo resultado:
        0.0      -> "0"
        14.0     -> "14"
        NaN/None -> ""      (NULL do Oracle vira string vazia, não "nan")
        já-texto -> mantido como estava (ex.: código alfanumérico)
    """
    numerico = pd.to_numeric(series, errors="coerce")
    resultado = np.select(
        [series.isna(), numerico.notna()],
        ["", numerico.astype("Int64").astype(str)],
        default=series.astype(str).str.strip(),
    )
    return pd.Series(resultado, index=series.index)


# ----- QUERY -- FATO PRINCIPAL -----

# Fiel ao extracao.qvs do Qlik Sense.
# USU_VZRASLAU já conhecida -- view válida (usada também em Rastreabilidade).

query_fato = f"""
SELECT
    T0.USU_CODEMP,
    T0.USU_CODFIL,
    T0.USU_CODFOR,
    T7.NOMFOR,
    T7.SIGUFS,
    T7.CIDFOR,
    T7.CODCLI,
    T7.TIPFOR,
    T7.FONFOR,
    T7.FONFO2,
    T7.FONFO3,
    T7.INTNET,
    T0.USU_NUMNFC,
    T0.USU_SEQIPC,
    T0.USU_SEQUNI,
    T6.USU_DATCON,
    T6.DATENT,
    T0.USU_CODLAU,
    T1.USU_TIPLAU,
    T2.USU_DESTIP,
    T0.USU_SERMAC,
    T0.USU_CODPRO,
    T0.USU_CODDER,
    T9.CODAGT,
    T10.DESAGP,
    T8.CODORI,
    T8.ORIMER,
    T0.USU_CODDEF,
    T3.USU_DESDEF,
    T0.USU_PECFAL,
    T0.USU_PECTRO,
    T0.USU_CODCOR,
    T14.USU_DESCOR,
    T0.USU_USUTEC,
    T11.NOMCOM,
    T0.USU_TMPUTI,
    T1.USU_NUMNFV,
    T1.USU_USUFIN,
    T1.USU_DATALT,
    CASE WHEN T1.USU_CODSIT IN ('3','4','5','6','8')
         THEN T1.USU_DATSEP
         ELSE NULL
    END                                         AS DATFIN,
    T0.USU_OBSCLI,
    T0.USU_CODPRB,
    T5.USU_DESPRB,
    T1.USU_CODSIT,
    T4.USU_DESSIT,
    1                                           AS QTDREG,
    T12.DATEMI,
    T12.USU_CODRAS,
    T12.USU_ENTCOR,
    T12.CODTRA,
    T13.APETRA,
    T15.NUMOCP,
    T15.DATEMIOCP,
    T15.CODFOR,
    T15.NOMFOR                                  AS NOMFORCOMP,
    T15.USU_NUMINV,
    T15.USU_DATEMB,
    T15.NUMNFC,
    T15.DATEMINFC

FROM {schema_bronze}.USU_TLAUITE T0

LEFT JOIN {schema_bronze}.USU_TLAUGER T1
    ON  T0.USU_CODLAU = T1.USU_CODLAU
    AND T0.USU_CODEMP = T1.USU_CODEMP
    AND T0.USU_CODFIL = T1.USU_CODFIL

LEFT JOIN {schema_bronze}.USU_TLAUTIP T2
    ON  T1.USU_TIPLAU = T2.USU_CODTIP

LEFT JOIN {schema_bronze}.USU_TLAUDEF T3
    ON  T0.USU_CODEMP = T3.USU_CODEMP
    AND T0.USU_CODPRO = T3.USU_CODPRO
    AND T0.USU_CODDER = T3.USU_CODDER
    AND T0.USU_CODDEF = T3.USU_CODDEF

LEFT JOIN {schema_bronze}.USU_TLAUSIT T4
    ON  T1.USU_CODSIT = T4.USU_CODSIT

LEFT JOIN {schema_bronze}.USU_TLAUPRB T5
    ON  T0.USU_CODPRB = T5.USU_CODPRB

LEFT JOIN {schema_bronze}.E440NFC T6
    ON  T0.USU_CODEMP = T6.CODEMP
    AND T0.USU_CODFIL = T6.CODFIL
    AND T0.USU_CODFOR = T6.CODFOR
    AND T0.USU_NUMNFC = T6.NUMNFC

LEFT JOIN {schema_bronze}.E095FOR T7
    ON  T0.USU_CODFOR = T7.CODFOR

LEFT JOIN {schema_bronze}.E075PRO T8
    ON  T0.USU_CODEMP = T8.CODEMP
    AND T0.USU_CODPRO = T8.CODPRO

LEFT JOIN {schema_bronze}.E075DER T9
    ON  T9.CODEMP = T0.USU_CODEMP
    AND T9.CODPRO = T0.USU_CODPRO
    AND T9.CODDER = T0.USU_CODDER

LEFT JOIN {schema_bronze}.E013AGP T10
    ON  T9.CODEMP  = T10.CODEMP
    AND T9.CODAGT  = T10.CODAGP
    AND T10.TIPAGP = 'T'

LEFT JOIN {schema_bronze}.R910USU T11
    ON  T0.USU_USUTEC = T11.CODENT

LEFT JOIN {schema_bronze}.E140NFV T12
    ON  T12.CODEMP = T1.USU_CODEMP
    AND T12.CODFIL = T1.USU_CODFIL
    AND T12.NUMNFV = T1.USU_NUMNFV

LEFT JOIN {schema_bronze}.E073TRA T13
    ON  T13.CODTRA = T12.CODTRA

LEFT JOIN {schema_bronze}.USU_TLAUCOR T14
    ON  T0.USU_CODCOR = T14.USU_CODCOR

LEFT JOIN {schema_bronze}.USU_VZRASLAU T15
    ON  T0.USU_SERMAC = T15.USU_CODBAR
    AND T0.USU_CODEMP = T15.EMPNFV
    AND T0.USU_CODFIL = T15.FILNFV

WHERE T6.DATENT >= TO_DATE('{DATA_CORTE_LAUDOS}', 'DD/MM/YYYY')
"""

# ----- QUERY -- REINCIDÊNCIA (otimizada -- ver docstring do módulo) -----

# Equivalente ao self-join original (REINCIDENTE_TEMP do extracao.qvs):
# "a entrada anterior mais recente do mesmo número de série" == o valor
# imediatamente anterior numa sequência ordenada por DATENT, dentro da
# mesma partição de USU_SERMAC. Chave de join com o fato: DATENT +
# USU_SERMAC (equivalente ao @CH_REINC do Qlik).
query_reincidencia = f"""
SELECT
    DATENT,
    USU_SERMAC,
    LAG(DATENT) OVER (
        PARTITION BY USU_SERMAC
        ORDER BY DATENT
    ) AS DATREI
FROM (
    SELECT DISTINCT
        T1.DATENT,
        T2.USU_SERMAC
    FROM {schema_bronze}.USU_TLAUITE T2
    LEFT JOIN {schema_bronze}.E440NFC T1
        ON  T2.USU_CODEMP = T1.CODEMP
        AND T2.USU_CODFIL = T1.CODFIL
        AND T2.USU_CODFOR = T1.CODFOR
        AND T2.USU_NUMNFC = T1.NUMNFC
    WHERE T1.DATENT      > TO_DATE('{DATA_CORTE_LAUDOS}', 'DD/MM/YYYY')
      AND T2.USU_SERMAC IS NOT NULL
      AND T2.USU_SERMAC <> ' '
)
"""

# ----- EXTRAÇÃO -----

inicio_total = perf_counter()

engine = get_engine_prata()

print("  Extraindo fato principal...")
inicio_extracao_fato = perf_counter()
with engine.connect() as conn:
    df = pd.read_sql(text(query_fato), conn)
print(f"  Tempo extração (fato): {perf_counter() - inicio_extracao_fato:.1f}s")

df.columns = [col.upper() for col in df.columns]
print(f"  Linhas extraídas (fato): {len(df):,}")

print("  Extraindo reincidência...")
inicio_extracao_reinc = perf_counter()
with engine.connect() as conn:
    df_reinc = pd.read_sql(text(query_reincidencia), conn)
print(f"  Tempo extração (reincidência): {perf_counter() - inicio_extracao_reinc:.1f}s")

df_reinc.columns = [col.upper() for col in df_reinc.columns]
print(f"  Linhas extraídas (reincidência): {len(df_reinc):,}")

# ----- JOIN REINCIDÊNCIA (concatena_fato.qvs) -----

# Replica o LEFT JOIN do concatena_fato.qvs do Qlik Sense.
# Chave: DATENT + USU_SERMAC -- equivalente ao @CH_REINC do Qlik.

df = df.merge(df_reinc, on=["DATENT", "USU_SERMAC"], how="left")
print(f"  Linhas após join com reincidência: {len(df):,}")

# ----- LÓGICA DE NEGÓCIO (fato.qvs) -----

inicio_logica = perf_counter()

hoje = pd.Timestamp(date.today())

# Garantir tipos datetime antes dos cálculos
for col in ["DATENT", "DATFIN", "DATEMI", "USU_ENTCOR", "DATREI"]:
    df[col] = pd.to_datetime(df[col], errors="coerce")

# ----- CHAVES DE RELACIONAMENTO -----
# USU_CODDEF e USU_CODPRO vêm do Oracle como NUMBER/VARCHAR -- _int_str()
# garante "0", "14" (não "0.0", "14.0") pra coluna NUMBER.

# PROD_COD_DEF: equivalente ao @ProdCodDef do Qlik (USU_CODPRO|USU_CODDEF)
df["PROD_COD_DEF"] = (
    df["USU_CODPRO"].astype(str) + "|" + _int_str(df["USU_CODDEF"])
)

# VENDA_MES_ANO_PRODUTO: equivalente ao @VendaMêsAnoProduto do Qlik
# USU_CODPRO é VARCHAR no Oracle (código alfanumérico como "DTV-100"), então
# .astype(str) é seguro aqui -- mantido como estava, sem risco de .0
df["VENDA_MES_ANO_PRODUTO"] = (
    df["DATENT"].dt.month.astype(str) + "|" +
    df["DATENT"].dt.year.astype(str)  + "|" +
    df["USU_CODPRO"].astype(str)
)

# Macro Região por UF -- fiel ao fato.qvs do Qlik Sense
mapa_regiao = {
    "RS": "Sul",       "SC": "Sul",       "PR": "Sul",
    "SP": "Sudeste",   "RJ": "Sudeste",   "ES": "Sudeste",   "MG": "Sudeste",
    "RR": "Norte",     "RO": "Norte",     "AM": "Norte",     "AC": "Norte",
    "AP": "Norte",     "TO": "Norte",     "PA": "Norte",
    "CE": "Nordeste",  "PI": "Nordeste",  "SE": "Nordeste",  "RN": "Nordeste",
    "PB": "Nordeste",  "PE": "Nordeste",  "BA": "Nordeste",  "MA": "Nordeste",
    "AL": "Nordeste",
    "DF": "Centro-Oeste", "MS": "Centro-Oeste",
    "MT": "Centro-Oeste", "GO": "Centro-Oeste",
}
df["MACRO_REGIAO"] = df["SIGUFS"].map(mapa_regiao)

# Origem Fiscal -- fiel ao fato.qvs
importados = {"1", "6", "3", "8", "7"}
df["DS_ORIGEM_FISCAL"] = df["ORIMER"].astype(str).apply(
    lambda x: "Importado" if x in importados else "Nacional"
)

# Ds_Prazo -- fiel ao fato.qvs
dias_desde_entrada   = (hoje - df["DATENT"]).dt.days
dias_ate_finalizacao = (df["DATFIN"] - df["DATENT"]).dt.days
sem_finalizacao      = df["DATFIN"].isna()

df["DS_PRAZO"] = np.select(
    [
        sem_finalizacao & (dias_desde_entrada > 10),
        sem_finalizacao & (dias_desde_entrada <= 10),
        (~sem_finalizacao) & (dias_ate_finalizacao <= 10),
        (~sem_finalizacao) & (dias_ate_finalizacao > 10),
    ],
    [
        "Em Aberto Atrasado",
        "Em Aberto no Prazo",
        "Finalizado no Prazo",
        "Finalizado em Atraso",
    ],
    default=None,
)

# #DiasPrazoLaudo -- fiel ao fato.qvs
df["DIAS_PRAZO_LAUDO"] = np.where(
    sem_finalizacao,
    dias_desde_entrada,
    dias_ate_finalizacao,
)

# #Reincidente e #Dias_Reincidencia -- fiel ao fato.qvs
serie_invalida    = df["USU_SERMAC"].isin([" ", "S/N", "SN"]) | df["USU_SERMAC"].isna()
dias_reincidencia = (df["DATENT"] - df["DATREI"]).dt.days

df["DIAS_REINCIDENCIA"] = np.where(
    serie_invalida | df["DATREI"].isna(), 0, dias_reincidencia
)
df["REINCIDENTE"] = np.select(
    [
        serie_invalida,
        (~serie_invalida) & (df["DATREI"].isna() | (dias_reincidencia > 180)),
        (~serie_invalida) & (dias_reincidencia <= 180),
    ],
    [2, 0, 1],
    default=0,
)

# Datas de finalização separadas -- fiel ao fato.qvs
df["DT_ANO_FINALIZ"] = np.where(
    df["DATFIN"].isna() | (df["DATFIN"] == pd.Timestamp("1900-12-31")),
    "Sem Data",
    df["DATFIN"].dt.year.astype("Int64").astype(str),
)
df["DT_MES_FINALIZ"] = df["DATFIN"].dt.month
df["DT_DIA_FINALIZ"] = df["DATFIN"].dt.day

# Transportadora entrega -- fiel ao fato.qvs
transportadoras_entrega = {
    "TEX COURIER LTDA. EM RECUPERACAO JUDICIAL",
    "CORREIO / SEDEX",
}
df["DS_TRANSPORTADORA_ENTREGA"] = df["APETRA"].apply(
    lambda x: x if x in transportadoras_entrega else None
)

# #DiasEntrega -- fiel ao fato.qvs
dias_entrega_raw    = (df["USU_ENTCOR"] - df["DATENT"]).dt.days
dias_entrega_valido = df["USU_ENTCOR"].notna() & (dias_entrega_raw >= 0)

df["DIAS_ENTREGA"] = np.where(dias_entrega_valido, dias_entrega_raw, None)

# Ds_ClassifEntrega -- fiel ao fato.qvs
df["DS_CLASSIF_ENTREGA"] = np.select(
    [
        ~dias_entrega_valido,
        dias_entrega_raw > 30,
        dias_entrega_raw > 20,
        dias_entrega_raw > 10,
        dias_entrega_raw > 0,
    ],
    [
        "Sem Data",
        "Maior que 30 Dias",
        "Entre 21 e 30 Dias",
        "Entre 11 e 20 Dias",
        "Entre 0 e 10 Dias",
    ],
    default="Sem Data",
)

# Ds_TipoTransporte -- fiel ao fato.qvs
df["DS_TIPO_TRANSPORTE"] = np.select(
    [
        df["APETRA"].isna(),
        df["APETRA"] == "CORREIO / SEDEX",
        df["APETRA"] == "RETIRA",
    ],
    ["Sem NFSaída", "Correios", "Retirada"],
    default="Transportadoras",
)

print(f"  Tempo lógica de negócio (pandas): {perf_counter() - inicio_logica:.1f}s")

# ----- CARGA -----

dtype_map = build_dtype_map(df)

inicio_carga = perf_counter()
full_reload(engine, df, schema_prata, tabela_destino, chunksize=10000)
print(f"  Tempo carga: {perf_counter() - inicio_carga:.1f}s")

print(f"  Tempo total {tabela_destino}: {perf_counter() - inicio_total:.1f}s")
