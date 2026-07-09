"""
Motor genérico de extração da camada Bronze da Produção.

Mesmo padrão do Comercial/Laudos RMA: um único motor genérico serve para
as 16 tabelas do catálogo (producao/bronze/tabelas.py) -- não precisa de
script por tabela.

Para cada tabela:
    1. Verifica se ela já existe e tem dados na Bronze (tabela_tem_dados).
    2. Monta a query de extração:
        - 1ª carga         -> SELECT * com filtro pela coluna de empresa
                              real (info["coluna_codemp"]) = 1, e coluna
                              de filial real (info["coluna_codfil"]) = 1
                              quando tem_codfil=True.
        - cargas seguintes -> idem + filtro coluna_data >= SYSDATE - 60
                              (só se a tabela tiver coluna_data no
                              catálogo; senão, continua sempre full --
                              8 das 16 tabelas desta área não têm coluna
                              de auditoria confiável, ver tabelas.py)
    3. Chama core.loader.carregar_bronze() para gravar na Bronze.

TABELAS COMPARTILHADAS COM O COMERCIAL (E012FAM, E013AGP, E075DER,
E075PRO) NÃO aparecem em TABELAS_DESTE_BLOCO -- já são mantidas pelo
comercial/bronze/extrator.py. Ver observação em bronze/tabelas.py.

VERIFICAÇÃO DE ÓRFÃOS: mesma regra do Comercial/OPEX/Laudos RMA -- só
roda na ÚLTIMA execução do dia, quando o script é chamado com a flag
--sweep-orfaos.
"""

# ----- IMPORTS -----

import sys
import traceback
from datetime import datetime
from time import perf_counter

from producao.bronze.tabelas import TABELAS, buscar_tabela
from producao.config.settings import (
    CODEMP_AQUARIO,
    CODFIL_AQUARIO,
    JANELA_INCREMENTAL_DIAS,
    schema_bronze,
)
from core.db import get_engine
from core.loader import carregar_bronze, tabela_tem_dados

# ----- BLOCO ATUAL -----

TABELAS_DESTE_BLOCO = [
    "E018MTV",
    "E044CCU",
    "E047NTG",
    "E093ETG",
    "E210MVP",
    "E621MTC",
    "E626ORC",
    "E626TAX",
    "E630SPE",
    "E720OPR",
    "E725CRE",
    "E900COP",
    "E900EOQ",
    "E900OOP",
    "E900QDO",
    "E930MPR",
]


# ----- MONTAGEM DA QUERY -----

def montar_query(info: dict, primeira_carga: bool) -> str:
    """
    Monta a query de extração no Sapiens para uma tabela do catálogo.

    Respeita tem_codemp: tabelas sem coluna de empresa não recebem
    nenhum filtro (não é o caso de nenhuma tabela desta área -- todas as
    16 têm CODEMP). Filtra pela coluna real de empresa
    (info["coluna_codemp"]) = 1, e pela coluna real de filial
    (info["coluna_codfil"]) = 1 quando tem_codfil = True.

    Na carga incremental (não é a 1ª carga E a tabela tem coluna_data
    definida no catálogo), adiciona o filtro de janela de 60 dias.

    data_sentinela (opcional, ex.: E900EOQ = "1900-12-31"): algumas
    tabelas do Sapiens usam uma data fixa no passado como "sem data
    definida" (ex.: apontamento ainda pendente), em vez de NULL. Como
    esse valor nunca satisfaz >= SYSDATE-60, uma linha nova com esse
    sentinela ficaria permanentemente fora do incremental -- bug real
    encontrado em 09/07/2026 via conferência (E900EOQ). Quando o
    catálogo declara data_sentinela, o filtro de janela também inclui
    linhas com esse valor exato, até ganharem uma data real.
    """
    tabela = info["tabela"]
    filtros = []

    if info["tem_codemp"]:
        coluna_codemp = info.get("coluna_codemp", "CODEMP")
        filtros.append(f"{coluna_codemp} = {CODEMP_AQUARIO}")

    if info.get("tem_codfil"):
        coluna_codfil = info.get("coluna_codfil", "CODFIL")
        filtros.append(f"{coluna_codfil} = {CODFIL_AQUARIO}")

    if not primeira_carga and info["coluna_data"]:
        coluna_data = info["coluna_data"]
        sentinela = info.get("data_sentinela")
        if sentinela:
            filtros.append(
                f"({coluna_data} >= SYSDATE - {JANELA_INCREMENTAL_DIAS} "
                f"OR {coluna_data} = TO_DATE('{sentinela}', 'YYYY-MM-DD'))"
            )
        else:
            filtros.append(
                f"{coluna_data} >= SYSDATE - {JANELA_INCREMENTAL_DIAS}"
            )

    if filtros:
        where = " AND ".join(filtros)
        return f"SELECT * FROM SAPIENS.{tabela} WHERE {where}"
    else:
        return f"SELECT * FROM SAPIENS.{tabela}"


def montar_query_pks(info: dict) -> str:
    """
    Monta a query leve usada para detectar órfãos (core.loader.remover_orfaos()).

    Traz SÓ as colunas de chaves_pk, no escopo cheio, sem janela de data.
    """
    tabela  = info["tabela"]
    pk_cols = ", ".join(info["chaves_pk"])
    filtros = []

    if info["tem_codemp"]:
        coluna_codemp = info.get("coluna_codemp", "CODEMP")
        filtros.append(f"{coluna_codemp} = {CODEMP_AQUARIO}")

    if info.get("tem_codfil"):
        coluna_codfil = info.get("coluna_codfil", "CODFIL")
        filtros.append(f"{coluna_codfil} = {CODFIL_AQUARIO}")

    if filtros:
        where = " AND ".join(filtros)
        return f"SELECT {pk_cols} FROM SAPIENS.{tabela} WHERE {where}"
    else:
        return f"SELECT {pk_cols} FROM SAPIENS.{tabela}"


# ----- EXTRAÇÃO E CARGA DE UMA TABELA -----

def rodar_tabela(engine, nome_tabela: str, verificar_orfaos: bool = False) -> dict:
    """Executa o ciclo completo (extração + carga) para uma tabela do catálogo."""
    info = buscar_tabela(nome_tabela)

    primeira_carga = not tabela_tem_dados(engine, schema_bronze, nome_tabela)
    query = montar_query(info, primeira_carga)

    print(f"\n{'='*60}")
    print(f"  TABELA: {nome_tabela}  ({'1a CARGA - FULL' if primeira_carga else 'INCREMENTAL'})")
    print(f"{'='*60}")
    print(f"  Query: {query}")

    coluna_ordem = info["coluna_data"] or info["chaves_pk"][0]
    query_pks_completo = montar_query_pks(info) if verificar_orfaos else None

    resultado = carregar_bronze(
        engine,
        schema_bronze,
        nome_tabela,
        query,
        chaves_pk=info["chaves_pk"],
        coluna_ordem=coluna_ordem,
        query_pks_completo=query_pks_completo,
    )

    resultado["tabela"] = nome_tabela
    return resultado


# ----- EXECUÇÃO DO BLOCO -----

if __name__ == "__main__":
    verificar_orfaos = "--sweep-orfaos" in sys.argv

    engine = get_engine()
    resultados = []
    inicio_bloco = perf_counter()
    inicio_datetime = datetime.now()

    print(f"\n{'#'*60}")
    print(f"  Início da execução: {inicio_datetime:%Y-%m-%d %H:%M:%S}")
    if verificar_orfaos:
        print("  ÚLTIMA EXECUÇÃO DO DIA -- será verificado se há registros órfãos")
        print("  (comparação do universo completo de PKs no Sapiens x Bronze,")
        print("  sem depender da janela de 60 dias do incremental normal)")
    else:
        print("  Execução normal do ciclo -- sem verificação de órfãos")
    print(f"{'#'*60}")

    for nome in TABELAS_DESTE_BLOCO:
        inicio_tabela = perf_counter()
        try:
            resultado = rodar_tabela(engine, nome, verificar_orfaos=verificar_orfaos)
        except Exception:
            print(f"\n  [ERRO] Falha ao processar {nome}:")
            traceback.print_exc()
            resultado = {"tabela": nome, "status": "ERRO"}

        resultado["duracao_s"] = perf_counter() - inicio_tabela
        resultados.append(resultado)

    duracao_bloco = perf_counter() - inicio_bloco

    print(f"\n{'#'*60}")
    print("  RESUMO DO BLOCO")
    print(f"{'#'*60}")
    for r in resultados:
        status = r.get("status", "OK")
        linhas = r.get("linhas_salvas", "-")
        linhas_fmt = f"{linhas:,}" if isinstance(linhas, int) else linhas

        if "linhas_removidas" in r:
            orfaos = f" | órfãos verificados: {r['linhas_removidas']}"
        else:
            orfaos = ""

        print(f"  {r['tabela']:<20} -> {status:<8} | linhas salvas: {linhas_fmt:>10} | tempo: {r['duracao_s']:>6.1f}s{orfaos}")

    fim_datetime = datetime.now()
    minutos  = int(duracao_bloco // 60)
    segundos = duracao_bloco % 60
    print(f"{'#'*60}")
    print(f"  Início da execução : {inicio_datetime:%Y-%m-%d %H:%M:%S}")
    print(f"  Término da execução: {fim_datetime:%Y-%m-%d %H:%M:%S}")
    print(f"  Duração total do bloco: {minutos}min {segundos:.0f}s")
    if verificar_orfaos:
        total_orfaos = sum(r.get("linhas_removidas", 0) for r in resultados)
        print(f"  Última execução do dia: verificação de órfãos concluída -- total removido: {total_orfaos}")
    print(f"{'#'*60}")
