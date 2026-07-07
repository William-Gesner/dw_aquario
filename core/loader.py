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
from sqlalchemy.types import CLOB, DateTime, Integer, Numeric, String

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
    # IMPORTANTE: a verificação de existência é feita ANTES do DROP (via
    # inspect().has_table), em vez de um "except Exception" genérico. Um
    # except genérico mascararia QUALQUER falha no DROP (lock, permissão,
    # timeout) como se fosse simplesmente "tabela não existe", e o fluxo
    # seguiria para o to_sql(if_exists="append") gravando os dados novos POR
    # CIMA dos antigos -- misturando registros já cancelados/obsoletos com
    # os dados atuais (bug já visto no projeto legado, ver aquario/core/loader.py).

    insp = inspect(engine)

    if insp.has_table(tabela, schema=schema):
        with engine.begin() as conn:
            conn.execute(text(f"DROP TABLE {schema}.{tabela}"))
        print(f"  Tabela {schema}.{tabela} removida.")
    else:
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


def _dtype_map_da_origem(engine: Engine, owner_origem: str, tabela: str) -> dict:
    """
    Monta o dtype_map a partir da definição REAL das colunas na origem
    (ALL_TAB_COLUMNS), em vez de inferir pelo conteúdo de uma amostra.

    Por que não inferir por amostra (como build_dtype_map faz para a
    Prata): se o maior valor de uma coluna de texto só aparecer fora da
    amostra usada pra criar a tabela, o INSERT falha com ORA-12899 (valor
    maior que a coluna) -- foi o que aconteceu com E120IPD.OBSIPD em
    06/07/2026, usando só o 1º lote de 100 mil linhas como amostra.

    Como a Bronze é cópia 1:1 da estrutura de origem ("mesma estrutura,
    mesmo nome, sem transformação"), o tamanho de cada coluna de destino
    deve ser IGUAL ao declarado na origem -- não estimado.
    """
    query = """
        SELECT column_name, data_type, data_length, data_precision, data_scale
        FROM ALL_TAB_COLUMNS
        WHERE owner = :owner AND table_name = :tabela
        ORDER BY column_id
    """
    with engine.connect() as conn:
        colunas = conn.execute(
            text(query), {"owner": owner_origem, "tabela": tabela}
        ).fetchall()

    if not colunas:
        raise ValueError(
            f"Nenhuma coluna encontrada para {owner_origem}.{tabela} em "
            f"ALL_TAB_COLUMNS -- confira se o nome da tabela está correto "
            f"e se o usuário de conexão tem privilégio de leitura nela."
        )

    dtype_map = {}

    for coluna_nome, tipo, tamanho, precisao, escala in colunas:
        nome = coluna_nome.upper()

        if tipo == "NUMBER":
            if escala in (0, None) and (precisao is None or precisao <= 18):
                dtype_map[nome] = Integer()
            else:
                dtype_map[nome] = Numeric(precisao or 38, escala or 10)

        elif tipo in ("DATE",) or tipo.startswith("TIMESTAMP"):
            dtype_map[nome] = DateTime()

        elif tipo in ("CLOB", "NCLOB", "LONG"):
            dtype_map[nome] = CLOB()

        elif tipo in ("VARCHAR2", "NVARCHAR2", "CHAR", "NCHAR"):
            if tamanho is None or tamanho > 4000:
                dtype_map[nome] = CLOB()
            else:
                dtype_map[nome] = String(min(tamanho + 10, 4000))

        else:
            # Tipo não mapeado explicitamente (ex.: RAW, BLOB) -- fallback seguro.
            dtype_map[nome] = String(4000)

    return dtype_map


def full_reload_streaming(
    engine: Engine,
    query: str,
    schema: str,
    tabela: str,
    owner_origem: str = "SAPIENS",
    chunksize: int = 100_000,
) -> dict:
    """
    Full reload lendo a query em lotes direto do cursor Oracle, em vez de
    montar a tabela inteira em um único DataFrame antes de gravar.

    Usada nas tabelas grandes/transacionais da Bronze (ex.: E120IPD, com
    1,4 milhão de linhas x 285 colunas -- um pd.read_sql() sem chunksize
    estourou a memória do processo em 06/07/2026 tentando montar tudo de
    uma vez antes mesmo de começar a gravar).

    O dtype_map vem de _dtype_map_da_origem() -- schema REAL do Sapiens via
    ALL_TAB_COLUMNS, não de uma amostra dos dados -- então não depende de
    qual lote é lido primeiro nem corre risco de ORA-12899 por causa de um
    valor de texto maior que o previsto.

    Returns:
        dict com chaves: linhas_extraidas, linhas_salvas
    """
    insp = inspect(engine)

    if insp.has_table(tabela, schema=schema):
        with engine.begin() as conn:
            conn.execute(text(f"DROP TABLE {schema}.{tabela}"))
        print(f"  Tabela {schema}.{tabela} removida.")
    else:
        print(f"  Tabela {schema}.{tabela} não existia, será criada.")

    dtype_map = _dtype_map_da_origem(engine, owner_origem, tabela)
    linhas_extraidas = 0

    with engine.connect() as conn:
        for i, chunk in enumerate(pd.read_sql(text(query), conn, chunksize=chunksize), start=1):
            chunk.columns = [col.upper() for col in chunk.columns]

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                chunk.to_sql(
                    name=tabela.upper(),
                    con=engine,
                    schema=schema,
                    if_exists="append",
                    index=False,
                    dtype=dtype_map,
                )

            linhas_extraidas += len(chunk)
            print(f"  Lote {i:>3}: +{len(chunk):>8,} linhas (acumulado: {linhas_extraidas:>10,})")

    if linhas_extraidas == 0:
        print(f"  [AVISO] Nenhuma linha extraída para {schema}.{tabela}. Carga abortada.")
        return {"linhas_extraidas": 0, "linhas_salvas": 0}

    with engine.connect() as conn:
        linhas_salvas = conn.execute(text(f"SELECT COUNT(*) FROM {schema}.{tabela}")).scalar()

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
#
# REMOÇÃO DE ÓRFÃOS (registros deletados fisicamente na origem):
#     Diferente do projeto legado (aquario/core/loader.py), o upsert() da
#     Bronze NÃO remove órfãos usando a query incremental (janela de 60
#     dias) -- um NOT EXISTS contra esse subconjunto apagaria da Bronze
#     tudo que é mais antigo que a janela, não só os órfãos de verdade
#     (caso real: meta de funcionário que saiu, deletada no Sapiens --
#     ver conversa de 06/07/2026). Em vez disso, remover_orfaos() (abaixo)
#     roda com uma query SEPARADA, que traz só as colunas de PK, no escopo
#     cheio (CODEMP/CODFIL, sem filtro de data nenhum) -- ou seja, o
#     universo completo e atual do Sapiens. Só é removido da Bronze o que
#     não aparece em lugar nenhum desse universo; qualquer linha que ainda
#     exista no Sapiens (de qualquer data) nunca é tocada.
#
#     carregar_bronze() só chama remover_orfaos() quando o chamador
#     fornece query_pks_completo (nunca acontece na 1ª carga -- ali o
#     full_reload_streaming() já reflete exatamente o estado atual do
#     Sapiens, sem risco de sobra). No Comercial (comercial/bronze/
#     extrator.py), essa query só é fornecida na ÚLTIMA execução do dia
#     (flag --sweep-orfaos) -- rodar essa varredura a cada ciclo de 15 min
#     seria custo de I/O repetido e desnecessário contra tabelas de até
#     1,4 milhão de linhas no Sapiens em produção, quando exclusão física
#     é rara no dia a dia (decisão de 06/07/2026).
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


# ----- REMOÇÃO DE ÓRFÃOS (CAMADA BRONZE) -----

def remover_orfaos(
    engine: Engine,
    schema: str,
    tabela: str,
    chaves_pk: list[str],
    query_pks_completo: str,
) -> int:
    """
    Remove da Bronze as linhas cuja PK não existe mais no Sapiens.

    query_pks_completo deve trazer SÓ as colunas de chaves_pk, no escopo
    cheio da tabela (CODEMP/CODFIL quando aplicável), SEM filtro de data --
    é o universo completo e atual do Sapiens, desacoplado da janela de 60
    dias do incremental normal. Uma linha só é removida se a PK dela não
    aparecer em lugar nenhum desse universo; qualquer linha que ainda
    exista no Sapiens (de qualquer data) nunca é tocada.

    Returns:
        Quantidade de linhas removidas (0 se nenhuma).
    """
    condicao_merge = " AND ".join(
        [f"DEST.{col} = SRC.{col}" for col in chaves_pk]
    )

    delete_sql = f"""
DELETE FROM {schema}.{tabela} DEST
WHERE NOT EXISTS (
    SELECT 1
    FROM (
        {query_pks_completo}
    ) SRC
    WHERE {condicao_merge}
)
"""

    with engine.begin() as conn:
        resultado = conn.execute(text(delete_sql))
        linhas_removidas = resultado.rowcount or 0

    if linhas_removidas:
        print(f"  [BRONZE] {schema}.{tabela}: {linhas_removidas} linha(s) removida(s) (órfã -- excluída na origem)")

    return linhas_removidas


# ----- CARGA DA CAMADA BRONZE -----

def carregar_bronze(
    engine: Engine,
    schema: str,
    tabela: str,
    query: str,
    chaves_pk: list[str],
    coluna_ordem: str | None = None,
    chunksize: int = 100_000,
    query_pks_completo: str | None = None,
) -> dict:
    """
    Ponto de entrada único de carga para a camada Bronze.

    Decide automaticamente entre full_reload_streaming() (1ª carga) e
    upsert() (cargas seguintes, incremental com janela de 60 dias
    retroativos) -- e só lê do Sapiens DEPOIS de decidir qual caminho
    seguir. Na 1ª carga, a leitura é feita em lotes direto do cursor
    Oracle (full_reload_streaming), sem nunca montar a tabela inteira em
    um único DataFrame -- necessário para tabelas grandes/transacionais
    (ex.: E120IPD, 1,4 milhão de linhas x 285 colunas).

    Args:
        query              : query de extração já com o filtro correto
                             (full ou janela de 60 dias) -- essa decisão é
                             tomada previamente pelo chamador usando
                             tabela_tem_dados().
        chaves_pk          : PK real da tabela no Sapiens. Como a Bronze
                             não aplica nenhuma transformação, é a mesma
                             PK física de origem.
        coluna_ordem       : usada só na carga incremental, para
                             desduplicar caso a janela de 60 dias traga o
                             mesmo registro mais de uma vez no MERGE. Se
                             None, usa a primeira coluna de chaves_pk.
        chunksize          : tamanho do lote de leitura na 1ª carga
                             (streaming).
        query_pks_completo : query leve (só colunas de chaves_pk, escopo
                             cheio, sem janela de data) usada para
                             detectar e remover órfãos -- ver
                             remover_orfaos(). Roda só na carga
                             incremental, nunca na 1ª carga. Se None,
                             pula a remoção de órfãos (comportamento
                             anterior).

    Returns:
        dict no mesmo formato retornado por full_reload_streaming() ou
        upsert(), dependendo de qual estratégia foi usada. Na carga
        incremental, ganha também a chave 'linhas_removidas' quando
        query_pks_completo é informado.
    """
    primeira_carga = not tabela_tem_dados(engine, schema, tabela)

    if primeira_carga:
        print(f"  [BRONZE] {schema}.{tabela}: 1ª carga -> FULL, lendo em lotes de {chunksize:,} linhas")
        return full_reload_streaming(engine, query, schema, tabela, chunksize=chunksize)

    print(f"  [BRONZE] {schema}.{tabela}: carga incremental -> MERGE (janela de 60 dias)")

    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
    df.columns = [col.upper() for col in df.columns]
    dtype_map = build_dtype_map(df)

    resultado = upsert(
        engine,
        df,
        schema,
        tabela,
        query=query,
        chaves_merge=chaves_pk,
        coluna_ordem=coluna_ordem or chaves_pk[0],
        dtype_map=dtype_map,
    )

    if query_pks_completo:
        resultado["linhas_removidas"] = remover_orfaos(
            engine, schema, tabela, chaves_pk, query_pks_completo
        )

    return resultado