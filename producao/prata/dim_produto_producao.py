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

----------------------------------------------------------------------
CORREÇÃO (22/07/2026): desempate de CODDER amarrado ao legado
----------------------------------------------------------------------
`chaves_merge = [CODEMP, CODPRO]` (igual ao legado) não reflete a
granularidade real de E075DER (PK real CODEMP+CODPRO+CODDER -- ver
comercial/bronze/tabelas.py). Quando um produto tem mais de uma
derivação (~96 casos confirmados, ex.: CODPRO='4K01' com CODDER em
'B'/'N'/'U', todas ativas, sem coluna que indique qual é "a" principal),
o MERGE só guarda 1 CODDER por produto -- e a escolha, sem nenhum
ORDER BY que desempate de verdade, depende só da ordem física com que o
Oracle devolve as linhas do JOIN, que MUDA entre Sapiens (legado) e
Bronze (Prata), mesmo com os dados idênticos dos dois lados.

Confirmado com o usuário (22/07/2026), comparando amostra de divergências
da conferência: não existe critério de coluna (nem alfabético, nem
SITDER, nem nenhum outro campo usado na query) que explique a escolha do
legado -- em alguns grupos ele "parece" pegar o maior CODDER, em outros
o menor, sem consistência. Não dá pra reproduzir via ORDER BY comum.

Decisão: em vez de tentar adivinhar uma regra, o desempate passa a
PREFERIR explicitamente o CODDER que já está gravado hoje em
BIAQUARIO.USU_VBIAPROD_PRODUTO (legado) para aquele CODPRO -- LEFT JOIN
só para esse fim, calculando PRIORIDADE_LEGADO (0 = bate com o legado,
1 = não bate/produto novo sem equivalente no legado). Essa coluna é
usada SÓ no ORDER BY do MERGE (dedup via ROW_NUMBER, ver core/loader.py
upsert()) -- é removida do DataFrame antes da carga, então nunca vira
coluna física em DW_PRATA.DIM_PRODUTO_PRODUCAO. Fallback determinístico
(CODDER ASC) cobre produtos sem linha no legado (não tem o que amarrar).

LIMITAÇÃO CONHECIDA: esse amarramento só funciona enquanto
BIAQUARIO.USU_VBIAPROD_PRODUTO existir. Quando o legado for desligado
(fim da migração), a ambiguidade volta -- nesse momento será preciso uma
decisão de negócio real (ex.: mudar a granularidade pra CODPRO+CODDER,
mesmo padrão já usado em DIM_PRODUTO do Comercial) ou aceitar o resíduo
como está congelado no último ciclo antes do desligamento. Ver
dw_aquario/doc_nova_arquitetura.md, seção "Produção", para o histórico
completo.
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
    NVL(CASE WHEN T0.USU_INDFDL = ' ' THEN 'N' ELSE T0.USU_INDFDL END, 'N') AS USU_INDFDL,

    -- Só para desempate de CODDER (removida do df antes da carga, nunca
    -- vira coluna física -- ver docstring "CORREÇÃO 22/07/2026" acima).
    CASE WHEN TRIM(T1.CODDER) = TRIM(LEG.CODDER) THEN 0 ELSE 1 END AS PRIORIDADE_LEGADO

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

LEFT JOIN BIAQUARIO.USU_VBIAPROD_PRODUTO LEG
    ON  LEG.CODEMP = T0.CODEMP
    AND LEG.CODPRO = T0.CODPRO

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

# PRIORIDADE_LEGADO só serve para o ORDER BY do MERGE (via `query`,
# reexecutada no banco por upsert()) -- nunca deve virar coluna física
# em DW_PRATA.DIM_PRODUTO_PRODUCAO.
df = df.drop(columns=["PRIORIDADE_LEGADO"])

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
    coluna_ordem="PRIORIDADE_LEGADO ASC, CODDER ASC",
    dtype_map=dtype_map,
)
print(f"  Tempo carga: {perf_counter() - inicio_carga:.1f}s")

print(f"  Tempo total {tabela_destino}: {perf_counter() - inicio_total:.1f}s")
