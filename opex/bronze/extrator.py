"""
Motor genérico de extração da camada Bronze do OPEX.

Como a Bronze é cópia crua (mesma estrutura, mesmo nome, sem transformação),
um único motor genérico serve para as 5 tabelas do catálogo
(opex/bronze/tabelas.py) -- mesmo padrão do Comercial.

DIFERENÇA ESTRUTURAL EM RELAÇÃO AO COMERCIAL: a origem é o banco de
Controladoria (servidor Oracle separado, 172.16.0.123), não o ERP
principal. Isso exige DOIS engines:
    engine_leitura  = core.db.get_engine_controladoria() -- lê SAPIENS.* de lá
    engine_escrita  = core.db.get_engine_bronze()         -- grava no DW_BRONZE

Como não existe DB LINK entre os dois servidores (confirmado em
07/07/2026), core.loader.carregar_bronze() usa upsert_cross_servidor()/
remover_orfaos_cross_servidor() (staging no destino) em vez do MERGE/
DELETE com subquery embutida usado pelo Comercial -- ver core/loader.py.

Para cada tabela:
    1. Verifica se ela já existe e tem dados na Bronze (tabela_tem_dados).
    2. Monta a query de extração:
        - 1ª carga         -> SELECT * com filtro pela coluna de empresa
                              real (info["coluna_codemp"]) IN (1, 50)
                              quando tem_codemp=True. Tabelas globais
                              (tem_codemp=False): sem filtro algum.
        - cargas seguintes -> idem + filtro coluna_data >= SYSDATE - 60
    3. Chama core.loader.carregar_bronze() (lê da Controladoria, grava no
       DW_BRONZE).

VERIFICAÇÃO DE ÓRFÃOS: mesma regra do Comercial -- só roda na ÚLTIMA
execução do dia, quando o script é chamado com a flag --sweep-orfaos (ver
core/loader.py para o porquê: custo de I/O repetido desnecessário se
rodasse em todo ciclo).
"""

# ----- IMPORTS -----

import sys
import traceback
from datetime import datetime
from time import perf_counter

from opex.bronze.tabelas import TABELAS, buscar_tabela
from opex.config.settings import (
    CODEMP_AQUARIO_OPEX,
    JANELA_INCREMENTAL_DIAS,
    schema_bronze,
)
from core.db import get_engine_bronze, get_engine_controladoria
from core.loader import carregar_bronze, tabela_tem_dados

# ----- BLOCO ATUAL -----

TABELAS_DESTE_BLOCO = [
    "USU_T650ORC",
    "USU_T650CUS",
    "E044CCU",
    "E043PCM",
    "R910USU"
]


# ----- MONTAGEM DA QUERY -----

def montar_query(info: dict, primeira_carga: bool) -> str:
    """
    Monta a query de extração no Sapiens (Controladoria) para uma tabela
    do catálogo.

    Respeita tem_codemp: tabelas globais (tem_codemp=False) não recebem
    nenhum filtro de empresa. Para as demais, filtra pela coluna real de
    empresa (info["coluna_codemp"]) IN CODEMP_AQUARIO_OPEX -- (1, 50),
    exceção documentada em opex.config.settings (diferente do resto do
    projeto, que é sempre CODEMP = 1).

    Na carga incremental (não é a 1ª carga E a tabela tem coluna_data
    definida no catálogo), adiciona o filtro de janela de 60 dias.

    coluna_data_fallback (opcional, ex.: E043PCM): quando a coluna de
    auditoria (coluna_data) pode ficar NULL em linha nova (só é
    preenchida numa edição futura, nunca na criação), o filtro vira
    NVL(coluna_data, coluna_data_fallback) -- usa a data de geração
    quando não existe data de alteração ainda, em vez de deixar a linha
    permanentemente fora da janela incremental. Bug real encontrado em
    18/07/2026 -- ver doc_nova_arquitetura.md.
    """
    tabela = info["tabela"]
    filtros = []

    if info["tem_codemp"]:
        coluna_codemp = info["coluna_codemp"]
        valores = ", ".join(str(v) for v in CODEMP_AQUARIO_OPEX)
        filtros.append(f"{coluna_codemp} IN ({valores})")

    if not primeira_carga and info["coluna_data"]:
        coluna_data = info["coluna_data"]
        fallback = info.get("coluna_data_fallback")
        if fallback:
            filtros.append(
                f"NVL({coluna_data}, {fallback}) >= SYSDATE - {JANELA_INCREMENTAL_DIAS}"
            )
        else:
            filtros.append(f"{coluna_data} >= SYSDATE - {JANELA_INCREMENTAL_DIAS}")

    if filtros:
        where = " AND ".join(filtros)
        return f"SELECT * FROM SAPIENS.{tabela} WHERE {where}"
    else:
        # Tabela global sem nenhum filtro (E043PCM, R910USU)
        return f"SELECT * FROM SAPIENS.{tabela}"


def montar_query_pks(info: dict) -> str:
    """
    Monta a query leve usada para detectar órfãos
    (core.loader.remover_orfaos_cross_servidor()).

    Traz SÓ as colunas de chaves_pk, no escopo cheio (coluna_codemp real
    IN CODEMP_AQUARIO_OPEX, quando aplicável) -- NUNCA com o filtro de
    janela de 60 dias, porque essa query representa o universo completo e
    atual do Sapiens (Controladoria).
    """
    tabela  = info["tabela"]
    pk_cols = ", ".join(info["chaves_pk"])
    filtros = []

    if info["tem_codemp"]:
        coluna_codemp = info["coluna_codemp"]
        valores = ", ".join(str(v) for v in CODEMP_AQUARIO_OPEX)
        filtros.append(f"{coluna_codemp} IN ({valores})")

    if filtros:
        where = " AND ".join(filtros)
        return f"SELECT {pk_cols} FROM SAPIENS.{tabela} WHERE {where}"
    else:
        return f"SELECT {pk_cols} FROM SAPIENS.{tabela}"


# ----- EXTRAÇÃO E CARGA DE UMA TABELA -----

def rodar_tabela(engine_leitura, engine_escrita, nome_tabela: str, verificar_orfaos: bool = False) -> dict:
    """
    Executa o ciclo completo (extração + carga) para uma tabela do catálogo.

    verificar_orfaos: só True na última execução do dia (flag --sweep-orfaos
    do bloco principal) -- mesma regra do Comercial.
    """
    info = buscar_tabela(nome_tabela)

    primeira_carga = not tabela_tem_dados(engine_escrita, schema_bronze, nome_tabela)
    query = montar_query(info, primeira_carga)

    print(f"\n{'='*60}")
    print(f"  TABELA: {nome_tabela}  ({'1a CARGA - FULL' if primeira_carga else 'INCREMENTAL'})")
    print(f"{'='*60}")
    print(f"  Query: {query}")

    coluna_ordem = info["coluna_data"] or info["chaves_pk"][0]

    query_pks_completo = montar_query_pks(info) if verificar_orfaos else None

    resultado = carregar_bronze(
        engine_leitura,
        schema_bronze,
        nome_tabela,
        query,
        chaves_pk=info["chaves_pk"],
        coluna_ordem=coluna_ordem,
        query_pks_completo=query_pks_completo,
        engine_escrita=engine_escrita,
    )

    resultado["tabela"] = nome_tabela
    return resultado


# ----- EXECUÇÃO DO BLOCO -----

if __name__ == "__main__":
    # --sweep-orfaos: passada só pela ÚLTIMA execução agendada do dia.
    verificar_orfaos = "--sweep-orfaos" in sys.argv

    engine_leitura = get_engine_controladoria()
    engine_escrita = get_engine_bronze()
    resultados = []
    inicio_bloco = perf_counter()
    inicio_datetime = datetime.now()

    print(f"\n{'#'*60}")
    print(f"  Início da execução: {inicio_datetime:%Y-%m-%d %H:%M:%S}")
    if verificar_orfaos:
        print("  ÚLTIMA EXECUÇÃO DO DIA -- será verificado se há registros órfãos")
        print("  (comparação do universo completo de PKs na Controladoria x Bronze,")
        print("  sem depender da janela de 60 dias do incremental normal)")
    else:
        print("  Execução normal do ciclo -- sem verificação de órfãos")
    print(f"{'#'*60}")

    for nome in TABELAS_DESTE_BLOCO:
        inicio_tabela = perf_counter()
        try:
            resultado = rodar_tabela(engine_leitura, engine_escrita, nome, verificar_orfaos=verificar_orfaos)
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
