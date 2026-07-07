"""
Motor genérico de extração da camada Bronze do Comercial.

Como a Bronze é cópia crua (mesma estrutura, mesmo nome, sem transformação),
um único motor genérico serve para QUALQUER tabela do catálogo
(comercial/bronze/tabelas.py) -- não precisa de script por tabela, como
acontece na Prata.

Para cada tabela:
    1. Verifica se ela já existe e tem dados na Bronze (tabela_tem_dados).
    2. Monta a query de extração:
        - 1ª carga         -> SELECT * com filtro CODEMP = 1 (se tem_codemp=True)
                              e CODFIL = 1 (se tem_codfil=True).
                              Tabelas globais (tem_codemp=False): sem filtro algum.
        - cargas seguintes -> idem + filtro coluna_data >= SYSDATE - 60
                              (só se a tabela tiver coluna_data no catálogo;
                              senão, continua sempre full)
    3. Executa a query no Sapiens, lê para DataFrame.
    4. Chama core.loader.carregar_bronze() para gravar na Bronze.
"""

# ----- IMPORTS -----

import traceback

from comercial.bronze.tabelas import TABELAS, buscar_tabela
from comercial.config.settings import (
    CODEMP_AQUARIO,
    CODFIL_AQUARIO,
    JANELA_INCREMENTAL_DIAS,
    schema_bronze,
)
from core.db import get_engine
from core.loader import carregar_bronze, tabela_tem_dados

# ----- BLOCO ATUAL -----

TABELAS_DESTE_BLOCO = [
    "E120IPD",
    "E120PED",
    "E140IPV",
    "E140ISV",
    "E140NFV",
    "E440IPC",
    "E440NFC",
    "E001TNS",
    "E012FAM",
    "E013AGP",
    "E028CPG",
    "E066FPG",
    "E075DER",
    "E075PRO",
    "E085HCL",
    "E140IDE",
    "E140PVD",
    "E022CLF",
    "E026RAM",
    "E069GRE",
    "E073TRA",
    "E085CLI",
    "E090REP",
    "E095FOR"

]



# ----- MONTAGEM DA QUERY -----

def montar_query(info: dict, primeira_carga: bool) -> str:
    """
    Monta a query de extração no Sapiens para uma tabela do catálogo.

    Respeita tem_codemp: tabelas globais (tem_codemp=False) não recebem
    nenhum filtro de empresa. Para as demais, filtra CODEMP = 1 sempre,
    e CODFIL = 1 quando tem_codfil = True.

    Na carga incremental (não é a 1ª carga E a tabela tem coluna_data
    definida no catálogo), adiciona o filtro de janela de 60 dias.
    """
    tabela = info["tabela"]
    filtros = []

    # Filtro de empresa — só para tabelas que têm CODEMP
    if info["tem_codemp"]:
        filtros.append(f"CODEMP = {CODEMP_AQUARIO}")

    # Filtro de filial — só quando tem_codfil=True (implica tem_codemp=True)
    if info["tem_codfil"]:
        filtros.append(f"CODFIL = {CODFIL_AQUARIO}")

    # Filtro incremental — só nas cargas seguintes à 1ª, e se houver coluna_data
    if not primeira_carga and info["coluna_data"]:
        filtros.append(
            f"{info['coluna_data']} >= SYSDATE - {JANELA_INCREMENTAL_DIAS}"
        )

    if filtros:
        where = " AND ".join(filtros)
        return f"SELECT * FROM SAPIENS.{tabela} WHERE {where}"
    else:
        # Tabela global sem nenhum filtro (ex.: E073TRA, E085CLI, etc.)
        return f"SELECT * FROM SAPIENS.{tabela}"


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

    coluna_ordem = info["coluna_data"] or info["chaves_pk"][0]

    # A leitura do Sapiens acontece DENTRO de carregar_bronze(): na 1ª carga,
    # em lotes (full_reload_streaming) para não estourar memória em tabelas
    # grandes (ex.: E120IPD); nas cargas seguintes, via upsert() normal --
    # a janela de 60 dias já mantém o volume pequeno o suficiente.
    resultado = carregar_bronze(
        engine,
        schema_bronze,
        nome_tabela,
        query,
        chaves_pk=info["chaves_pk"],
        coluna_ordem=coluna_ordem,
    )

    resultado["tabela"] = nome_tabela
    return resultado


# ----- EXECUÇÃO DO BLOCO -----

if __name__ == "__main__":
    engine = get_engine()
    resultados = []

    for nome in TABELAS_DESTE_BLOCO:
        try:
            resultados.append(rodar_tabela(engine, nome))
        except Exception:
            # Uma tabela com erro não pode travar as demais do bloco --
            # loga o erro completo (pra investigar depois) e segue pra próxima.
            print(f"\n  [ERRO] Falha ao processar {nome}:")
            traceback.print_exc()
            resultados.append({"tabela": nome, "status": "ERRO"})

    print(f"\n{'#'*60}")
    print("  RESUMO DO BLOCO")
    print(f"{'#'*60}")
    for r in resultados:
        status = r.get("status", "OK")
        linhas = r.get("linhas_salvas", "-")
        print(f"  {r['tabela']:<20} -> {status:<8} | linhas salvas: {linhas}")