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

VERIFICAÇÃO DE ÓRFÃOS (registros deletados fisicamente no Sapiens):
    Rodar essa verificação em TODO ciclo de 15 min seria uma varredura
    repetida contra tabelas de até 1,4 milhão de linhas do Sapiens em
    produção (compartilhado com outras empresas do grupo) -- custo de I/O
    recorrente desnecessário, já que exclusão física é rara no dia a dia.

    Por isso ela só roda na ÚLTIMA execução do dia, quando o script é
    chamado com a flag --sweep-orfaos (ex.: agendada para as 19h no
    Agendador de Tarefas). Nas demais execuções do dia, roda tudo
    normalmente, sem essa verificação.

    A decisão de "é a última execução do dia" é deliberadamente uma flag
    explícita passada por quem agenda o script, e não um cálculo por
    horário aqui dentro -- calcular por relógio seria frágil (atraso de
    um ciclo, execução manual fora de hora, etc. poderiam pular a
    verificação do dia inteiro sem ninguém perceber).
"""

# ----- IMPORTS -----

import sys
import traceback
from datetime import datetime
from time import perf_counter

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
    "E095FOR",
    "USU_T017RVR",
    "USU_T101CRI",
    "USU_T101MET",
    "USU_T101TIP",
    "USU_TPCAMNC",
    "USU_TPCAPFC",
    "USU_TPCRCDG",
    "USU_TPCRCPC",
    "R999USU",
]


# ----- MONTAGEM DA QUERY -----

def montar_query(info: dict, primeira_carga: bool) -> str:
    """
    Monta a query de extração no Sapiens para uma tabela do catálogo.

    Respeita tem_codemp: tabelas globais (tem_codemp=False) não recebem
    nenhum filtro de empresa. Para as demais, filtra pela coluna real de
    empresa (info["coluna_codemp"], default "CODEMP") = 1, e pela coluna
    real de filial (info["coluna_codfil"], default "CODFIL") = 1 quando
    tem_codfil = True. A maioria das tabelas usa os nomes padrão -- só
    quando o nome físico é outro (ex.: USU_T101MET usa USU_CODEMP, não
    CODEMP -- bug de produção corrigido em 06/07/2026) o catálogo precisa
    declarar coluna_codemp/coluna_codfil explicitamente.

    Na carga incremental (não é a 1ª carga E a tabela tem coluna_data
    definida no catálogo), adiciona o filtro de janela de 60 dias.
    """
    tabela = info["tabela"]
    filtros = []

    coluna_codemp = info.get("coluna_codemp", "CODEMP")
    coluna_codfil = info.get("coluna_codfil", "CODFIL")

    # Filtro de empresa — só para tabelas que têm coluna de empresa
    if info["tem_codemp"]:
        filtros.append(f"{coluna_codemp} = {CODEMP_AQUARIO}")

    # Filtro de filial — só quando tem_codfil=True (implica tem_codemp=True)
    if info["tem_codfil"]:
        filtros.append(f"{coluna_codfil} = {CODFIL_AQUARIO}")

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


def montar_query_pks(info: dict) -> str:
    """
    Monta a query leve usada para detectar órfãos (core.loader.remover_orfaos()).

    Traz SÓ as colunas de chaves_pk, no escopo cheio (coluna_codemp/
    coluna_codfil reais, quando aplicável) -- NUNCA com o filtro de janela
    de 60 dias, porque essa query representa o universo completo e atual
    do Sapiens, usado pra saber o que realmente não existe mais lá (não só
    o que ficou de fora da leva incremental).
    """
    tabela   = info["tabela"]
    pk_cols  = ", ".join(info["chaves_pk"])
    filtros  = []

    coluna_codemp = info.get("coluna_codemp", "CODEMP")
    coluna_codfil = info.get("coluna_codfil", "CODFIL")

    if info["tem_codemp"]:
        filtros.append(f"{coluna_codemp} = {CODEMP_AQUARIO}")
    if info["tem_codfil"]:
        filtros.append(f"{coluna_codfil} = {CODFIL_AQUARIO}")

    if filtros:
        where = " AND ".join(filtros)
        return f"SELECT {pk_cols} FROM SAPIENS.{tabela} WHERE {where}"
    else:
        return f"SELECT {pk_cols} FROM SAPIENS.{tabela}"


# ----- EXTRAÇÃO E CARGA DE UMA TABELA -----

def rodar_tabela(engine, nome_tabela: str, verificar_orfaos: bool = False) -> dict:
    """
    Executa o ciclo completo (extração + carga) para uma tabela do catálogo.

    verificar_orfaos: só True na última execução do dia (flag --sweep-orfaos
    do bloco principal). Controla se query_pks_completo é passada adiante --
    sem ela, carregar_bronze() simplesmente pula a verificação de órfãos
    nesta execução (ver docstring do módulo).
    """
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

    # query_pks_completo só é usada na carga incremental (carregar_bronze()
    # ignora esse parâmetro na 1ª carga) -- é a query leve que detecta e
    # remove órfãos (registros deletados fisicamente no Sapiens), decoupled
    # da janela de 60 dias do incremental normal. Só é montada quando esta
    # é a última execução do dia (verificar_orfaos=True) -- nas demais
    # execuções, fica None e carregar_bronze() pula a verificação.
    query_pks_completo = montar_query_pks(info) if verificar_orfaos else None

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
        query_pks_completo=query_pks_completo,
    )

    resultado["tabela"] = nome_tabela
    return resultado


# ----- EXECUÇÃO DO BLOCO -----

if __name__ == "__main__":
    # --sweep-orfaos: passada só pela ÚLTIMA execução agendada do dia (ex.:
    # 19h no Agendador de Tarefas). Ver docstring do módulo para o porquê de
    # ser uma flag explícita, e não um cálculo por horário aqui dentro.
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
            # Uma tabela com erro não pode travar as demais do bloco --
            # loga o erro completo (pra investigar depois) e segue pra próxima.
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

        # "linhas_removidas" só existe no dict quando a verificação de
        # órfãos de fato rodou nesta tabela (verificar_orfaos=True e não foi
        # 1ª carga) -- por isso o "in r" em vez de comparar contra 0: assim
        # dá pra distinguir "verificado, não achou órfão" (mostra 0) de
        # "não foi verificado nesta execução" (não mostra nada).
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