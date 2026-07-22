"""
Carga da dimensão de centros de custo do BI Produção -- camada Prata.

Origem  : DW_BRONZE.E720OPR, E044CCU, E093ETG, E725CRE (todas exclusivas
          do catálogo da Produção)
Destino : DW_PRATA.DIM_CENTRO_CUSTO_PRODUCAO (era
          BIAQUARIO.USU_VBIAPROD_CENTROCUSTO no legado)
Carga   : upsert (MERGE por CODCCU + CODETG + CODCRE + CODOPR).

Classificação: DIMENSÃO -- sem corte de data (Regra 2 da Fase 2).

Extrai a estrutura de centros de custo, estágios, centros de recurso e
operações da produção, incluindo centros de recurso sem estágios
vinculados (2º bloco do UNION ALL -- lista hardcoded fiel ao legado).

----------------------------------------------------------------------
CORREÇÃO (21/07/2026): CODOPR incluído na chave de merge
----------------------------------------------------------------------
O legado usava chaves_merge = [CODCCU, CODETG, CODCRE] (sem CODOPR) --
mas a granularidade real da query é por E720OPR (a tabela-âncora do
FROM, PK real CODEMP+CODOPR). Quando mais de uma operação existe pro
mesmo centro de custo/estágio/centro de recurso (comum -- confirmado
21 grupos reais em produção, até 23 operações num único grupo), o MERGE
com a chave antiga só conseguia guardar 1 operação por grupo, descartando
as demais -- tanto no legado quanto na 1ª versão desta migração (mesmo
bug herdado fielmente). Confirmado com consulta direta em E720OPR
(Sapiens e Bronze, idênticas) que as operações são registros reais e
distintos, não duplicata/lixo. Corrigido incluindo CODOPR na chave --
a tabela cresce de ~133 para ~194 linhas (a granularidade correta, não
inflação). Ver dw_aquario/doc_nova_arquitetura.md, seção "Produção",
para o levantamento completo (contagem por grupo, casos investigados).

Conferência desta tabela usa uma técnica diferente das outras (ver
conferencia_dim_centro_custo_producao.py) -- não compara "idêntico ao
legado" (o legado tem a mesma limitação, não é fonte de verdade aqui),
compara contra E720OPR/Bronze diretamente.

----------------------------------------------------------------------
BUG CORRIGIDO (22/07/2026): CODOPR podia vir NULL, duplicando linha a
cada execução
----------------------------------------------------------------------
O 2º bloco do UNION ALL (centros de recurso sem estágio) faz LEFT JOIN
de E720OPR -- pra 10 dos 11 códigos de CODCRE da lista hardcoded, não
existe nenhuma operação vinculada, então OPR.CODOPR vem NULL. Como
CODOPR passou a fazer parte da chaves_merge (correção acima), e
`NULL = NULL` nunca é verdadeiro em SQL, o MERGE nunca reconhecia a
linha já existente como "a mesma" -- toda execução inserida uma cópia
nova (confirmado na VM: 10 grupos com 2 linhas idênticas cada, exceto
CODOPR nulo). Corrigido com `NVL(OPR.CODOPR, ' ')` no 2º bloco (mesma
convenção de "vazio = espaço" já usada nesta mesma query pra
CODETG/DESETG/ABRETG). LIÇÃO GERAL: qualquer coluna usada em
chaves_merge precisa ser NOT NULL (ou tratada com NVL/COALESCE) --
coluna nula numa chave de merge faz o MERGE duplicar em vez de
atualizar, silenciosamente, a cada ciclo.

Depois desta correção, a tabela precisou ser dropada e recarregada do
zero na VM (DROP TABLE DW_PRATA.DIM_CENTRO_CUSTO_PRODUCAO) pra remover
as duplicatas já criadas pelas execuções anteriores -- upsert() nunca
remove linha, só o DROP limpa o que já foi duplicado.
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

tabela_destino = "DIM_CENTRO_CUSTO_PRODUCAO"

# ----- QUERY DE EXTRAÇÃO (lendo da Bronze) -----

query = f"""
SELECT
    OPR.CODCCU,
    CCU.DESCCU,
    CCU.ABRCCU,
    CCU.CCUPAI,
    OPR.CODETG,
    ETG.DESETG,
    ETG.ABRETG,
    OPR.CODCRE,
    CRE.DESCRE,
    CRE.ABRCRE,
    OPR.CODOPR,
    OPR.DESOPR,
    OPR.ABROPR,
    OPR.UNICRE,
    OPR.MOVORP

FROM {schema_bronze}.E720OPR OPR

LEFT JOIN {schema_bronze}.E044CCU CCU
    ON  CCU.CODEMP = OPR.CODEMP
    AND CCU.CODCCU = OPR.CODCCU

LEFT JOIN {schema_bronze}.E093ETG ETG
    ON  ETG.CODEMP = OPR.CODEMP
    AND ETG.CODETG = OPR.CODETG

LEFT JOIN {schema_bronze}.E725CRE CRE
    ON  CRE.CODEMP = OPR.CODEMP
    AND CRE.CODCRE = OPR.CODCRE

WHERE OPR.CODEMP = 1

UNION ALL

-- Centros de Recurso sem Estágios vinculados (lista fiel ao legado)
SELECT
    CRE.CODCCU,
    CCU.DESCCU,
    CCU.ABRCCU,
    CCU.CCUPAI,
    0          AS CODETG,
    ' '        AS DESETG,
    ' '        AS ABRETG,
    CRE.CODCRE,
    CRE.DESCRE,
    CRE.ABRCRE,
    NVL(OPR.CODOPR, ' ')                            AS CODOPR,
    OPR.DESOPR,
    OPR.ABROPR,
    OPR.UNICRE,
    OPR.MOVORP

FROM {schema_bronze}.E725CRE CRE

LEFT JOIN {schema_bronze}.E044CCU CCU
    ON  CCU.CODEMP = CRE.CODEMP
    AND CCU.CODCCU = CRE.CODCCU

LEFT JOIN {schema_bronze}.E720OPR OPR
    ON  CRE.CODEMP = OPR.CODEMP
    AND CRE.CODCRE = OPR.CODCRE

WHERE CRE.CODEMP = 1
  AND CRE.CODCRE IN ('7020','7120','7320','7420','7520','8120','3020','3220','2540','2940','2240')
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
    chaves_merge=["CODCCU", "CODETG", "CODCRE", "CODOPR"],
    coluna_ordem="CODCCU ASC",
    dtype_map=dtype_map,
)
print(f"  Tempo carga: {perf_counter() - inicio_carga:.1f}s")

print(f"  Tempo total {tabela_destino}: {perf_counter() - inicio_total:.1f}s")
