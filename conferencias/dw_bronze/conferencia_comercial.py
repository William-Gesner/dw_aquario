"""
Conferência Bronze x Sapiens -- Comercial.

Dois níveis de checagem, porque o nível 1 sozinho (o único que existia
antes de 17/07/2026) tinha 2 pontos cegos reais, descobertos via
conferência da Prata (ver doc_nova_arquitetura.md, item 6 das regras):

    a) Contagem usava o MESMO filtro (tem_codemp/tem_codfil) do catálogo
       pros dois lados (Sapiens e Bronze) -- então uma tabela com
       tem_codfil=True ERRADO (bug real encontrado em 10 tabelas) comparava
       "Sapiens filtrado por filial 1" x "Bronze filtrada por filial 1":
       os dois lados erravam igual, a contagem batia, e o bug nunca
       aparecia aqui -- só apareceu na conferência da Prata contra o
       legado, muito mais tarde no processo.
    b) Só comparava COUNT(*) -- nunca pegaria divergência de VALOR num
       registro que existe dos dois lados (caso real: E085CLI com
       ENDCLI/NENCLI desatualizado na Bronze porque o incremental por
       DATATU não capturava a edição -- contagem idêntica, conteúdo
       diferente).

Correções aplicadas:
    a) A contagem "oficial" continua no escopo do catálogo (serve pra
       pegar falha de sincronização de verdade -- 1ª carga incompleta,
       incremental que falhou, órfão não varrido). Mas agora mostra
       TAMBÉM uma contagem do Sapiens SÓ com CODEMP (ignorando CODFIL),
       lado a lado -- só informativo, não decide OK/DIVERGENTE sozinho,
       mas fica visível pra revisão humana se uma tabela tem_codfil=True
       está descartando volume relevante de outras filiais. Não elimina
       a necessidade de validar o JOIN do legado tabela por tabela (regra
       6 do doc), mas não deixa mais isso invisível.
    b) Nova função conferir_conteudo(): MINUS nos dois sentidos, TODAS as
       colunas reais (cópia crua, mesma estrutura do Sapiens, exclui só a
       coluna de metadado DW_DATA_INGESTAO), no mesmo escopo do catálogo.
       Sob demanda (1 tabela por vez, via --conteudo) -- não roda nas 33
       de uma vez, porque nas tabelas grandes (milhões de linhas) um MINUS
       de todas as colunas é pesado. Serve pra pegar exatamente o tipo de
       bug que a contagem nunca pegaria.

Só leitura -- não corrige nem apaga nada.

Uso:
    python -m conferencias.dw_bronze.conferencia_comercial
        -> contagem (rápida) nas 33 tabelas do catálogo.

    python -m conferencias.dw_bronze.conferencia_comercial --conteudo E085CLI
        -> conteúdo (MINUS, dado a dado) só dessa tabela.

Interpretação da contagem (coluna DIFERENÇA != 0):
    - Pequena (1-2 linhas) rodando em horário comercial: pode ser só uma
      transação nova entre a leitura de um lado e do outro (corrida normal,
      não é bug). Rode de novo pra confirmar se persiste.
    - Diferença maior ou persistente: investigar. Causas prováveis --
      1ª carga incompleta, incremental que falhou silenciosamente em algum
      ciclo, ou (se for logo após corrigir uma tabela) órfãos que ainda não
      foram varridos porque o sweep diário (--sweep-orfaos) ainda não rodou
      hoje.

Interpretação do alerta de filial (coluna ALERTA):
    - Só aparece quando tem_codfil=True no catálogo E a contagem sem
      filtro de filial é diferente da contagem oficial. Não é
      automaticamente bug -- pode ser um caso já validado (ver Expedição/
      Rastreabilidade no doc, onde tem_codfil=True está correto porque a
      tabela-base da query legada já fixa CODFIL=1). Mas se aparecer numa
      tabela nova ou ainda não revisada, é sinal de checar o JOIN do
      script legado antes de confiar (regra 6 do doc_nova_arquitetura.md).
"""

# ----- IMPORTS -----

import sys
import traceback

from sqlalchemy import text

from comercial.bronze.extrator import TABELAS_DESTE_BLOCO, montar_query, montar_query_pks
from comercial.bronze.tabelas import buscar_tabela
from comercial.config.settings import CODEMP_AQUARIO, schema_bronze
from core.db import get_engine


# ----- CONTAGENS -----

def contar_sapiens(engine, info: dict) -> int:
    """
    Universo completo e atual da tabela no Sapiens, no escopo do catálogo
    (tem_codemp/tem_codfil) -- mesmo escopo que a Bronze deveria ter.
    """
    query = f"SELECT COUNT(*) FROM ({montar_query_pks(info)})"
    with engine.connect() as conn:
        return conn.execute(text(query)).scalar()


def contar_sapiens_sem_filial(engine, info: dict) -> int | None:
    """
    Contagem do Sapiens só com CODEMP, ignorando CODFIL mesmo quando o
    catálogo diz tem_codfil=True. Puramente informativa (ver docstring do
    módulo) -- None quando tem_codemp=False (tabela global, comparação não
    faz sentido).
    """
    if not info["tem_codemp"]:
        return None

    tabela = info["tabela"]
    coluna_codemp = info.get("coluna_codemp", "CODEMP")
    pk_cols = ", ".join(info["chaves_pk"])
    query = (
        f"SELECT COUNT(*) FROM "
        f"(SELECT {pk_cols} FROM SAPIENS.{tabela} WHERE {coluna_codemp} = {CODEMP_AQUARIO})"
    )
    with engine.connect() as conn:
        return conn.execute(text(query)).scalar()


def contar_bronze(engine, schema: str, tabela: str) -> int:
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT COUNT(*) FROM {schema}.{tabela}")).scalar()


# ----- COLUNAS REAIS (cópia crua -- mesma lista do Sapiens) -----

def colunas_reais(engine, tabela: str) -> list[str]:
    """
    Lista as colunas reais da tabela, na ordem física do Sapiens
    (ALL_TAB_COLUMNS por column_id) -- é a mesma lista/ordem que a Bronze
    tem, já que é cópia crua sem transformação (a Bronze só ganha
    DW_DATA_INGESTAO a mais no final, que fica naturalmente fora desta
    lista por não existir no Sapiens).
    """
    query = """
        SELECT column_name
        FROM ALL_TAB_COLUMNS
        WHERE owner = 'SAPIENS' AND table_name = :tabela
        ORDER BY column_id
    """
    with engine.connect() as conn:
        linhas = conn.execute(text(query), {"tabela": tabela}).fetchall()
    if not linhas:
        raise ValueError(
            f"Nenhuma coluna encontrada para SAPIENS.{tabela} em ALL_TAB_COLUMNS."
        )
    return [linha[0] for linha in linhas]


# ----- CONFERÊNCIA DE CONTAGEM (rápida, todas as tabelas) -----

def conferir_tabela(engine, nome_tabela: str) -> dict:
    info = buscar_tabela(nome_tabela)

    if info["chaves_pk"] is None:
        print(f"  [AVISO] {nome_tabela} não tem PK (é view) -- fora desta conferência.")
        return {"tabela": nome_tabela, "status": "PULADA"}

    total_sapiens = contar_sapiens(engine, info)
    total_bronze = contar_bronze(engine, schema_bronze, nome_tabela)
    total_sapiens_sem_filial = contar_sapiens_sem_filial(engine, info)
    diferenca = total_bronze - total_sapiens

    status = "OK" if diferenca == 0 else "DIVERGENTE"

    alerta_filial = bool(
        info["tem_codfil"]
        and total_sapiens_sem_filial is not None
        and total_sapiens_sem_filial != total_sapiens
    )

    return {
        "tabela": nome_tabela,
        "sapiens": total_sapiens,
        "sapiens_sem_filial": total_sapiens_sem_filial,
        "bronze": total_bronze,
        "diferenca": diferenca,
        "status": status,
        "alerta_filial": alerta_filial,
    }


# ----- CONFERÊNCIA DE CONTEÚDO (dado a dado, 1 tabela por vez) -----

def conferir_conteudo(engine, nome_tabela: str) -> None:
    """
    MINUS nos dois sentidos, todas as colunas reais, Bronze x Sapiens, no
    mesmo escopo do catálogo (tem_codemp/tem_codfil -- reaproveita
    montar_query(), a mesma função que a extração usa pra 1ª carga: full,
    sem janela de data). Pega divergência de VALOR que a contagem nunca
    pegaria -- registro presente nos dois lados, com algum campo
    desatualizado/diferente num deles.

    Pode ser pesado nas tabelas grandes (milhões de linhas, dezenas de
    colunas) -- por isso é sob demanda, 1 tabela por vez, não faz parte da
    varredura rápida das 33.
    """
    info = buscar_tabela(nome_tabela)

    if info["chaves_pk"] is None:
        print(f"  [AVISO] {nome_tabela} não tem PK (é view) -- fora desta conferência.")
        return

    colunas = colunas_reais(engine, nome_tabela)
    colunas_str = ", ".join(colunas)

    query_sapiens = montar_query(info, primeira_carga=True)
    query_bronze = f"SELECT {colunas_str} FROM {schema_bronze}.{nome_tabela}"

    print(f"\n{'='*70}")
    print(f"  CONFERÊNCIA DE CONTEÚDO -- {nome_tabela} (Bronze x Sapiens)")
    print(f"{'='*70}")
    print(f"  Query Sapiens: {query_sapiens}")

    with engine.connect() as conn:
        so_no_sapiens = conn.execute(
            text(f"{query_sapiens}\nMINUS\n{query_bronze}")
        ).fetchall()
        so_na_bronze = conn.execute(
            text(f"{query_bronze}\nMINUS\n{query_sapiens}")
        ).fetchall()

    print(f"\n  Só no Sapiens (ausente ou desatualizado na Bronze) : {len(so_no_sapiens):>8,}")
    print(f"  Só na Bronze (sem equivalente idêntico no Sapiens) : {len(so_na_bronze):>8,}")

    if not so_no_sapiens and not so_na_bronze:
        print(f"\n  [OK] Conteúdo idêntico.")
    else:
        print(f"\n  [DIVERGENTE]")
        if so_no_sapiens:
            print(f"\n  --- Amostra: só no Sapiens (até 10 de {len(so_no_sapiens)}) ---")
            for linha in so_no_sapiens[:10]:
                print(f"    {dict(zip(colunas, linha))}")
        if so_na_bronze:
            print(f"\n  --- Amostra: só na Bronze (até 10 de {len(so_na_bronze)}) ---")
            for linha in so_na_bronze[:10]:
                print(f"    {dict(zip(colunas, linha))}")
    print(f"{'='*70}")


# ----- EXECUÇÃO -----

if __name__ == "__main__":
    engine = get_engine()

    if "--conteudo" in sys.argv:
        idx = sys.argv.index("--conteudo")
        try:
            nome_tabela = sys.argv[idx + 1]
        except IndexError:
            print("  Uso: python -m conferencias.dw_bronze.conferencia_comercial --conteudo NOME_TABELA")
            sys.exit(1)

        conferir_conteudo(engine, nome_tabela)
        sys.exit(0)

    resultados = []

    for nome in TABELAS_DESTE_BLOCO:
        try:
            resultados.append(conferir_tabela(engine, nome))
        except Exception:
            print(f"\n  [ERRO] Falha ao conferir {nome}:")
            traceback.print_exc()
            resultados.append({"tabela": nome, "status": "ERRO"})

    print(f"\n{'='*92}")
    print(
        f"  {'TABELA':<20} {'SAPIENS':>12} {'S/ FILIAL':>12} {'BRONZE':>12} "
        f"{'DIFERENÇA':>12}  STATUS      ALERTA"
    )
    print(f"{'='*92}")

    for r in resultados:
        sapiens = r.get("sapiens", "-")
        sapiens_sf = r.get("sapiens_sem_filial")
        bronze = r.get("bronze", "-")
        diferenca = r.get("diferenca", "-")

        sapiens_fmt = f"{sapiens:,}" if isinstance(sapiens, int) else sapiens
        sapiens_sf_fmt = f"{sapiens_sf:,}" if isinstance(sapiens_sf, int) else "-"
        bronze_fmt = f"{bronze:,}" if isinstance(bronze, int) else bronze
        diferenca_fmt = f"{diferenca:+,}" if isinstance(diferenca, int) else diferenca
        alerta_fmt = "FILIAL?" if r.get("alerta_filial") else ""

        print(
            f"  {r['tabela']:<20} {sapiens_fmt:>12} {sapiens_sf_fmt:>12} {bronze_fmt:>12} "
            f"{diferenca_fmt:>12}  {r['status']:<10}  {alerta_fmt}"
        )

    divergentes = [r for r in resultados if r.get("status") == "DIVERGENTE"]
    puladas = [r for r in resultados if r.get("status") == "PULADA"]
    erros = [r for r in resultados if r.get("status") == "ERRO"]
    alertas = [r for r in resultados if r.get("alerta_filial")]

    print(f"{'='*92}")
    print(
        f"  Total: {len(resultados)} tabelas | "
        f"{len(resultados) - len(divergentes) - len(puladas) - len(erros)} OK | "
        f"{len(divergentes)} divergente(s) | {len(puladas)} pulada(s) | {len(erros)} erro(s) | "
        f"{len(alertas)} com alerta de filial"
    )
    print(f"{'='*92}")
