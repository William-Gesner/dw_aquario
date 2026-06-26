"""
Estratégias de carga de dados no banco Oracle.

Módulo de infraestrutura compartilhada — usado tanto pela camada Bronze
quanto pela camada Prata. O schema de destino é sempre um parâmetro
(nunca fixo no código), então a mesma função grava em DW_BRONZE, DW_PRATA,
ou qualquer outro schema que vier a existir no projeto.

Disponibiliza duas funções principais, usadas por todos os scripts de extração:

    upsert()      — carga incremental via MERGE (INSERT + UPDATE).
                    Ideal para tabelas de dimensão e dados que mudam com frequência.
    full_reload() — carga completa via DROP + recriação da tabela.
                    Ideal para tabelas de fato volumosas sem chave natural confiável.

Ambas as funções dependem de build_dtype_map() (core/dtype_map.py) para garantir
compatibilidade de tipos com o Oracle.

Além dessas duas, o módulo também expõe tabela_tem_dados() e carregar_bronze(),
que são ESPECÍFICAS da camada Bronze (decidem automaticamente full x incremental
com a janela de 60 dias). Para a Prata, os scripts continuam chamando upsert()
e full_reload() diretamente, escolhendo a estratégia tabela por tabela -- a
estratégia já vem definida no catálogo de cada área, igual já era feito no
projeto legado, só que agora apontando para schema_prata.
"""

# ----- IMPORTS -----

import warnings

import pandas as pd
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from core.dtype_map import build_dtype_map


# ----- FUNÇÕES INTERNAS -----

def _ensure_table(
    engine: Engine,
    df: pd.DataFrame,
    schema: str,
    tabela: str,
    dtype_map: dict,
) -> None:
    """
    Cria a tabela de destino no Oracle caso ela ainda não exista.

    Utiliza o cabeçalho do DataFrame (0 linhas) para inferir a estrutura,
    garantindo que os tipos sejam aplicados conforme o dtype_map fornecido.

    Args:
        engine    : engine SQLAlchemy conectado ao Oracle.
        df        : DataFrame com a estrutura de colunas desejada.
        schema    : schema Oracle de destino (ex.: 'DW_BRONZE', 'DW_PRATA').
        tabela    : nome da tabela de destino.
        dtype_map : mapeamento {coluna: tipo_SQLAlchemy}.
    """
    insp = inspect(engine)

    if not insp.has_table(tabela, schema=schema):
        df.head(0).to_sql(
            name=tabela.upper(),
            con=engine,
            schema=schema,
            if_exists="fail",
            index=False,
            dtype=dtype_map,
        )
        print(f"  Tabela {schema}.{tabela} criada.")
    else:
        print(f"  Tabela {schema}.{tabela} já existe.")


# ----- FUNÇÕES PÚBLICAS -----

def upsert(
    engine: Engine,
    df: pd.DataFrame,
    schema: str,
    tabela: str,
    query: str,
    chaves_merge: list[str],
    coluna_ordem: str,
    dtype_map: dict | None = None,
) -> dict:
    """
    Executa carga incremental via MERGE (upsert) no Oracle.

    Genérica em relação ao schema -- usada tanto pela Bronze (via
    carregar_bronze()) quanto diretamente pelos scripts da Prata.

    Fluxo:
        1. Garante que a tabela de destino existe (_ensure_table).
        2. Conta registros existentes antes do MERGE para calcular inseridos/atualizados.
        3. Monta dinamicamente o SQL MERGE com base nas colunas do DataFrame.
        4. Usa ROW_NUMBER() para desduplicar registros antes do MERGE,
           ordenando pela coluna_ordem para manter sempre o registro mais relevante.
        5. Atualiza registros existentes (WHEN MATCHED) e insere novos (WHEN NOT MATCHED).

    Returns:
        dict com chaves: linhas_extraidas, linhas_inseridas, linhas_atualizadas, linhas_salvas
    """
    if dtype_map is None:
        dtype_map = build_dtype_map(df)

    linhas_extraidas = len(df)
    print(f"  Linhas extraídas : {linhas_extraidas:>10,}")

    # ----- ALERTA DE DATAFRAME VAZIO -----
    if linhas_extraidas == 0:
        print(f"  [AVISO] Nenhuma linha extraída para {schema}.{tabela}. Carga abortada.")
        return {
            "linhas_extraidas": 0,
            "linhas_inseridas": 0,
            "linhas_atualizadas": 0,
            "linhas_salvas": 0,
        }

    _ensure_table(engine, df, schema, tabela, dtype_map)

    # ----- CONTAGEM ANTES DO MERGE -----
    with engine.connect() as conn:
        resultado = conn.execute(text(f"SELECT COUNT(*) FROM {schema}.{tabela}"))
        total_antes = resultado.scalar()

    # ----- MONTAGEM DINÂMICA DO MERGE -----

    colunas        = list(df.columns)
    colunas_update = [col for col in colunas if col not in chaves_merge]

    condicao_merge = " AND ".join(
        [f"DEST.{col} = SRC.{col}" for col in chaves_merge]
    )
    set_update = ",\n        ".join(
        [f"DEST.{col} = SRC.{col}" for col in colunas_update]
    )
    insert_cols   = ",\n        ".join(colunas)
    insert_values = ",\n        ".join([f"SRC.{col}" for col in colunas])
    partition_by  = ",\n                    ".join(chaves_merge)

    merge_sql = f"""
MERGE INTO {schema}.{tabela} DEST
USING (
    SELECT
        {", ".join(colunas)}
    FROM (
        SELECT
            Q.*,
            ROW_NUMBER() OVER (
                PARTITION BY
                    {partition_by}
                ORDER BY
                    {coluna_ordem}
            ) AS RN
        FROM (
            {query}
        ) Q
    )
    WHERE RN = 1
) SRC
ON (
    {condicao_merge}
)
WHEN MATCHED THEN
    UPDATE SET
        {set_update}
WHEN NOT MATCHED THEN
    INSERT (
        {insert_cols}
    )
    VALUES (
        {insert_values}
    )
"""

    with engine.begin() as conn:
        conn.execute(text(merge_sql))

    # ----- CONTAGEM APÓS O MERGE -----
    with engine.connect() as conn:
        resultado = conn.execute(text(f"SELECT COUNT(*) FROM {schema}.{tabela}"))
        total_depois = resultado.scalar()

    linhas_inseridas   = total_depois - total_antes
    linhas_atualizadas = linhas_extraidas - linhas_inseridas
    linhas_salvas      = linhas_inseridas + linhas_atualizadas

    print(f"  Linhas inseridas (novas)    : {linhas_inseridas:>10,}")
    print(f"  Linhas atualizadas          : {linhas_atualizadas:>10,}")
    print(f"  Total salvo em {schema}.{tabela} : {linhas_salvas:>10,}")

    return {
        "linhas_extraidas": linhas_extraidas,
        "linhas_inseridas": linhas_inseridas,
        "linhas_atualizadas": linhas_atualizadas,
        "linhas_salvas": linhas_salvas,
    }


def full_reload(
    engine: Engine,
    df: pd.DataFrame,
    schema: str,
    tabela: str,
    chunksize: int = 10000,
    dtype_map: dict | None = None,
) -> dict:
    """
    Executa carga completa via DROP TABLE + recriação e recarga.

    Genérica em relação ao schema -- usada tanto pela Bronze (via
    carregar_bronze()) quanto diretamente pelos scripts da Prata.

    Indicada para tabelas de fato volumosas, com grande volume de
    alterações e sem chave natural estável o suficiente para um MERGE
    eficiente.

    Fluxo:
        1. Remove a tabela de destino (ignora erro se não existir).
        2. Recria a tabela e insere todos os dados em lotes (chunksize).

    Returns:
        dict com chaves: linhas_extraidas, linhas_salvas
    """
    if dtype_map is None:
        dtype_map = build_dtype_map(df)

    linhas_extraidas = len(df)
    print(f"  Linhas extraídas : {linhas_extraidas:>10,}")

    # ----- ALERTA DE DATAFRAME VAZIO -----
    if linhas_extraidas == 0:
        print(f"  [AVISO] Nenhuma linha extraída para {schema}.{tabela}. Carga abortada.")
        return {
            "linhas_extraidas": 0,
            "linhas_salvas": 0,
        }

    # ----- REMOÇÃO DA TABELA EXISTENTE -----

    with engine.begin() as conn:
        try:
            conn.execute(text(f"DROP TABLE {schema}.{tabela}"))
            print(f"  Tabela {schema}.{tabela} removida.")
        except Exception:
            print(f"  Tabela {schema}.{tabela} não existia, será criada.")

    # ----- RECARGA COMPLETA -----

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        df.to_sql(
            name=tabela.upper(),
            con=engine,
            schema=schema,
            if_exists="append",
            index=False,
            dtype=dtype_map,
            chunksize=chunksize,
        )

    # ----- CONTAGEM PÓS-CARGA -----
    with engine.connect() as conn:
        resultado = conn.execute(text(f"SELECT COUNT(*) FROM {schema}.{tabela}"))
        linhas_salvas = resultado.scalar()

    print(f"  Linhas salvas em {schema}.{tabela}   : {linhas_salvas:>10,}")

    if linhas_salvas != linhas_extraidas:
        print(f"  [AVISO] Divergência: extraídas={linhas_extraidas:,} | salvas={linhas_salvas:,}")
    else:
        print(f"  Extracao e carga conferem [OK]")

    return {
        "linhas_extraidas": linhas_extraidas,
        "linhas_salvas": linhas_salvas,
    }


# ==================================================================
# CAMADA BRONZE 
# ==================================================================
#
# REGRA DE CARGA DA BRONZE — vale para TODAS as 33 tabelas do catálogo
# (comercial/bronze/tabelas.py), SEM EXCEÇÃO:
#
#     1ª carga (tabela de destino não existe OU existe e está vazia):
#         -> FULL. A query de extração deve trazer tudo, filtrando apenas
#            CODEMP = 1 (e CODFIL = 1 onde a tabela tiver esse campo).
#
#     Cargas seguintes (tabela já tem ao menos 1 linha):
#         -> INCREMENTAL. A query de extração já deve vir filtrada pela
#            coluna de data definida no catálogo, com
#            WHERE coluna_data >= SYSDATE - 60
#            (além dos filtros de CODEMP/CODFIL). O MERGE é feito pela PK
#            real da tabela no Sapiens (mesma PK física, já que a Bronze
#            é cópia 1:1 da estrutura de origem, sem transformação).
#
# Quem decide se a query deve ser full ou incremental é o extrator
# (comercial/bronze/extrator.py, Artefato 2), chamando tabela_tem_dados()
# ANTES de montar a query no Sapiens. carregar_bronze() apenas executa a
# estratégia correspondente.
#
# A Prata NÃO usa essa decisão automática -- os scripts de lá chamam
# upsert()/full_reload() direto, com a estratégia já fixa por tabela.
# ==================================================================


# ----- VERIFICAÇÃO DE ESTADO DA TABELA -----

def tabela_tem_dados(engine: Engine, schema: str, tabela: str) -> bool:
    """
    Verifica se a tabela de destino já existe e já tem pelo menos 1 linha.

    Usada pelo extrator (Artefato 2) para decidir, ANTES de montar a query
    no Sapiens, se deve aplicar o filtro de janela de 60 dias ou extrair
    tudo (1ª carga). Também usada internamente por carregar_bronze() para
    escolher entre full_reload() e upsert().
    """
    insp = inspect(engine)

    if not insp.has_table(tabela, schema=schema):
        return False

    with engine.connect() as conn:
        total = conn.execute(text(f"SELECT COUNT(*) FROM {schema}.{tabela}")).scalar()

    return total > 0


# ----- CARGA DA CAMADA BRONZE -----

def carregar_bronze(
    engine: Engine,
    df: pd.DataFrame,
    schema: str,
    tabela: str,
    query: str,
    chaves_pk: list[str],
    coluna_ordem: str | None = None,
    dtype_map: dict | None = None,
    chunksize: int = 10000,
) -> dict:
    """
    Ponto de entrada único de carga para a camada Bronze.

    Decide automaticamente entre full_reload() (1ª carga) e upsert()
    (cargas seguintes, incremental com janela de 60 dias retroativos).

    Args:
        query        : a MESMA query usada para extrair o df, já com o
                       filtro correto (full ou janela de 60 dias) -- essa
                       decisão é tomada previamente pelo chamador usando
                       tabela_tem_dados().
        chaves_pk    : PK real da tabela no Sapiens. Como a Bronze não
                       aplica nenhuma transformação, é a mesma PK física
                       de origem.
        coluna_ordem : usada só na carga incremental, para desduplicar
                       caso a janela de 60 dias traga o mesmo registro
                       mais de uma vez no MERGE. Se None, usa a primeira
                       coluna de chaves_pk.

    Returns:
        dict no mesmo formato retornado por full_reload() ou upsert(),
        dependendo de qual estratégia foi usada.
    """
    primeira_carga = not tabela_tem_dados(engine, schema, tabela)

    if primeira_carga:
        print(f"  [BRONZE] {schema}.{tabela}: 1ª carga -> FULL (sem filtro de data)")
        return full_reload(
            engine, df, schema, tabela, chunksize=chunksize, dtype_map=dtype_map
        )

    print(f"  [BRONZE] {schema}.{tabela}: carga incremental -> MERGE (janela de 60 dias)")
    return upsert(
        engine,
        df,
        schema,
        tabela,
        query=query,
        chaves_merge=chaves_pk,
        coluna_ordem=coluna_ordem or chaves_pk[0],
        dtype_map=dtype_map,
    )