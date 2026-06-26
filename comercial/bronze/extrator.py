"""
Motor genérico de extração da camada Bronze do Comercial.

Como a Bronze é cópia crua (mesma estrutura, mesmo nome, sem transformação),
um único motor genérico serve para QUALQUER tabela do catálogo
(comercial/bronze/tabelas.py) -- não precisa de script por tabela, como
acontece na Prata.

Para cada tabela:
    1. Verifica se ela já existe e tem dados na Bronze (tabela_tem_dados).
    2. Monta a query de extração:
        - 1ª carga         -> SELECT * com filtro CODEMP = 1 (e CODFIL = 1,
                              se a tabela tiver esse campo)
        - cargas seguintes -> idem + filtro coluna_data >= SYSDATE - 60
                              (só se a tabela tiver coluna_data no catálogo;
                              senão, continua sempre full)
    3. Executa a query no Sapiens, lê para DataFrame.
    4. Chama core.loader.carregar_bronze() para gravar na Bronze.
"""

# ----- IMPORTS -----

import pandas as pd
from sqlalchemy import text

from comercial.bronze.tabelas import buscar_tabela
from comercial.config.settings import (
    CODEMP_AQUARIO,
    CODFIL_AQUARIO,
    JANELA_INCREMENTAL_DIAS,
    schema_bronze,
)
from core.db import get_engine
from core.dtype_map import build_dtype_map
from core.loader import carregar_bronze, tabela_tem_dados

# ----- BLOCO ATUAL -----

TABELAS_DESTE_BLOCO = ["E028CPG", "E066FPG", "E073TRA"]


# ----- MONTAGEM DA QUERY -----

def montar_query(info: dict, primeira_carga: bool) -> str:
    """
    Monta a query de extração no Sapiens para uma tabela do catálogo.

    Sempre filtra CODEMP = 1. Filtra também CODFIL = 1 quando
    info["tem_codfil"] = True. Na carga incremental (não é a 1ª carga
    E a tabela tem coluna_data definida no catálogo), adiciona o filtro
    de janela de 60 dias retroativos.
    """
    tabela = info["tabela"]
    filtros = [f"CODEMP = {CODEMP_AQUARIO}"]

    if info["tem_codfil"]:
        filtros.append(f"CODFIL = {CODFIL_AQUARIO}")

    if not primeira_carga and info["coluna_data"]:
        filtros.append(
            f"{info['coluna_data']} >= SYSDATE - {JANELA_INCREMENTAL_DIAS}"
        )

    where = " AND ".join(filtros)

    return f"SELECT * FROM SAPIENS.{tabela} WHERE {where}"


# ----- EXTRAÇÃO E CARGA DE UMA TABELA -----

def rodar_tabela(engine, nome_tabela: str) -> dict:
    """Executa o ciclo completo (extração + carga) para uma tabela do catálogo."""
    info = buscar_tabela(nome_tabela)

    if info["chaves_pk"] is None:
        print(f"  [AVISO] {nome_tabela} não tem PK (é view) -- fora deste motor genérico.")
        return {"tabela": nome_tabela, "status": "PULADA"}

    primeira_carga = not tabela_tem_dados(engine, schema_bronze, nome_tabela)
    query = montar_query(info, primeira_carga)

    print(f"\n{'='*60}")
    print(f"  TABELA: {nome_tabela}  ({'1a CARGA - FULL' if primeira_carga else 'INCREMENTAL'})")
    print(f"{'='*60}")
    print(f"  Query: {query}")

    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)

    df.columns = [col.upper() for col in df.columns]
    dtype_map = build_dtype_map(df)

    coluna_ordem = info["coluna_data"] or info["chaves_pk"][0]

    resultado = carregar_bronze(
        engine,
        df,
        schema_bronze,
        nome_tabela,
        query=query,
        chaves_pk=info["chaves_pk"],
        coluna_ordem=coluna_ordem,
        dtype_map=dtype_map,
    )

    resultado["tabela"] = nome_tabela
    return resultado


# ----- EXECUÇÃO DO BLOCO -----

if __name__ == "__main__":
    engine = get_engine()
    resultados = []

    for nome in TABELAS_DESTE_BLOCO:
        resultados.append(rodar_tabela(engine, nome))

    print(f"\n{'#'*60}")
    print("  RESUMO DO BLOCO")
    print(f"{'#'*60}")
    for r in resultados:
        print(f"  {r}")